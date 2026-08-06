"""
ULTIMATE DAILY SIGNAL BOT - FIXED VERSION
- Har Din Signal Aayega
- Gmail Alert
- 24/7 Render Pe
- Score 8+ pe signal
- Har ghante scan
"""

import requests
import pandas as pd
import numpy as np
import time
import smtplib
import threading
from email.message import EmailMessage
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== CONFIG ====================
EMAIL    = "himanshurajoriya12895@gmail.com"
APP_PASS = "bpjm fspb ttcw tlru"
SYMBOL   = "BTCUSDT"

# ==================== RENDER SERVER ====================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Running 24/7!")
    def log_message(self, *args):
        pass

threading.Thread(
    target=lambda: HTTPServer(('0.0.0.0', 10000), Handler).serve_forever(),
    daemon=True
).start()

# ==================== DATA ====================
def get_ohlcv(interval='1h', limit=100):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={interval}&limit={limit}"
        r   = requests.get(url, timeout=15)
        df  = pd.DataFrame(r.json(), columns=[
            'ts','open','high','low','close','volume',
            'ct','qv','t','bb','bq','i'
        ])
        for col in ['open','high','low','close','volume']:
            df[col] = df[col].astype(float)
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
        return df
    except:
        return pd.DataFrame()

def get_price():
    try:
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}",
            timeout=10
        )
        return float(r.json()['price'])
    except:
        return 0.0

def get_funding_rate():
    try:
        r = requests.get(
            f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={SYMBOL}&limit=1",
            timeout=10
        )
        return float(r.json()[-1]['fundingRate']) * 100
    except:
        return 0.0

def get_long_short_ratio():
    try:
        r = requests.get(
            f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={SYMBOL}&period=1h&limit=2",
            timeout=10
        )
        return float(r.json()[-1]['longShortRatio'])
    except:
        return 1.0

def get_whale_flow():
    try:
        r   = requests.get(
            f"https://api.binance.com/api/v3/aggTrades?symbol={SYMBOL}&limit=1000",
            timeout=10
        )
        df  = pd.DataFrame(r.json())
        df['qty']  = df['q'].astype(float)
        df['side'] = df['m'].apply(lambda x: "SELL" if x else "BUY")
        big        = df[df['qty'] >= 3.0]
        buy_vol    = big[big['side'] == "BUY"]['qty'].sum()
        sell_vol   = big[big['side'] == "SELL"]['qty'].sum()
        return buy_vol, sell_vol
    except:
        return 0, 0

def get_fear_greed():
    try:
        r = requests.get(
            "https://api.alternative.me/fng/?limit=1",
            timeout=10
        )
        return int(r.json()['data'][0]['value'])
    except:
        return 50

# ==================== INDICATORS ====================
def calc_ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def calc_rsi(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0).rolling(p).mean()
    l = (-d.where(d < 0, 0)).rolling(p).mean()
    return 100 - (100 / (1 + g/l))

def calc_atr(df, p=14):
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low']  - df['close'].shift())
    ], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def calc_macd(s):
    m   = calc_ema(s, 12) - calc_ema(s, 26)
    sig = calc_ema(m, 9)
    return m, sig, m - sig

def calc_bb(s, p=20):
    sma = s.rolling(p).mean()
    std = s.rolling(p).std()
    return sma + std*2, sma, sma - std*2

