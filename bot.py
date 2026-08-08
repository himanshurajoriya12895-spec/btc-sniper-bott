import requests
import pandas as pd
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

TG_TOKEN   = "8966743878:AAFRB2rB7nxM8eMQN5Om6_veQ4Ow2m8lIo4"    # Apna daal
TG_CHAT_ID = "8193076289"  # Apna daal
SYMBOL     = "BTCUSDT"

# Render ke liye
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
        print("✅ Telegram message sent!")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def get_data():
    # Order Book
    depth   = requests.get(f"https://api.binance.com/api/v3/depth?symbol={SYMBOL}&limit=500").json()
    bid_vol = sum(float(q) for p,q in depth['bids'])
    ask_vol = sum(float(q) for p,q in depth['asks'])
    ob_ratio= bid_vol / (ask_vol + 0.001)

    # Trades
    trades   = requests.get(f"https://api.binance.com/api/v3/aggTrades?symbol={SYMBOL}&limit=1000").json()
    df       = pd.DataFrame(trades)
    df['qty']   = df['q'].astype(float)
    df['price'] = df['p'].astype(float)
    buy_v    = df[df['m']==False]['qty'].sum()
    sell_v   = df[df['m']==True]['qty'].sum()
    price    = float(df['price'].iloc[-1])
    recent   = df.tail(100)['qty'].sum()
    avg      = df['qty'].sum() / 10
    velocity = recent / (avg + 0.001)
    buy_pct  = buy_v / (buy_v + sell_v + 0.001) * 100

    return ob_ratio, velocity, buy_pct, price, bid_vol, ask_vol, buy_v, sell_v

# ==================== START ====================
print("HRP MASTERMIND: STARTING...")

# Pehle turant test message bhejo
price = float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}").json()['price'])
send_tg(f"⚡ <b>HRP MASTERMIND ONLINE!</b>\n\nBTC: ${price:,.2f}\nBot chal gaya!\nSignal aate hi bataunga...")
print(f"✅ Bot started! BTC: ${price:,.2f}")

last_alert = 0

# ==================== MAIN LOOP ====================
while True:
    try:
        ob_ratio, velocity, buy_pct, price, bid_vol, ask_vol, buy_v, sell_v = get_data()

        print(f"\rBTC: ${price:,.2f} | OB: {ob_ratio:.1f}x | Vel: {velocity:.1f}x | Buy: {buy_pct:.0f}%", end="")

        # LONG Signal
        if (ob_ratio > 2.0 and
            velocity > 3.0 and
            buy_pct > 62 and
            time.time() - last_alert > 600):

            sl  = price * 0.993
            tp1 = price * 1.025
            tp2 = price * 1.045

            send_tg(f"""
🚀 <b>HRP PRIME: LONG SIGNAL!</b>

💰 Price  : ${price:,.2f}
🛑 SL     : ${sl:,.2f}
🎯 TP1    : ${tp1:,.2f}
🎯 TP2    : ${tp2:,.2f}

📊 OB Ratio  : {ob_ratio:.1f}x
⚡ Velocity  : {velocity:.1f}x
🐋 Buy Vol   : {buy_pct:.0f}%

Move Expected: 30-60 min!
            """)
            last_alert = time.time()
            print(f"\n🚀 LONG Signal sent!")

        # SHORT Signal
        elif (ob_ratio < 0.5 and
              velocity > 3.0 and
              buy_pct < 38 and
              time.time() - last_alert > 600):

            sl  = price * 1.007
            tp1 = price * 0.975
            tp2 = price * 0.955

            send_tg(f"""
🔻 <b>HRP PRIME: SHORT SIGNAL!</b>

💰 Price  : ${price:,.2f}
🛑 SL     : ${sl:,.2f}
🎯 TP1    : ${tp1:,.2f}
🎯 TP2    : ${tp2:,.2f}

📊 OB Ratio  : {ob_ratio:.1f}x
⚡ Velocity  : {velocity:.1f}x
🐻 Sell Vol  : {100-buy_pct:.0f}%

Move Expected: 30-60 min!
            """)
            last_alert = time.time()
            print(f"\n🔻 SHORT Signal sent!")

        time.sleep(15)

    except Exception as e:
        print(f"\nError: {e}")
        time.sleep(30)
