import os
import requests
import anthropic
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

PAIRS = ["XAUUSD", "EURAUD", "USDJPY", "USDCAD", "GBPJPY", "GBPCAD", "GBPAUD"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

async def analyze_pair(pair):
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""You are a professional SMC forex trader. Analyze {pair} right now.
            
Give a SHORT signal in this exact format:
PAIR: {pair}
SIGNAL: BUY or SELL or WAIT
BIAS: (1H trend direction)
ENTRY: (price)
SL: (price)
TP1: (price)
TP2: (price)
REASON: (one line SMC reason - OB, BOS, sweep etc)

Be realistic with current market prices. Only give BUY or SELL if setup is strong."""
        }]
    )
    return message.content[0].text

async def send_signals():
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(
        chat_id=CHAT_ID,
        text="🔍 *Scanning 7 pairs...*",
        parse_mode="Markdown"
    )
    
    for pair in PAIRS:
        try:
            analysis = await analyze_pair(pair)
            signal_line = ""
            if "SIGNAL: BUY" in analysis:
                signal_line = "🟢"
            elif "SIGNAL: SELL" in analysis:
                signal_line = "🔴"
            else:
                signal_line = "⚪"
            
            await bot.send_message(
                chat_id=CHAT_ID,
                text=f"{signal_line}\n```\n{analysis}\n```",
                parse_mode="Markdown"
            )
        except Exception as e:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=f"❌ Error analyzing {pair}: {str(e)}"
            )

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(
        chat_id=CHAT_ID,
        text="✅ *FX Signal Bot is LIVE!*\nI will scan all 7 pairs every 4 hours.\nSending first analysis now...",
        parse_mode="Markdown"
    )
    
    await send_signals()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_signals, 'interval', hours=4)
    scheduler.start()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
