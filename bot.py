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

def get_candles(symbol, interval, outputsize=50):
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVE_DATA_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "values" not in data:
        print(f"Error fetching {symbol} {interval}: {data}")
        return None
    return data["values"]

def calculate_levels(candles):
    if not candles or len(candles) < 10:
        return None
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    opens = [float(c["open"]) for c in candles]
    current_price = closes[0]
    recent_high = max(highs[:20])
    recent_low = min(lows[:20])
    ema20 = sum(closes[:20]) / 20
    gains, losses = [], []
    for i in range(1, 15):
        diff = closes[i-1] - closes[i]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains) / 14 if gains else 0
    avg_loss = sum(losses) / 14 if losses else 0.001
    rsi = 100 - (100 / (1 + avg_gain/avg_loss))
    prev_high = max(highs[5:15])
    prev_low = min(lows[5:15])
    bos_bullish = current_price > prev_high
    bos_bearish = current_price < prev_low
    bull_ob_high, bull_ob_low = None, None
    bear_ob_high, bear_ob_low = None, None
    for i in range(2, 15):
        if opens[i] > closes[i] and closes[0] > opens[i]:
            bull_ob_high = opens[i]
            bull_ob_low = closes[i]
            break
    for i in range(2, 15):
        if opens[i] < closes[i] and closes[0] < opens[i]:
            bear_ob_high = closes[i]
            bear_ob_low = opens[i]
            break
    return {
        "current_price": current_price,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "ema20": ema20,
        "rsi": round(rsi, 1),
        "bos_bullish": bos_bullish,
        "bos_bearish": bos_bearish,
        "bull_ob": f"{bull_ob_low}-{bull_ob_high}" if bull_ob_high else "None",
        "bear_ob": f"{bear_ob_low}-{bear_ob_high}" if bear_ob_high else "None",
        "trend": "BULLISH" if current_price > ema20 else "BEARISH"
    }

def analyze_with_gpt(pair, h4, h1, m30, m15):
    if not all([h4, h1, m30, m15]):
        return None
    prompt = f"""You are a professional SMC forex trader. Analyze {pair} based on REAL market data:

4H: Price={h4['current_price']} Trend={h4['trend']} RSI={h4['rsi']} BOS_Bull={h4['bos_bullish']} BOS_Bear={h4['bos_bearish']} Bull_OB={h4['bull_ob']} Bear_OB={h4['bear_ob']}
1H: Price={h1['current_price']} Trend={h1['trend']} RSI={h1['rsi']} BOS_Bull={h1['bos_bullish']} BOS_Bear={h1['bos_bearish']} Bull_OB={h1['bull_ob']} Bear_OB={h1['bear_ob']}
30M: Price={m30['current_price']} Trend={m30['trend']} RSI={m30['rsi']} BOS_Bull={m30['bos_bullish']} BOS_Bear={m30['bos_bearish']}
15M: Price={m15['current_price']} Trend={m15['trend']} RSI={m15['rsi']} Bull_OB={m15['bull_ob']} Bear_OB={m15['bear_ob']}

Rules:
- Only BUY or SELL if ALL timeframes align
- Must have OB retest on 15M
- If not perfect setup reply WAIT
- SL below/above OB
- TP1 = 1:2 RR, TP2 = 1:3 RR

Reply ONLY in this format:
SIGNAL: BUY or SELL or WAIT
ENTRY: price
SL: price
TP1: price
TP2: price
REASON: one line SMC reason"""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )
    result = response.json()
    print(f"GPT response: {result}")
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    else:
        print(f"GPT error: {result}")
        return None

def check_pair(pair):
    print(f"Checking {pair}...")
    h4 = get_candles(pair, "4h", 50)
    time.sleep(1)
    h1 = get_candles(pair, "1h", 50)
    time.sleep(1)
    m30 = get_candles(pair, "30min", 50)
    time.sleep(1)
    m15 = get_candles(pair, "15min", 50)
    time.sleep(1)
    if not all([h4, h1, m30, m15]):
        print(f"Could not fetch data for {pair}")
        return
    h4_l = calculate_levels(h4)
    h1_l = calculate_levels(h1)
    m30_l = calculate_levels(m30)
    m15_l = calculate_levels(m15)
    analysis = analyze_with_gpt(pair, h4_l, h1_l, m30_l, m15_l)
    if analysis and "WAIT" not in analysis:
        emoji = "🟢" if "BUY" in analysis else "🔴"
        send_telegram(f"{emoji} {pair}\n{analysis}")
        print(f"Signal sent for {pair}")
    else:
        print(f"No setup for {pair}")

def run_scan():
    print("Scanning market...")
    for pair in PAIRS:
        try:
            check_pair(pair)
            time.sleep(2)
        except Exception as e:
            print(f"Error {pair}: {e}")
    print("Scan done. Next in 5 min.")

send_telegram("✅ FX Signal Bot LIVE! Scanning real market every 5 minutes...")

while True:
    run_scan()
    time.sleep(300)    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVE_DATA_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "values" not in data:
        print(f"Error fetching {symbol} {interval}: {data}")
        return None
    return data["values"]

