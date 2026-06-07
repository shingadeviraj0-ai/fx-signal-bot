import os
import requests
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def start_server():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

TELEGRAM_TOKEN = "8857229938:AAF0BCtGKij335kPgGtMWQcBGVbr8Nw9DJI"
CHAT_ID = "5048896288"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWELVE_DATA_KEY = "b77ef725aae044fda092c57dc2cfbcf1"
PAIRS = ["XAU/USD", "EUR/AUD", "USD/JPY", "USD/CAD", "GBP/JPY", "GBP/CAD", "GBP/AUD"]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Telegram error: {e}")

def get_candles(symbol, interval):
    try:
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": 50,
            "apikey": TWELVE_DATA_KEY
        }
        r = requests.get(url, params=params)
        data = r.json()
        if "values" in data:
            return data["values"]
        print(f"No data for {symbol} {interval}: {data}")
        return None
    except Exception as e:
        print(f"Candle error: {e}")
        return None

def calc(candles):
    try:
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        closes = [float(c["close"]) for c in candles]
        opens = [float(c["open"]) for c in candles]

        price = closes[0]
        ema20 = sum(closes[:20]) / 20
        high20 = max(highs[:20])
        low20 = min(lows[:20])

        gains = []
        losses = []
        for i in range(1, 15):
            diff = closes[i-1] - closes[i]
            if diff > 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        ag = sum(gains) / 14 if gains else 0
        al = sum(losses) / 14 if losses else 0.001
        rsi = round(100 - (100 / (1 + ag / al)), 1)

        prev_high = max(highs[5:15])
        prev_low = min(lows[5:15])
        bos_bull = price > prev_high
        bos_bear = price < prev_low

        bull_ob = "None"
        bear_ob = "None"
        for i in range(2, 15):
            if opens[i] > closes[i] and price > opens[i]:
                bull_ob = f"{round(closes[i], 5)}-{round(opens[i], 5)}"
                break
        for i in range(2, 15):
            if opens[i] < closes[i] and price < opens[i]:
                bear_ob = f"{round(opens[i], 5)}-{round(closes[i], 5)}"
                break

        trend = "BULLISH" if price > ema20 else "BEARISH"

        return {
            "price": price,
            "trend": trend,
            "rsi": rsi,
            "high": high20,
            "low": low20,
            "bos_bull": bos_bull,
            "bos_bear": bos_bear,
            "bull_ob": bull_ob,
            "bear_ob": bear_ob
        }
    except Exception as e:
        print(f"Calc error: {e}")
        return None

def ask_gpt(pair, h4, h1, m30, m15):
    try:
        prompt = f"""You are a professional SMC forex trader. Analyze {pair} with this REAL data:

4H: price={h4['price']} trend={h4['trend']} rsi={h4['rsi']} bos_bull={h4['bos_bull']} bos_bear={h4['bos_bear']} bull_ob={h4['bull_ob']} bear_ob={h4['bear_ob']}
1H: price={h1['price']} trend={h1['trend']} rsi={h1['rsi']} bos_bull={h1['bos_bull']} bos_bear={h1['bos_bear']} bull_ob={h1['bull_ob']} bear_ob={h1['bear_ob']}
30M: price={m30['price']} trend={m30['trend']} rsi={m30['rsi']} bos_bull={m30['bos_bull']} bos_bear={m30['bos_bear']}
15M: price={m15['price']} trend={m15['trend']} rsi={m15['rsi']} bull_ob={m15['bull_ob']} bear_ob={m15['bear_ob']}

Only give BUY or SELL if all timeframes align and there is a clear SMC setup.
If no perfect setup reply WAIT.
TP1 = 1:2 RR, TP2 = 1:3 RR

Reply ONLY in this format:
SIGNAL: BUY or SELL or WAIT
ENTRY: price
SL: price
TP1: price
TP2: price
REASON: one line"""

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "gpt-4o-mini",
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}]
        }
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body
        )
        result = r.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        print(f"GPT error: {result}")
        return None
    except Exception as e:
        print(f"GPT error: {e}")
        return None

def check_pair(pair):
    print(f"Checking {pair}...")
    h4 = get_candles(pair, "4h")
    time.sleep(1)
    h1 = get_candles(pair, "1h")
    time.sleep(1)
    m30 = get_candles(pair, "30min")
    time.sleep(1)
    m15 = get_candles(pair, "15min")
    time.sleep(1)

    if not all([h4, h1, m30, m15]):
        print(f"Missing data for {pair}")
        return

    h4d = calc(h4)
    h1d = calc(h1)
    m30d = calc(m30)
    m15d = calc(m15)

    if not all([h4d, h1d, m30d, m15d]):
        print(f"Calc failed for {pair}")
        return

    result = ask_gpt(pair, h4d, h1d, m30d, m15d)

    if result and "WAIT" not in result:
        emoji = "🟢" if "BUY" in result else "🔴"
        send_telegram(f"{emoji} {pair}\n{result}")
        print(f"Signal sent: {pair}")
    else:
        print(f"No setup: {pair}")

def scan():
    print("Scanning all pairs...")
    for pair in PAIRS:
        try:
            check_pair(pair)
            time.sleep(2)
        except Exception as e:
            print(f"Error {pair}: {e}")
    print("Scan done. Next in 5 min.")

send_telegram("FX Signal Bot LIVE! Scanning real market every 5 min...")

while True:
    scan()
    time.sleep(300)
