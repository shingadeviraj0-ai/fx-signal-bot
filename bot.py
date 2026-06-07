import os
import requests
import anthropic
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
ANTHROPIC_API_KEY = "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"

PAIRS = ["XAUUSD", "EURAUD", "USDJPY", "USDCAD", "GBPJPY", "GBPCAD", "GBPAUD"]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=data)
        print(response.json())
    except Exception as e:
        print(f"Telegram error: {e}")

def analyze_pair(pair):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"Analyze {pair} for day trading. Reply in this exact format:\nPAIR: {pair}\nSIGNAL: BUY or SELL or WAIT\nENTRY: price\nSL: price\nTP1: price\nTP2: price\nREASON: one line"
        }]
    )
    return message.content[0].text

def run():
    send_telegram("FX Signal Bot scanning 7 pairs...")
    for pair in PAIRS:
        try:
            print(f"Analyzing {pair}...")
            analysis = analyze_pair(pair)
            emoji = "🟢" if "BUY" in analysis else "🔴" if "SELL" in analysis else "⚪"
            send_telegram(f"{emoji}\n{analysis}")
            time.sleep(3)
        except Exception as e:
            print(f"Error {pair}: {e}")
            send_telegram(f"Error on {pair}: {str(e)}")
    send_telegram("Done! Next update in 4 hours.")

while True:
    run()
    time.sleep(14400)
