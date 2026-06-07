import os
import requests
import anthropic
import time

TELEGRAM_TOKEN = "8857229938:AAF0BCtGKij335kPgGtMWQcBGVbr8Nw9DJI"
CHAT_ID = "5048896288"
ANTHROPIC_API_KEY = os.environ.get("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")

PAIRS = ["XAUUSD", "EURAUD", "USDJPY", "USDCAD", "GBPJPY", "GBPCAD", "GBPAUD"]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    response = requests.post(url, data=data)
    print(response.json())
    return response

def analyze_pair(pair):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""Analyze {pair} for day trading right now. Give signal in this format:
PAIR: {pair}
SIGNAL: BUY or SELL or WAIT
ENTRY: price
SL: price
TP1: price
TP2: price
REASON: one line SMC reason"""
        }]
    )
    return message.content[0].text

def run():
    send_telegram("✅ FX Signal Bot is LIVE! Analyzing 7 pairs now...")
    
    for pair in PAIRS:
        try:
            print(f"Analyzing {pair}...")
            analysis = analyze_pair(pair)
            if "BUY" in analysis:
                emoji = "🟢"
            elif "SELL" in analysis:
                emoji = "🔴"
            else:
                emoji = "⚪"
            send_telegram(f"{emoji} {analysis}")
            time.sleep(2)
        except Exception as e:
            print(f"Error {pair}: {e}")
            send_telegram(f"❌ Error on {pair}: {str(e)}")
    
    send_telegram("✅ Analysis complete! Next update in 4 hours.")

while True:
    run()
    time.sleep(14400)
