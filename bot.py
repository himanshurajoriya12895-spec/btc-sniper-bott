import requests
import pandas as pd
import numpy as np
import time

TOKEN   = "8966743878:AAFRB2rB7nxM8eMQN5Om6_veQ4Ow2m8lIo4"
CHAT_ID = "8193076289"
SYMBOL  = "BTCUSDT"

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )

def get_price_history():
    """Last 2 ghante ka price"""
    r  = requests.get(
        f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval=5m&limit=24",
        timeout=10
    ).json()
    df = pd.DataFrame(r, columns=[
        'ts','open','high','low','close','volume',
        'ct','qv','t','bb','bq','i'
    ])
    df['close'] = df['close'].astype(float)
    df['volume']= df['volume'].astype(float)
    df['ts']    = pd.to_datetime(df['ts'], unit='ms')
    return df

def get_funding_history():
    """Last kuch funding rates"""
    r = requests.get(
        f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={SYMBOL}&limit=10",
        timeout=10
    ).json()
    rates = [float(x['fundingRate']) * 100 for x in r]
    return rates

def get_oi_history():
    """Open Interest history"""
    r = requests.get(
        f"https://fapi.binance.com/futures/data/openInterestHist?symbol={SYMBOL}&period=5m&limit=12",
        timeout=10
    ).json()
    oi = [float(x['sumOpenInterest']) for x in r]
    return oi

def get_ls_ratio():
    """Long Short Ratio"""
    r = requests.get(
        f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={SYMBOL}&period=5m&limit=6",
        timeout=10
    ).json()
    return [float(x['longShortRatio']) for x in r]

def get_liquidations():
    """Recent liquidations"""
    try:
        r = requests.get(
            f"https://fapi.binance.com/fapi/v1/forceOrders?symbol={SYMBOL}&limit=50",
            timeout=10
        ).json()
        long_liq  = sum(float(x['origQty']) for x in r if x['side'] == 'SELL')
        short_liq = sum(float(x['origQty']) for x in r if x['side'] == 'BUY')
        return long_liq, short_liq
    except:
        return 0, 0

def get_orderbook_imbalance():
    """Order book depth"""
    r    = requests.get(
        f"https://api.binance.com/api/v3/depth?symbol={SYMBOL}&limit=100",
        timeout=10
    ).json()
    bids = sum(float(q) for p,q in r['bids'])
    asks = sum(float(q) for p,q in r['asks'])
    return bids, asks

def calc_atr(df):
    tr = pd.concat([
        df['high'].astype(float) - df['low'].astype(float),
        abs(df['high'].astype(float) - df['close'].shift()),
        abs(df['low'].astype(float)  - df['close'].shift())
    ], axis=1).max(axis=1)
    return tr.rolling(14).mean().iloc[-1]

