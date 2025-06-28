from flask import Flask, request, Response
from telegram import Update
from telegram.ext import Application
import os
import asyncio

from main_bot import application  # Assuming your main bot logic is moved to `main_bot.py`

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

@app.route("/")
def index():
    return "🤖 Bot is alive!"

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
    except Exception as e:
        print(f"Error handling webhook update: {e}")
    return Response("OK", status=200)

# One-time webhook setup
def setup_webhook():
    url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
    if not WEBHOOK_URL:
        raise RuntimeError("Missing WEBHOOK_URL environment variable.")
    print(f"📡 Setting Telegram webhook to: {f"{WEBHOOK_URL}/webhook/TOKEN"}")
    asyncio.run(application.bot.set_webhook(url=url))

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 5000))  # Render provides the PORT env var
    app.run(host="0.0.0.0", port=port)