import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import requests

# Load environment variables
load_dotenv()

# Get environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBSITE_URL = os.getenv("WEBSITE_URL")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to your Bookmark Manager Bot! Use /help to see available commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
    Available commands:
    /add <url> - Add a new bookmark
    /list - List all saved bookmarks
    /fetch <url> - Fetch content from a URL
    /website - Get a link to the website
    """
    await update.message.reply_text(help_text)

async def add_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Please provide a URL. Usage: /add <url>")
        return
    url = context.args[0]
    try:
        response = requests.post(f"{WEBSITE_URL}/save_bookmark", json={"url": url})
        response.raise_for_status()
        data = response.json()
        await update.message.reply_text(f"Bookmark added: {data['title']}")
    except Exception as e:
        await update.message.reply_text(f"Error adding bookmark: {str(e)}")

async def list_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        response = requests.get(f"{WEBSITE_URL}/bookmarks")
        response.raise_for_status()
        bookmarks = response.json()
        if not bookmarks:
            await update.message.reply_text("You have no saved bookmarks.")
            return
        response = "Your bookmarks:\n\n"
        for bookmark in bookmarks:
            response += f"• {bookmark['title']}\n{bookmark['url']}\n\n"
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"Error listing bookmarks: {str(e)}")

async def fetch_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Please provide a URL. Usage: /fetch <url>")
        return
    url = context.args[0]
    try:
        response = requests.post(f"{WEBSITE_URL}/fetch", json={"url": url})
        response.raise_for_status()
        content = response.json()
        await update.message.reply_text(f"Title: {content['title']}\n\nSummary: {content['summary'][:1000]}...")
    except Exception as e:
        await update.message.reply_text(f"Error fetching content: {str(e)}")

async def website(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Visit Website", url=WEBSITE_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Click the button below to visit the website:", reply_markup=reply_markup)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_bookmark))
    application.add_handler(CommandHandler("list", list_bookmarks))
    application.add_handler(CommandHandler("fetch", fetch_url))
    application.add_handler(CommandHandler("website", website))  # Add this line

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()