# ==================== SIGNAL ====================
def generate_signal():
    df_1d  = get_ohlcv('1d', 100)
    df_4h  = get_ohlcv('4h', 100)
    df_1h  = get_ohlcv('1h', 100)
    price  = get_price()
    fr     = get_funding_rate()
    ls     = get_long_short_ratio()
    fg     = get_fear_greed()
    wb, ws = get_whale_flow()

    if df_1h.empty or price == 0:
        return None

    score_long  = 0
    score_short = 0
    reasons     = []

    # 1. DAILY TREND
    if not df_1d.empty:
        ema200_d = calc_ema(df_1d['close'], 200).iloc[-1]
        ema50_d  = calc_ema(df_1d['close'], 50).iloc[-1]
        if price > ema200_d:
            score_long += 2
            reasons.append("✅ Daily Bullish Trend")
        else:
            score_short += 2
            reasons.append("✅ Daily Bearish Trend")
        if ema50_d > ema200_d:
            score_long += 1
            reasons.append("✅ Golden Cross")
        else:
            score_short += 1
            reasons.append("✅ Death Cross")

    # 2. 4H STRUCTURE
    if not df_4h.empty:
        ema21_4h = calc_ema(df_4h['close'], 21).iloc[-1]
        rsi_4h   = calc_rsi(df_4h['close']).iloc[-1]
        rsi_prev = calc_rsi(df_4h['close']).iloc[-2]
        if price > ema21_4h:
            score_long += 2
            reasons.append("✅ 4H Bullish")
        else:
            score_short += 2
            reasons.append("✅ 4H Bearish")
        if rsi_4h < 35:
            score_long += 2
            reasons.append(f"✅ RSI Oversold: {rsi_4h:.0f}")
        elif rsi_4h > 65:
            score_short += 2
            reasons.append(f"✅ RSI Overbought: {rsi_4h:.0f}")
        elif rsi_4h > rsi_prev:
            score_long += 1
            reasons.append(f"✅ RSI Rising: {rsi_4h:.0f}")
        else:
            score_short += 1
            reasons.append(f"✅ RSI Falling: {rsi_4h:.0f}")

    # 3. WHALE FLOW
    total_whale = wb + ws
    if total_whale > 10:
        if wb > ws * 1.5:
            score_long += 2
            reasons.append(f"✅ Whale Buying: {wb:.1f} BTC")
        elif ws > wb * 1.5:
            score_short += 2
            reasons.append(f"✅ Whale Selling: {ws:.1f} BTC")

    # 4. FUNDING RATE
    if fr < -0.02:
        score_long += 2
        reasons.append(f"✅ Funding Negative: {fr:.3f}%")
    elif fr > 0.02:
        score_short += 2
        reasons.append(f"✅ Funding Positive: {fr:.3f}%")

    # 5. LONG/SHORT
    if ls > 1.5:
        score_short += 2
        reasons.append(f"✅ Longs Overcrowded: {ls:.2f}")
    elif ls < 0.7:
        score_long += 2
        reasons.append(f"✅ Shorts Overcrowded: {ls:.2f}")

    # 6. FEAR GREED
    if fg < 30:
        score_long += 2
        reasons.append(f"✅ Fear Zone: {fg}")
    elif fg > 70:
        score_short += 2
        reasons.append(f"✅ Greed Zone: {fg}")

    # 7. MACD
    _, _, hist = calc_macd(df_1h['close'])
    if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]:
        score_long += 1
        reasons.append("✅ MACD Bullish")
    elif hist.iloc[-1] < 0 and hist.iloc[-1] < hist.iloc[-2]:
        score_short += 1
        reasons.append("✅ MACD Bearish")

    # 8. BOLLINGER BANDS
    bb_upper, bb_mid, bb_lower = calc_bb(df_1h['close'])
    if price < bb_lower.iloc[-1]:
        score_long += 2
        reasons.append("✅ Below BB (Oversold)")
    elif price > bb_upper.iloc[-1]:
        score_short += 2
        reasons.append("✅ Above BB (Overbought)")
    elif price > bb_mid.iloc[-1]:
        score_long += 1
        reasons.append("✅ Above BB Mid")
    else:
        score_short += 1
        reasons.append("✅ Below BB Mid")

    # ===== DECISION =====
    # Score 8+ chahiye
    direction = None
    score     = 0

    if score_long >= 8 and score_long > score_short:
        direction = 'LONG'
        score     = score_long
    elif score_short >= 8 and score_short > score_long:
        direction = 'SHORT'
        score     = score_short

    if not direction:
        return None

    # LEVELS
    atr_val  = calc_atr(df_1h).iloc[-1]
    atr_pct  = (atr_val / price) * 100

    if direction == 'LONG':
        sl  = price - (atr_val * 2.0)
        tp1 = price + (atr_val * 3.0)
        tp2 = price + (atr_val * 5.0)
    else:
        sl  = price + (atr_val * 2.0)
        tp1 = price - (atr_val * 3.0)
        tp2 = price - (atr_val * 5.0)

    risk     = abs(price - sl)
    rr1      = abs(tp1 - price) / risk if risk > 0 else 0
    rr2      = abs(tp2 - price) / risk if risk > 0 else 0
    risk_pct = (risk / price) * 100

    return {
        'direction'  : direction,
        'price'      : price,
        'sl'         : sl,
        'tp1'        : tp1,
        'tp2'        : tp2,
        'score'      : score,
        'score_long' : score_long,
        'score_short': score_short,
        'reasons'    : reasons,
        'rr1'        : rr1,
        'rr2'        : rr2,
        'risk_pct'   : risk_pct,
        'atr_pct'    : atr_pct,
        'fg'         : fg,
        'fr'         : fr,
        'ls'         : ls
    }

