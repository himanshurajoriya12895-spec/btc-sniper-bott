import requests
import pandas as pd
import time
import smtplib
from email.message import EmailMessage
from datetime import datetime

EMAIL    = "himanshurajoriya12895@gmail.com"
APP_PASS = "bpjm fspb ttcw tlru"

print("SnipX-90 Bot Started 24/7...")
last_alert = 0

while True:
    try:
        r    = requests.get("https://api.binance.com/api/v3/aggTrades?symbol=BTCUSDT&limit=1000").json()
        df   = pd.DataFrame(r)
        df['qty']  = df['q'].astype(float)
        df['side'] = df['m'].apply(lambda x: "SELL" if x else "BUY")

        buy_vol  = df[df['side'] == "BUY"]['qty'].sum()
        sell_vol = df[df['side'] == "SELL"]['qty'].sum()
        delta    = buy_vol - sell_vol
        price    = float(requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()['price'])

        if (buy_vol > sell_vol * 2.5 or sell_vol > buy_vol * 2.5) and (time.time() - last_alert > 1800):
            direction = "STRONG BUY 🚀" if buy_vol > sell_vol else "STRONG SELL 🔻"
            
            msg = EmailMessage()
            msg.set_content(f"""
BTC {direction} Signal!

Price  : ${price:,.2f}
Delta  : {delta:.2f} BTC
Time   : {datetime.now().strftime('%H:%M:%S')}

Ye signal institutional 
move indicate kar raha hai.
Entry le sakte ho!
            """)
            msg['Subject'] = f"BTC {direction} SIGNAL DETECTED"
            msg['From']    = EMAIL
            msg['To']      = EMAIL
            
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(EMAIL, APP_PASS)
            server.send_message(msg)
            server.quit()
            
            print(f"Alert Sent: {direction} @ ${price:,.2f}")
            last_alert = time.time()

        print(f"\r24/7 Active | BTC: ${price:,.0f} | Delta: {delta:.1f} BTC", end="")
        time.sleep(20)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(30)
