import requests
import pandas as pd
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

TG_TOKEN   = "8966743878:AAFRB2rB7nxM8eMQN5Om6_veQ4Ow2m8lIo4"
TG_CHAT_ID = "8193076289"
SYMBOL     = "BTCUSDT"

# Render server
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"HRP: ONLINE")
    def log_message(self, *args): pass

threading.Thread(
    target=lambda: HTTPServer(('0.0.0.0', 10000), Handler).serve_forever(),
    daemon=True
).start()

def send_tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
        print("✅ Telegram sent!")
    except Exception as e:
        print(f"❌ TG Error: {e}")

def get_price():
    """Multiple sources try karo"""
    
    # Source 1: Binance
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}
        ).json()
        if 'price' in r:
            return float(r['price'])
    except:
        pass
    
    # Source 2: Binance US
    try:
        r = requests.get(
            "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=10
        ).json()
        if 'price' in r:
            return float(r['price'])
    except:
        pass
    
    # Source 3: CoinGecko
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=10
        ).json()
        return float(r['bitcoin']['usd'])
    except:
        pass
    
    # Source 4: Kraken
    try:
        r = requests.get(
            "https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
            timeout=10
        ).json()
        return float(r['result']['XXBTZUSD']['c'][0])
    except:
        pass
    
    return 0.0

def get_data():
    """Data fetch with fallback"""
    try:
        # Order Book
        depth = requests.get(
            "https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=500",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}
        ).json()
        
        if 'bids' not in depth:
            return None
            
        bid_vol = sum(float(q) for p,q in depth['bids'])
        ask_vol = sum(float(q) for p,q in depth['asks'])
        ob_ratio = bid_vol / (ask_vol + 0.001)

        # Trades
        trades = requests.get(
            "https://api.binance.com/api/v3/aggTrades?symbol=BTCUSDT&limit=1000",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}
        ).json()
        
        if not isinstance(trades, list):
            return None
            
        df = pd.DataFrame(trades)
        df['qty']   = df['q'].astype(float)
        
        buy_v    = df[df['m']==False]['qty'].sum()
        sell_v   = df[df['m']==True]['qty'].sum()
        buy_pct  = buy_v / (buy_v + sell_v + 0.001) * 100
        recent   = df.tail(100)['qty'].sum()
        avg      = df['qty'].sum() / 10
        velocity = recent / (avg + 0.001)

        return {
            'ob_ratio': ob_ratio,
            'velocity': velocity,
            'buy_pct' : buy_pct,
            'buy_v'   : buy_v,
            'sell_v'  : sell_v
        }
    except Exception as e:
        print(f"Data error: {e}")
        return None

# ==================== START ====================
print("HRP MASTERMIND: STARTING...")

# Test price
price = get_price()
if price > 0:
    print(f"✅ Price OK: ${price:,.2f}")
    send_tg(f"⚡ <b>HRP MASTERMIND ONLINE!</b>\n\nBTC: ${price:,.2f}\nBot chal gaya!\nSignal ka wait kar...")
else:
    print("❌ Price fetch failed!")
    send_tg("⚠️ Bot started but price fetch issue hai. Monitoring...")

last_alert = 0

# ==================== MAIN LOOP ====================
while True:
    try:
        price = get_price()
        data  = get_data()

        if price > 0 and data:
            ob_ratio = data['ob_ratio']
            velocity = data['velocity']
            buy_pct  = data['buy_pct']

            print(f"\rBTC: ${price:,.2f} | OB: {ob_ratio:.1f}x | Vel: {velocity:.1f}x | Buy: {buy_pct:.0f}%", end="")

            # LONG
            if (ob_ratio > 2.0 and
                velocity > 3.0 and
                buy_pct > 62 and
                time.time() - last_alert > 600):

                sl  = price * 0.993
                tp1 = price * 1.025
                tp2 = price * 1.045

                send_tg(f"""
🚀 <b>HRP PRIME: LONG!</b>

💰 Price : ${price:,.2f}
🛑 SL    : ${sl:,.2f}
🎯 TP1   : ${tp1:,.2f}
🎯 TP2   : ${tp2:,.2f}

📊 OB    : {ob_ratio:.1f}x
⚡ Vel   : {velocity:.1f}x
🐋 Buy   : {buy_pct:.0f}%
                """)
                last_alert = time.time()
                print(f"\n🚀 LONG sent!")

            # SHORT
            elif (ob_ratio < 0.5 and
                  velocity > 3.0 and
                  buy_pct < 38 and
                  time.time() - last_alert > 600):

                sl  = price * 1.007
                tp1 = price * 0.975
                tp2 = price * 0.955

                send_tg(f"""
🔻 <b>HRP PRIME: SHORT!</b>

💰 Price : ${price:,.2f}
🛑 SL    : ${sl:,.2f}
🎯 TP1   : ${tp1:,.2f}
🎯 TP2   : ${tp2:,.2f}

📊 OB    : {ob_ratio:.1f}x
⚡ Vel   : {velocity:.1f}x
🐻 Sell  : {100-buy_pct:.0f}%
                """)
                last_alert = time.time()
                print(f"\n🔻 SHORT sent!")

        else:
            print(f"\rData fetch issue - retrying...", end="")

        time.sleep(15)

    except Exception as e:
        print(f"\nError: {e}")
        time.sleep(30)
