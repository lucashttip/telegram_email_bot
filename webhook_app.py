from flask import Flask, request, Response
from telegram import Update
from telegram.ext import Application
import os
import asyncio
import threading
from main_bot import application

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
initialized = False
init_lock = threading.Lock()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@app.route("/")
def index():
    return "🤖 Bot is alive!"

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    global initialized
    print("Webhook called!", flush=True)  # Log every call
    try:
        with init_lock:
            if not initialized:
                loop.run_until_complete(application.initialize())
                initialized = True
                print("Application initialized.", flush=True)
        data = request.get_json(force=True)
        print("Received data:", data, flush=True)
        update = Update.de_json(data, application.bot)
        loop.run_until_complete(application.process_update(update))
    except Exception as e:
        print(f"Error handling webhook update: {e}", flush=True)
    return Response("OK", status=200)

def setup_webhook():
    url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
    if not WEBHOOK_URL:
        raise RuntimeError("Missing WEBHOOK_URL environment variable.")
    print(f"📡 Setting Telegram webhook to: {f'{WEBHOOK_URL}/webhook/TOKEN'}")
    loop.run_until_complete(application.bot.set_webhook(url=url))

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)