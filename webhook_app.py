from flask import Flask, request, Response
from telegram import Update
from telegram.ext import Application
import os
import asyncio

from main_bot import application  # Assuming your main bot logic is moved to `main_bot.py`

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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

@app.before_first_request
def set_webhook():
    url = os.getenv("WEBHOOK_URL")
    if url:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(application.bot.set_webhook(url=url))
