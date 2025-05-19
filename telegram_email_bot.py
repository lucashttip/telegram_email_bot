import os
import smtplib
from email.mime.text import MIMEText
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackContext,
    CallbackQueryHandler, filters
)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Email configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID"))
TO_EMAIL = os.getenv("TO_EMAIL", EMAIL_ADDRESS)
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))

# State variables
composing = False
email_lines = []
email_category = "uncategorized"

def restricted(func):
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != AUTHORIZED_USER_ID:
            await update.message.reply_text("⛔ Unauthorized.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@restricted
async def start_email(update: Update, context: CallbackContext):
    global composing, email_lines, email_category
    composing = True
    email_lines = []
    email_category = "uncategorized"
    await update.message.reply_text("✍️ Started composing email. Send lines. If you wish to add a category, choose one from: #task, #idea, #random, #important, #event. Send /stopemail to finish.")

@restricted
async def stop_email(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("✅ Send", callback_data="send_email"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_email")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Do you want to send this email?", reply_markup=reply_markup)

def parse_category(line):
    global email_category
    categories = ['task', 'idea', 'random', 'important', 'event']
    changedCat = False
    for cat in categories:
        if f"#{cat}" in line.lower():
            if email_category != cat:
                email_category = cat
                changedCat = True
    return email_category, changedCat

@restricted
async def handle_message(update: Update, context: CallbackContext):
    global composing, email_lines, email_category
    text = update.message.text
    if composing:
        cat, changedCat = parse_category(text)
        if changedCat:
            email_category = cat
        else:
            email_lines.append(text)
        await update.message.reply_text("➕ Added to email. If you want to stop composing, send /stopemail.")
    else:
        await update.message.reply_text("⚠️ Not in compose mode. Send /startemail to begin.")

@restricted
async def button_handler(update: Update, context: CallbackContext):
    global composing, email_lines, email_category
    query = update.callback_query
    await query.answer()

    if query.data == "send_email":
        body = "\n".join(email_lines)
        try:
            send_email(body, email_category)
            composing = False
            email_lines = []
            email_category = "uncategorized"
            await query.edit_message_text("📤 Email sent!")
        except Exception as e:
            await query.edit_message_text(f"❌ Failed to send email: {e}")
    elif query.data == "cancel_email":
        composing = False
        email_lines = []
        email_category = "uncategorized"
        await query.edit_message_text("❌ Email canceled.")

def send_email(body: str, category: str):
    subject = f"[{category.upper()}] Telegram {category.capitalize()} Note"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = TO_EMAIL

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN or not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("❌ Missing environment variables. Check your .env file.")
        return

    print("🤖 Bot is starting...")
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("startemail", start_email))
    application.add_handler(CommandHandler("stopemail", stop_email))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Run the bot
    print("🤖 Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    import platform

    # Special handling for Windows
    if platform.system() == 'Windows':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Run the main function
    main()
