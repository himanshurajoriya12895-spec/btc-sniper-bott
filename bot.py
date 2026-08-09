import requests
import pandas as pd
import time

TOKEN = "8966743878:AAFRB2rB7nxM8eMQN5Om6_veQ4Ow2m8lIo4"
CHAT_ID = "8193076289"
SYMBOL = "BTCUSDT"

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )

print("HRP ENGINE ONLINE ✅")
send("✅ HRP PRIME ENGINE STARTED ✅")

last = 0

while True:
    try:
        trades = requests.get(
            f"https://api.binance.com/api/v3/aggTrades?symbol={SYMBOL}&limit=1000"
        ).json()

        buy = sum(float(x['q']) for x in trades if not x['m'])
        sell = sum(float(x['q']) for x in trades if x['m'])
        price = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"
        ).json()['price']

        if buy > sell * 2.5 and time.time() - last > 900:
            send(f"🚀 STRONG BUY @ ${price}")
            last = time.time()

        elif sell > buy * 2.5 and time.time() - last > 900:
            send(f"🔻 STRONG SELL @ ${price}")
            last = time.time()

        time.sleep(15)

    except:
        time.sleep(30)