def calculate_levels(candles):
    if not candles or len(candles) < 10:
        return None
    
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    opens = [float(c["open"]) for c in candles]
    
    # Current price
    current_price = closes[0]
    
    # Swing high and low (last 20 candles)
    recent_high = max(highs[:20])
    recent_low = min(lows[:20])
    
    # EMA 20 simple calculation
    ema20 = sum(closes[:20]) / 20
    
    # RSI calculation
    gains = []
    losses = []
    for i in range(1, 15):
        diff = closes[i-1] - closes[i]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains) / 14 if gains else 0
    avg_loss = sum(losses) / 14 if losses else 0.001
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # BOS detection
    prev_high = max(highs[5:15])
    prev_low = min(lows[5:15])
    bos_bullish = current_price > prev_high
    bos_bearish = current_price < prev_low
    
    # Order block detection
    # Bullish OB = last bearish candle before bullish move
    bull_ob_high = None
    bull_ob_low = None
    bear_ob_high = None
    bear_ob_low = None
    
    for i in range(2, 15):
        if opens[i] > closes[i]:  # bearish candle
            if closes[0] > opens[i]:  # price moved up after
                bull_ob_high = opens[i]
                bull_ob_low = closes[i]
                break
    
    for i in range(2, 15):
        if opens[i] < closes[i]:  # bullish candle
            if closes[0] < opens[i]:  # price moved down after
                bear_ob_high = closes[i]
                bear_ob_low = opens[i]
                break
    
    return {
        "current_price": current_price,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "ema20": ema20,
        "rsi": round(rsi, 1),
        "bos_bullish": bos_bullish,
        "bos_bearish": bos_bearish,
        "bull_ob": f"{bull_ob_low}-{bull_ob_high}" if bull_ob_high else "None",
        "bear_ob": f"{bear_ob_low}-{bear_ob_high}" if bear_ob_high else "None",
        "trend": "BULLISH" if current_price > ema20 else "BEARISH"
    }

def analyze_with_claude(pair, h4, h1, m30, m15):
    if not all([h4, h1, m30, m15]):
        return None
    
    prompt = f"""You are a professional SMC forex trader. Analyze {pair} based on this REAL market data:

4H ANALYSIS:
Price: {h4['current_price']} | Trend: {h4['trend']} | RSI: {h4['rsi']}
BOS Bullish: {h4['bos_bullish']} | BOS Bearish: {h4['bos_bearish']}
Bullish OB: {h4['bull_ob']} | Bearish OB: {h4['bear_ob']}
Range: {h4['recent_low']} - {h4['recent_high']}

1H ANALYSIS:
Price: {h1['current_price']} | Trend: {h1['trend']} | RSI: {h1['rsi']}
BOS Bullish: {h1['bos_bullish']} | BOS Bearish: {h1['bos_bearish']}
Bullish OB: {h1['bull_ob']} | Bearish OB: {h1['bear_ob']}

30M ANALYSIS:
Price: {m30['current_price']} | Trend: {m30['trend']} | RSI: {m30['rsi']}
BOS Bullish: {m30['bos_bullish']} | BOS Bearish: {m30['bos_bearish']}

15M ANALYSIS:
Price: {m15['current_price']} | Trend: {m15['trend']} | RSI: {m15['rsi']}
Bullish OB: {m15['bull_ob']} | Bearish OB: {m15['bear_ob']}

Rules:
- Only give BUY or SELL if ALL timeframes align
- Must have liquidity sweep + OB retest on 15M
- If setup not perfect reply with WAIT
- Entry must be at OB level
- SL below/above OB
- TP1 = 1:2 RR, TP2 = 1:3 RR

Reply ONLY in this format:
SIGNAL: BUY or SELL or WAIT
ENTRY: price
SL: price  
TP1: price
TP2: price
REASON: one line"""

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=data
    )
    result = response.json()
    
    if "content" in result:
        return result["content"][0]["text"]
    else:
        print(f"Claude error: {result}")
        return None

def check_pair(pair):
    print(f"Checking {pair}...")
    
    h4 = get_candles(pair, "4h", 50)
    time.sleep(1)
    h1 = get_candles(pair, "1h", 50)
    time.sleep(1)
    m30 = get_candles(pair, "30min", 50)
    time.sleep(1)
    m15 = get_candles(pair, "15min", 50)
    time.sleep(1)
    
    if not all([h4, h1, m30, m15]):
        print(f"Could not fetch data for {pair}")
        return
    
    h4_levels = calculate_levels(h4)
    h1_levels = calculate_levels(h1)
    m30_levels = calculate_levels(m30)
    m15_levels = calculate_levels(m15)
    
    analysis = analyze_with_claude(pair, h4_levels, h1_levels, m30_levels, m15_levels)
    
    if analysis and "WAIT" not in analysis:
        emoji = "🟢" if "BUY" in analysis else "🔴"
        message = f"{emoji} {pair}\n{analysis}"
        send_telegram(message)
        print(f"Signal sent for {pair}: {analysis}")
    else:
        print(f"No setup for {pair} - waiting")

def run_scan():
    print("Starting market scan...")
    for pair in PAIRS:
        try:
            check_pair(pair)
            time.sleep(2)
        except Exception as e:
            print(f"Error checking {pair}: {e}")
    print("Scan complete. Next scan in 5 minutes.")

while True:
    run_scan()
    time.sleep(300)
