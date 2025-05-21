import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackContext,
    CallbackQueryHandler, filters
)
from dotenv import load_dotenv
from datetime import datetime

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
category_selected = False  # New state variable
image_files = []  # List of (filename, bytes) tuples for images

CATEGORY_LIST = ['task', 'idea', 'random', 'important', 'event']

def restricted(func):
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != AUTHORIZED_USER_ID:
            await update.message.reply_text("⛔ Unauthorized.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@restricted
async def show_start_button(update: Update, context: CallbackContext):
    # Show a persistent 'Start Email' button
    keyboard = [["Start Email"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    if update.message:
        await update.message.reply_text("Press the button below to start composing an email.", reply_markup=reply_markup)
    else:
        # If triggered from a callback, send a new message
        await context.bot.send_message(chat_id=update.effective_user.id, text="Press the button below to start composing an email.", reply_markup=reply_markup)

@restricted
async def start_email(update: Update, context: CallbackContext):
    global composing, email_lines, email_category, category_selected
    composing = False
    email_lines = []
    email_category = "uncategorized"
    category_selected = False
    # Remove the custom keyboard
    await update.message.reply_text("Let's start!", reply_markup=ReplyKeyboardRemove())
    # Show category selection buttons
    keyboard = [[InlineKeyboardButton(cat.capitalize(), callback_data=f"select_category_{cat}")] for cat in CATEGORY_LIST]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select a category for your email:", reply_markup=reply_markup
    )

@restricted
async def category_button_handler(update: Update, context: CallbackContext):
    global composing, email_category, category_selected
    query = update.callback_query
    await query.answer()
    if query.data.startswith("select_category_"):
        email_category = query.data.replace("select_category_", "")
        category_selected = True
        composing = True
        await query.edit_message_text(f"Category selected: {email_category.capitalize()}\nYou can now compose your email. Send lines. When done, press the Stop Email button.")

@restricted
async def stop_email(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("✅ Send", callback_data="send_email"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_email")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Support both message and callback_query triggers
    if update.message:
        await update.message.reply_text("Do you want to send this email?", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("Do you want to send this email?", reply_markup=reply_markup)

@restricted
async def handle_message(update: Update, context: CallbackContext):
    global composing, email_lines, email_category, category_selected
    text = update.message.text
    if text == "Start Email":
        await start_email(update, context)
        return
    if not category_selected:
        await update.message.reply_text("⚠️ Please select a category first by pressing Start Email and choosing a category.")
        return
    if composing:
        email_lines.append(text)
        # Show inline Stop Email button after each message
        keyboard = [[InlineKeyboardButton("🛑 Stop Email", callback_data="stop_email")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("➕ Added to email.", reply_markup=reply_markup)
    else:
        await update.message.reply_text("⚠️ Not in compose mode. Press Start Email to begin.")

@restricted
async def stop_email_button_handler(update: Update, context: CallbackContext):
    # Handles the inline Stop Email button
    await stop_email(update, context)

@restricted
async def handle_photo(update: Update, context: CallbackContext):
    global composing, image_files, category_selected
    if not category_selected or not composing:
        await update.message.reply_text("⚠️ Please start and select a category first.")
        return
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    filename = f"image_{photo.file_id}.jpg"
    image_files.append((filename, file_bytes))
    # Show inline Stop Email button after each image
    keyboard = [[InlineKeyboardButton("🛑 Stop Email", callback_data="stop_email")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🖼️ Image added to email.", reply_markup=reply_markup)

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
            await show_start_button(update, context)
        except Exception as e:
            await query.edit_message_text(f"❌ Failed to send email: {e}")
    elif query.data == "cancel_email":
        composing = False
        email_lines = []
        image_files.clear()  # Clear images on cancel
        email_category = "uncategorized"
        await query.edit_message_text("❌ Email canceled.")
        await show_start_button(update, context)

def send_email(body: str, category: str):
    global image_files
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"[{category.upper()}] Telegram {category.capitalize()} Note - {timestamp}"

    msg = MIMEMultipart('related')
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = TO_EMAIL

    # Build HTML body with images embedded
    html_body = f"<p>{body.replace(chr(10), '<br>')}</p>"
    for idx, (filename, _) in enumerate(image_files):
        cid = f"image{idx}"
        html_body += f'<br><img src="cid:{cid}">'

    msg_alt = MIMEMultipart('alternative')
    msg.attach(msg_alt)
    msg_alt.attach(MIMEText(html_body, 'html'))

    # Attach images as inline
    for idx, (filename, file_bytes) in enumerate(image_files):
        img = MIMEImage(file_bytes, name=filename)
        img.add_header('Content-ID', f'<image{idx}>')
        img.add_header('Content-Disposition', 'inline', filename=filename)
        msg.attach(img)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

    image_files.clear()  # Clear after sending

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN or not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("❌ Missing environment variables. Check your .env file.")
        return

    print("🤖 Bot is starting...")
    
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", show_start_button))
    application.add_handler(CommandHandler("startemail", start_email))
    application.add_handler(CommandHandler("stopemail", stop_email))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(category_button_handler, pattern=r"^select_category_"))
    application.add_handler(CallbackQueryHandler(stop_email_button_handler, pattern=r"^stop_email$"))
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