def detect_divergence():
    """
    THE SECRET WEAPON:
    Price vs Funding Rate Divergence
    + OI Divergence
    + LS Ratio Divergence
    """

    df      = get_price_history()
    rates   = get_funding_history()
    oi      = get_oi_history()
    ls      = get_ls_ratio()
    l_liq, s_liq = get_liquidations()
    bids, asks   = get_orderbook_imbalance()

    price      = df['close'].iloc[-1]
    price_old  = df['close'].iloc[0]
    price_move = ((price - price_old) / price_old) * 100

    # ===== DIVERGENCES =====

    # 1. PRICE vs FUNDING DIVERGENCE
    fr_now  = rates[-1] if rates else 0
    fr_old  = rates[0]  if rates else 0
    fr_move = fr_now - fr_old

    # Price up + FR down = DUMP coming
    # Price down + FR up = PUMP coming
    fr_div_dump = price_move > 0.5 and fr_move < -0.01
    fr_div_pump = price_move < -0.5 and fr_move > 0.01

    # 2. PRICE vs OI DIVERGENCE
    oi_now  = oi[-1] if oi else 0
    oi_old  = oi[0]  if oi else 0
    oi_move = ((oi_now - oi_old) / (oi_old + 0.001)) * 100

    # Price up + OI down = Weak move = Reversal coming
    # Price down + OI down = Short covering = Pump coming
    oi_div_dump = price_move > 0.5 and oi_move < -1
    oi_div_pump = price_move < -0.5 and oi_move < -1

    # 3. LS RATIO DIVERGENCE
    ls_now = ls[-1] if ls else 1
    ls_old = ls[0]  if ls else 1
    ls_move= ls_now - ls_old

    # Too many longs = dump
    # Too many shorts = pump
    ls_extreme_long  = ls_now > 1.8
    ls_extreme_short = ls_now < 0.6

    # 4. LIQUIDATION CASCADE
    liq_cascade_long  = s_liq > 5  # Shorts getting killed = pump
    liq_cascade_short = l_liq > 5  # Longs getting killed = dump

    # 5. ORDER BOOK VOID
    ob_ratio  = bids / (asks + 0.001)
    path_up   = ob_ratio > 2.0  # Upar raasta khali
    path_down = ob_ratio < 0.5  # Neeche raasta khali

    # ===== SCORE =====
    score_pump = 0
    score_dump = 0
    reasons_p  = []
    reasons_d  = []

    if fr_div_pump:
        score_pump += 3
        reasons_p.append(f"FR Divergence: Price↓ FR↑ ({fr_now:.4f}%)")
    if fr_div_dump:
        score_dump += 3
        reasons_d.append(f"FR Divergence: Price↑ FR↓ ({fr_now:.4f}%)")

    if oi_div_pump:
        score_pump += 2
        reasons_p.append(f"OI Divergence: Price↓ OI↓ ({oi_move:.1f}%)")
    if oi_div_dump:
        score_dump += 2
        reasons_d.append(f"OI Divergence: Price↑ OI↓ ({oi_move:.1f}%)")

    if ls_extreme_short:
        score_pump += 2
        reasons_p.append(f"L/S Extreme Short: {ls_now:.2f}")
    if ls_extreme_long:
        score_dump += 2
        reasons_d.append(f"L/S Extreme Long: {ls_now:.2f}")

    if liq_cascade_long:
        score_pump += 2
        reasons_p.append(f"Short Squeeze: {s_liq:.1f} BTC liquidated")
    if liq_cascade_short:
        score_dump += 2
        reasons_d.append(f"Long Cascade: {l_liq:.1f} BTC liquidated")

    if path_up:
        score_pump += 2
        reasons_p.append(f"OB Path Clear UP: {ob_ratio:.1f}x")
    if path_down:
        score_dump += 2
        reasons_d.append(f"OB Path Clear DOWN: {ob_ratio:.1f}x")

    return {
        'price'      : price,
        'price_move' : price_move,
        'score_pump' : score_pump,
        'score_dump' : score_dump,
        'reasons_p'  : reasons_p,
        'reasons_d'  : reasons_d,
        'fr_now'     : fr_now,
        'ls_now'     : ls_now,
        'oi_move'    : oi_move,
        'ob_ratio'   : ob_ratio
    }

# ==================== MAIN ====================
print("HRP DIVERGENCE ENGINE: ONLINE")
send("⚡ HRP DIVERGENCE ENGINE ONLINE!\nFunding Rate Divergence Tracker Active!")

last_alert = 0

while True:
    try:
        d     = detect_divergence()
        price = d['price']

        print(f"\rBTC: ${price:,.0f} | Pump:{d['score_pump']}/11 | Dump:{d['score_dump']}/11 | FR:{d['fr_now']:.4f}%", end="")

        # PUMP SIGNAL (500-1000 point UP)
        if d['score_pump'] >= 7 and time.time() - last_alert > 900:

            atr_val = 300  # Approximate BTC move
            sl  = price - atr_val
            tp1 = price + (atr_val * 2)
            tp2 = price + (atr_val * 4)

            msg = f"""
⚡ HRP PRIME: 500-1000 POINT MOVE!

🚀 DIRECTION: LONG (PUMP)
💰 Price: ${price:,.2f}
💪 Score: {d['score_pump']}/11

📋 LIMIT ORDER:
Entry    : ${price:,.2f}
Stop Loss: ${sl:,.2f}
TP1 (50%): ${tp1:,.2f}
TP2 (50%): ${tp2:,.2f}

🔍 DIVERGENCE SIGNALS:
{chr(10).join(['✅ ' + r for r in d['reasons_p']])}

⏳ Move: 30-90 min mein!
            """
            send(msg)
            last_alert = time.time()
            print(f"\n🚀 PUMP ALERT!")

        # DUMP SIGNAL (500-1000 point DOWN)
        elif d['score_dump'] >= 7 and time.time() - last_alert > 900:

            atr_val = 300
            sl  = price + atr_val
            tp1 = price - (atr_val * 2)
            tp2 = price - (atr_val * 4)

            msg = f"""
⚡ HRP PRIME: 500-1000 POINT MOVE!

🔻 DIRECTION: SHORT (DUMP)
💰 Price: ${price:,.2f}
💪 Score: {d['score_dump']}/11

📋 LIMIT ORDER:
Entry    : ${price:,.2f}
Stop Loss: ${sl:,.2f}
TP1 (50%): ${tp1:,.2f}
TP2 (50%): ${tp2:,.2f}

🔍 DIVERGENCE SIGNALS:
{chr(10).join(['✅ ' + r for r in d['reasons_d']])}

⏳ Move: 30-90 min mein!
            """
            send(msg)
            last_alert = time.time()
            print(f"\n🔻 DUMP ALERT!")

        time.sleep(30)

    except Exception as e:
        print(f"\nError: {e}")
        time.sleep(60)
