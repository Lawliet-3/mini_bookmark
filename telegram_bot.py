import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
import requests
import aiofiles
import aiohttp
import uuid
import html
from bs4 import BeautifulSoup

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBSITE_URL = os.getenv("WEBSITE_URL")

# Define states
USERNAME, PASSWORD, SIGNUP_USERNAME, SIGNUP_PASSWORD = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to the Bookmark Manager Bot! Use /help to see a list of available commands and learn how to use the bot.")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please enter your username:")
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text("Please enter your password:")
    return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['username']
    password = update.message.text
    
    response = requests.post(f"{WEBSITE_URL}/login", json={"username": username, "password": password})
    
    if response.status_code == 200:
        context.user_data['logged_in'] = True
        context.user_data['session_id'] = response.cookies.get('session')
        await update.message.reply_text(f"Welcome, {username}! You are now logged in.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Invalid username or password. Please try again.")
        return ConversationHandler.END

async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please enter a username for signup:")
    return SIGNUP_USERNAME

async def get_signup_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['signup_username'] = update.message.text
    await update.message.reply_text("Please enter a password:")
    return SIGNUP_PASSWORD

async def get_signup_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['signup_username']
    password = update.message.text
    
    response = requests.post(f"{WEBSITE_URL}/signup", json={"username": username, "password": password})
    
    if response.status_code == 200:
        context.user_data['logged_in'] = True
        context.user_data['username'] = username
        context.user_data['session_id'] = response.cookies.get('session')
        await update.message.reply_text(f"Welcome, {username}! Your account has been created and you are now logged in.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Signup failed. This username might already exist. Please try again.")
        return ConversationHandler.END

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('logged_in'):
        try:
            response = requests.post(f"{WEBSITE_URL}/logout",
                                     cookies={"session": context.user_data.get('session_id', '')})
            response.raise_for_status()
            context.user_data.clear()
            await update.message.reply_text("You have been logged out.")
        except Exception as e:
            await update.message.reply_text(f"Error logging out: {str(e)}")
    else:
        await update.message.reply_text("You are not logged in.")

async def add_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get('logged_in'):
        await update.message.reply_text("Please login first using /login command.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a URL. Usage: /add <url>")
        return
    url = context.args[0]
    try:
        # First, fetch the content
        fetch_response = requests.post(f"{WEBSITE_URL}/fetch", 
                                       json={"url": url},
                                       cookies={"session": context.user_data.get('session_id', '')})
        fetch_response.raise_for_status()
        content = fetch_response.json()
        
        # Then, save the bookmark
        save_response = requests.post(f"{WEBSITE_URL}/save_bookmark", 
                                      json={"url": url, "title": content['title'], "summary": content['summary']},
                                      cookies={"session": context.user_data.get('session_id', '')})
        save_response.raise_for_status()
        await update.message.reply_text(f"Bookmark added successfully: {content['title']}")
    except Exception as e:
        await update.message.reply_text(f"Error adding bookmark: {str(e)}")

async def list_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get('logged_in'):
        await update.message.reply_text("Please login first using /login command.")
        return
    
    try:
        response = requests.get(f"{WEBSITE_URL}/bookmarks",
                                cookies={"session": context.user_data.get('session_id', '')})
        response.raise_for_status()
        bookmarks = response.json()
        if not bookmarks:
            await update.message.reply_text("You have no saved bookmarks.")
            return
        response_text = "Your bookmarks:\n\n"
        for bookmark in bookmarks:
            response_text += f"• {bookmark['title']}\n{bookmark['url']}\n\n"
        await update.message.reply_text(response_text)
    except Exception as e:
        await update.message.reply_text(f"Error listing bookmarks: {str(e)}")

import html
from bs4 import BeautifulSoup

async def fetch_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get('logged_in'):
        await update.message.reply_text("Please login first using /login command.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a URL. Usage: /fetch <url>")
        return
    url = context.args[0]
    try:
        response = requests.post(f"{WEBSITE_URL}/fetch", 
                                 json={"url": url},
                                 cookies={"session": context.user_data.get('session_id', '')})
        response.raise_for_status()
        content = response.json()
        
        # Clean and format the summary
        soup = BeautifulSoup(content['summary'], 'html.parser')
        clean_summary = soup.get_text()
        formatted_summary = html.escape(clean_summary[:1000]) + "..." if len(clean_summary) > 1000 else html.escape(clean_summary)
        
        message = f"<b>Title:</b> {html.escape(content['title'])}\n\n<b>Summary:</b>\n{formatted_summary}"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
        # Generate a unique ID for this fetch operation
        fetch_id = str(uuid.uuid4())
        context.user_data[f'fetch_{fetch_id}'] = url
        
        # Offer to download the content
        keyboard = [
            [InlineKeyboardButton("Download Content", callback_data=f"download_{fetch_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Would you like to download the full content?", reply_markup=reply_markup)
    except Exception as e:
        await update.message.reply_text(f"Error fetching content: {str(e)}")

async def download_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    fetch_id = query.data.split('_')[1]
    url = context.user_data.get(f'fetch_{fetch_id}')
    
    if not url:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, the download link has expired. Please fetch the URL again.")
        return
    
    try:
        response = requests.post(f"{WEBSITE_URL}/fetch", 
                                 json={"url": url},
                                 cookies={"session": context.user_data.get('session_id', '')})
        response.raise_for_status()
        content = response.json()
        
        # Save content to a file
        filename = f"{content['title'][:50]}.txt"  # Limit filename length
        async with aiofiles.open(filename, mode='w', encoding='utf-8') as file:
            await file.write(f"Title: {content['title']}\n\n")
            await file.write(f"URL: {url}\n\n")
            await file.write(f"Summary: {content['summary']}\n\n")
            await file.write(f"Full Content: {content['full_text']}")
        
        # Send the file to the user
        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(filename, 'rb'))
        
        # Delete the file after sending
        os.remove(filename)
        
        # Clean up the stored URL
        del context.user_data[f'fetch_{fetch_id}']
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error downloading content: {str(e)}")

async def website(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Visit Website", url=WEBSITE_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Click the button below to visit the website:", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
Available commands:

/start - Welcome message and bot introduction
/help - Show this help message
/login - Log in to your account
/signup - Create a new account
/logout - Log out of your account
/add <url> - Add a new bookmark
/list - List all your saved bookmarks
/fetch <url> - Fetch content from a URL and offer to download
/website - Get a link to the web application

How to use:
1. Start by logging in with /login or signing up with /signup
2. Use /add to save new bookmarks
3. Use /list to see all your saved bookmarks
4. Use /fetch to get content from any URL
5. After fetching, you can choose to download the full content
6. Use /logout when you're done

For any issues or questions, please contact the bot administrator.
    """
    await update.message.reply_text(help_text)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    login_handler = ConversationHandler(
        entry_points=[CommandHandler("login", login)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[],
    )

    signup_handler = ConversationHandler(
        entry_points=[CommandHandler("signup", signup)],
        states={
            SIGNUP_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_signup_username)],
            SIGNUP_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_signup_password)],
        },
        fallbacks=[],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))  # Add this line if it's not already there
    application.add_handler(login_handler)
    application.add_handler(signup_handler)
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CommandHandler("add", add_bookmark))
    application.add_handler(CommandHandler("list", list_bookmarks))
    application.add_handler(CommandHandler("fetch", fetch_url))
    application.add_handler(CommandHandler("website", website))
    application.add_handler(CallbackQueryHandler(download_content, pattern="^download_"))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()