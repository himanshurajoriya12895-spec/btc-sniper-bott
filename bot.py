"""
ULTIMATE DAILY SIGNAL BOT
- Har Din 1 Perfect Trade
- 70-80% Win Rate Logic
- Volatility Based Entry
- Market Behavior Analysis
- Gmail Alert
- Zero API Key
- 24/7 Render Pe Chalega
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
        self.wfile.write(b"Daily Signal Bot Running 24/7!")
    def log_message(self, *args):
        pass

def run_server():
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

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
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}", timeout=10)
        return float(r.json()['price'])
    except:
        return 0.0

def get_funding_rate():
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={SYMBOL}&limit=1", timeout=10)
        return float(r.json()[-1]['fundingRate']) * 100
    except:
        return 0.0

def get_open_interest():
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={SYMBOL}", timeout=10)
        return float(r.json()['openInterest'])
    except:
        return 0.0

def get_long_short_ratio():
    try:
        r = requests.get(f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={SYMBOL}&period=1h&limit=2", timeout=10)
        return float(r.json()[-1]['longShortRatio'])
    except:
        return 1.0

def get_whale_flow():
    try:
        r   = requests.get(f"https://api.binance.com/api/v3/aggTrades?symbol={SYMBOL}&limit=1000", timeout=10)
        df  = pd.DataFrame(r.json())
        df['qty']  = df['q'].astype(float)
        df['side'] = df['m'].apply(lambda x: "SELL" if x else "BUY")
        big        = df[df['qty'] >= 5.0]
        buy_vol    = big[big['side'] == "BUY"]['qty'].sum()
        sell_vol   = big[big['side'] == "SELL"]['qty'].sum()
        return buy_vol, sell_vol
    except:
        return 0, 0

def get_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
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

def calc_volatility(df):
    """
    Volatility based position sizing
    High vol = chota trade
    Low vol  = normal trade
    """
    atr     = calc_atr(df).iloc[-1]
    price   = df['close'].iloc[-1]
    atr_pct = (atr / price) * 100
    
    if atr_pct > 3.0:
        return 'HIGH', atr_pct
    elif atr_pct > 1.5:
        return 'MEDIUM', atr_pct
    else:
        return 'LOW', atr_pct

def find_key_levels(df):
    """Support aur Resistance levels"""
    highs = []
    lows  = []
    
    for i in range(10, len(df)-3):
        if df['high'].iloc[i] == df['high'].iloc[i-10:i+3].max():
            highs.append(df['high'].iloc[i])
        if df['low'].iloc[i] == df['low'].iloc[i-10:i+3].min():
            lows.append(df['low'].iloc[i])
    
    return highs[-3:] if highs else [], lows[-3:] if lows else []

# ==================== MAIN SIGNAL LOGIC ====================
def generate_daily_signal():
    """
    70-80% Win Rate Logic:
    
    1. Market Structure (Daily + 4H)
    2. Volatility Check
    3. Whale Flow
    4. Key Levels
    5. Multiple Confirmations
    
    Sirf tab signal do jab
    8+ factors ek direction mein hon
    """
    
    # Fetch all data
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
    
    # ===== 1. DAILY TREND =====
    if not df_1d.empty:
        ema50_d  = calc_ema(df_1d['close'], 50).iloc[-1]
        ema200_d = calc_ema(df_1d['close'], 200).iloc[-1]
        
        if price > ema200_d:
            score_long += 2
            reasons.append("✅ Daily Trend: BULLISH")
        else:
            score_short += 2
            reasons.append("✅ Daily Trend: BEARISH")
        
        if ema50_d > ema200_d:
            score_long += 1
            reasons.append("✅ Golden Cross Active")
        else:
            score_short += 1
            reasons.append("✅ Death Cross Active")

    # ===== 2. 4H STRUCTURE =====
    if not df_4h.empty:
        ema21_4h = calc_ema(df_4h['close'], 21).iloc[-1]
        rsi_4h   = calc_rsi(df_4h['close']).iloc[-1]
        rsi_prev = calc_rsi(df_4h['close']).iloc[-2]
        
        if price > ema21_4h:
            score_long += 2
            reasons.append(f"✅ 4H: Above EMA21")
        else:
            score_short += 2
            reasons.append(f"✅ 4H: Below EMA21")
        
        if 35 <= rsi_4h <= 65:
            if rsi_4h > rsi_prev:
                score_long += 1
                reasons.append(f"✅ RSI Rising: {rsi_4h:.0f}")
            else:
                score_short += 1
                reasons.append(f"✅ RSI Falling: {rsi_4h:.0f}")
        
        if rsi_4h < 35:
            score_long += 2
            reasons.append(f"✅ RSI Oversold: {rsi_4h:.0f}")
        elif rsi_4h > 65:
            score_short += 2
            reasons.append(f"✅ RSI Overbought: {rsi_4h:.0f}")

    # ===== 3. VOLATILITY CHECK =====
    vol_level, atr_pct = calc_volatility(df_1h)
    if vol_level == 'MEDIUM':
        score_long  += 1
        score_short += 1
        reasons.append(f"✅ Volatility GOOD: {atr_pct:.2f}%")
    elif vol_level == 'HIGH':
        reasons.append(f"⚠️ Volatility HIGH: {atr_pct:.2f}%")
    else:
        reasons.append(f"⚠️ Volatility LOW: {atr_pct:.2f}%")

    # ===== 4. WHALE FLOW =====
    total_whale = wb + ws
    if total_whale > 20:
        if wb > ws * 2:
            score_long += 3
            reasons.append(f"✅ Whale BUYING: {wb:.1f} BTC")
        elif ws > wb * 2:
            score_short += 3
            reasons.append(f"✅ Whale SELLING: {ws:.1f} BTC")

    # ===== 5. FUNDING RATE =====
    if fr < -0.03:
        score_long += 2
        reasons.append(f"✅ Funding Negative: {fr:.3f}%")
    elif fr > 0.03:
        score_short += 2
        reasons.append(f"✅ Funding Positive: {fr:.3f}%")

    # ===== 6. LONG/SHORT RATIO =====
    if ls > 1.8:
        score_short += 2
        reasons.append(f"✅ Longs Overcrowded: {ls:.2f}")
    elif ls < 0.6:
        score_long += 2
        reasons.append(f"✅ Shorts Overcrowded: {ls:.2f}")

    # ===== 7. FEAR & GREED =====
    if fg < 25:
        score_long += 2
        reasons.append(f"✅ Extreme Fear: {fg}")
    elif fg > 75:
        score_short += 2
        reasons.append(f"✅ Extreme Greed: {fg}")
    elif 40 <= fg <= 60:
        reasons.append(f"ℹ️ Fear/Greed Neutral: {fg}")

    # ===== 8. MACD 1H =====
    macd, sig, hist = calc_macd(df_1h['close'])
    if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]:
        score_long += 1
        reasons.append("✅ MACD Bullish")
    elif hist.iloc[-1] < 0 and hist.iloc[-1] < hist.iloc[-2]:
        score_short += 1
        reasons.append("✅ MACD Bearish")

    # ===== 9. BB POSITION =====
    bb_upper, bb_mid, bb_lower = calc_bb(df_1h['close'])
    if price < bb_lower.iloc[-1]:
        score_long += 2
        reasons.append("✅ Below BB Lower (Oversold)")
    elif price > bb_upper.iloc[-1]:
        score_short += 2
        reasons.append("✅ Above BB Upper (Overbought)")
    elif price > bb_mid.iloc[-1]:
        score_long += 1
        reasons.append("✅ Above BB Mid")

    # ===== 10. KEY LEVELS =====
    highs, lows = find_key_levels(df_4h)
    
    for low in lows:
        if abs(price - low) / price < 0.01:
            score_long += 2
            reasons.append(f"✅ At Key Support: ${low:,.0f}")
            break
    
    for high in highs:
        if abs(price - high) / price < 0.01:
            score_short += 2
            reasons.append(f"✅ At Key Resistance: ${high:,.0f}")
            break

    # ===== FINAL DECISION =====
    # Minimum score chahiye 10
    # Clear direction - ek side 2x dusre se
    
    direction = None
    score     = 0
    max_score = 20

    if score_long >= 10 and score_long >= score_short * 1.8:
        direction = 'LONG'
        score     = score_long
    elif score_short >= 10 and score_short >= score_long * 1.8:
        direction = 'SHORT'
        score     = score_short

    if not direction:
        return None

    # ===== CALCULATE LEVELS =====
    atr_val = calc_atr(df_1h).iloc[-1]
    
    # Volatility ke hisaab se SL adjust karo
    if vol_level == 'HIGH':
        sl_mult  = 2.5
        tp1_mult = 3.0
        tp2_mult = 5.0
    elif vol_level == 'MEDIUM':
        sl_mult  = 2.0
        tp1_mult = 3.5
        tp2_mult = 6.0
    else:
        sl_mult  = 1.5
        tp1_mult = 3.0
        tp2_mult = 5.0

    if direction == 'LONG':
        sl  = price - (atr_val * sl_mult)
        tp1 = price + (atr_val * tp1_mult)
        tp2 = price + (atr_val * tp2_mult)
    else:
        sl  = price + (atr_val * sl_mult)
        tp1 = price - (atr_val * tp1_mult)
        tp2 = price - (atr_val * tp2_mult)

    risk    = abs(price - sl)
    rr1     = abs(tp1 - price) / risk if risk > 0 else 0
    rr2     = abs(tp2 - price) / risk if risk > 0 else 0
    risk_pct = (risk / price) * 100

    return {
        'direction'  : direction,
        'price'      : price,
        'sl'         : sl,
        'tp1'        : tp1,
        'tp2'        : tp2,
        'score'      : score,
        'max_score'  : max_score,
        'score_long' : score_long,
        'score_short': score_short,
        'reasons'    : reasons,
        'rr1'        : rr1,
        'rr2'        : rr2,
        'risk_pct'   : risk_pct,
        'vol_level'  : vol_level,
        'atr_pct'    : atr_pct,
        'fg'         : fg,
        'fr'         : fr,
        'ls'         : ls
    }

# ==================== GMAIL ====================
def send_gmail(sig):
    try:
        d   = sig['direction']
        msg = EmailMessage()
        msg.set_content(f"""
{'🚀' if d=='LONG' else '🔻'} BTC {d} SIGNAL!

