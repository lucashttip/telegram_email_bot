from flask import Flask, request, Response
from telegram import Update
from telegram.ext import Application
import os
import asyncio
from main_bot import application

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

@app.route("/")
def index():
    return "🤖 Bot is alive!"

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    print("Webhook called!")  # Log every call
    try:
        data = request.get_json(force=True)
        print("Received data:", data)
        update = Update.de_json(data, application.bot)
        asyncio.run(application.process_update(update))
    except Exception as e:
        print(f"Error handling webhook update: {e}")
    return Response("OK", status=200)

def setup_webhook():
    url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
    if not WEBHOOK_URL:
        raise RuntimeError("Missing WEBHOOK_URL environment variable.")
    print(f"📡 Setting Telegram webhook to: {f"{WEBHOOK_URL}/webhook/TOKEN"}")
    asyncio.run(application.bot.set_webhook(url=url))

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)