# ==================== GMAIL ====================
def send_gmail(sig):
    try:
        d = sig['direction']
        msg = EmailMessage()
        msg.set_content(f"""
{'🚀 LONG' if d=='LONG' else '🔻 SHORT'} SIGNAL!

━━━━━━━━━━━━━━━━━━━━━
💰 Price   : ${sig['price']:,.2f}
🛑 SL      : ${sig['sl']:,.2f} (-{sig['risk_pct']:.1f}%)
🎯 TP1     : ${sig['tp1']:,.2f} (1:{sig['rr1']:.1f})
🎯 TP2     : ${sig['tp2']:,.2f} (1:{sig['rr2']:.1f})
━━━━━━━━━━━━━━━━━━━━━
Score      : {sig['score']}/20
ATR        : {sig['atr_pct']:.2f}%
Fear/Greed : {sig['fg']}
Funding    : {sig['fr']:.3f}%
L/S Ratio  : {sig['ls']:.2f}
━━━━━━━━━━━━━━━━━━━━━
REASONS:
{chr(10).join(sig['reasons'])}
━━━━━━━━━━━━━━━━━━━━━
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} IST
        """)
        msg['Subject'] = f"🚨 BTC {d} - Score:{sig['score']}/20 - ${sig['price']:,.0f}"
        msg['From']    = EMAIL
        msg['To']      = EMAIL
        s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        s.login(EMAIL, APP_PASS)
        s.send_message(msg)
        s.quit()
        print(f"✅ Gmail Sent! {d} @ ${sig['price']:,.0f}")
        return True
    except Exception as e:
        print(f"❌ Gmail Error: {e}")
        return False

# ==================== MAIN ====================
print("🚀 Bot Started - 24/7 Active!")
print(f"📧 Gmail: {EMAIL}")

last_alert_date = ""

while True:
    try:
        now   = datetime.utcnow()
        today = now.strftime('%Y-%m-%d')

        # IST Time
        ist_h = (now.hour + 5) % 24
        ist_m = now.minute + 30
        if ist_m >= 60:
            ist_h = (ist_h + 1) % 24
            ist_m -= 60

        print(f"\r⏰ {ist_h:02d}:{ist_m:02d} IST | Signal: {'✅ SENT' if last_alert_date == today else '⏳ WAITING'}", end="")

        # New day = reset
        if last_alert_date != today:
            print(f"\n🔍 Scanning...")
            sig = generate_signal()

            if sig:
                print(f"\n🎯 Signal: {sig['direction']} | Score: {sig['score']}/20")
                if send_gmail(sig):
                    last_alert_date = today
            else:
                print(f"\n⏳ Score too low | Long:{sig['score_long'] if sig else 0} Short:{sig['score_short'] if sig else 0}")

        # Har 1 ghante mein scan
        time.sleep(3600)

    except Exception as e:
        print(f"\nError: {e}")
        time.sleep(60)