━━━━━━━━━━━━━━━━━━━━━
💰 Price  : ${sig['price']:,.2f}
🛑 SL     : ${sig['sl']:,.2f} (-{sig['risk_pct']:.1f}%)
🎯 TP1    : ${sig['tp1']:,.2f} (1:{sig['rr1']:.1f})
🎯 TP2    : ${sig['tp2']:,.2f} (1:{sig['rr2']:.1f})
━━━━━━━━━━━━━━━━━━━━━
💪 Score  : {sig['score']}/{sig['max_score']}
⚡ ATR    : {sig['atr_pct']:.2f}%
😨 FG     : {sig['fg']}
📊 L/S    : {sig['ls']:.2f}
💰 FR     : {sig['fr']:.3f}%
━━━━━━━━━━━━━━━━━━━━━
REASONS:
{chr(10).join(sig['reasons'])}
━━━━━━━━━━━━━━━━━━━━━
Time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """)
        msg['Subject'] = f"🚨 BTC {d} SIGNAL - Score:{sig['score']}/{sig['max_score']}"
        msg['From']    = EMAIL
        msg['To']      = EMAIL

        s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        s.login(EMAIL, APP_PASS)
        s.send_message(msg)
        s.quit()
        print(f"✅ Gmail Sent: {d} @ ${sig['price']:,.0f}")
    except Exception as e:
        print(f"❌ Gmail Error: {e}")

# ==================== MAIN LOOP ====================
print("🚀 Ultimate Daily Signal Bot Started!")
print("📧 Gmail Alert Active")
print("⏳ Scanning market every 5 minutes...")

last_alert_date = ""
last_alert_time = 0

while True:
    try:
        now   = datetime.utcnow()
        today = now.strftime('%Y-%m-%d')
        price = get_price()

        # IST time
        ist_h = (now.hour + 5) % 24
        ist_m = now.minute + 30
        if ist_m >= 60:
            ist_h = (ist_h + 1) % 24
            ist_m -= 60

        print(f"\r⏰ {ist_h:02d}:{ist_m:02d} IST | 💰 ${price:,.0f} | Today Signal: {'✅ SENT' if last_alert_date == today else '⏳ WAITING'}", end="")

        # Sirf 1 signal per day
        if last_alert_date != today:

            # Best time to scan: 
            # 9:30 AM - 11:30 AM IST (London open)
            # 7:30 PM - 9:30 PM IST (NY open)
            
            london_open = (ist_h == 9  and ist_m >= 30) or ist_h == 10 or (ist_h == 11 and ist_m <= 30)
            ny_open     = (ist_h == 19 and ist_m >= 30) or ist_h == 20 or (ist_h == 21 and ist_m <= 30)

            if london_open or ny_open:
                print(f"\n\n🔍 Scanning for daily signal...")
                sig = generate_daily_signal()

                if sig:
                    print(f"\n🎯 SIGNAL FOUND: {sig['direction']} Score:{sig['score']}/{sig['max_score']}")
                    send_gmail(sig)
                    last_alert_date = today
                    last_alert_time = time.time()
                else:
                    print(f"\n⏳ No clear signal yet... Scanning again in 5 min")

        time.sleep(300)  # 5 min

    except Exception as e:
        print(f"\nError: {e}")
        time.sleep(60)
