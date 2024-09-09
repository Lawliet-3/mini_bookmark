# Bookmark Manager with Telegram Bot Integration

This project is a Bookmark Manager web application with an integrated Telegram bot interface. It allows users to save, list, and fetch bookmarks through both a web interface and a Telegram bot.

## Features

- Save bookmarks with title and summary
- List saved bookmarks
- Fetch content from URLs
- Telegram bot integration for remote access
- Download fetched content as a text file
- Seamless login between Telegram bot and web interface

## Prerequisites

- Python 3.7+
- MongoDB
- Telegram Bot Token (obtain from BotFather)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/bookmark-manager.git
   cd bookmark-manager
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your configuration:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   WEBSITE_URL=http://your-website-url.com
   MONGO_URI=mongodb://localhost:27017/minibookmark
   SECRET_KEY=your_secret_key_here
   ```

## Usage

### Web Application

1. Start the Flask web server:
   ```
   python app.py
   ```

2. Open a web browser and navigate to `http://localhost:5000`

3. Use the web interface to add, list, and fetch bookmarks

### Telegram Bot

1. Start the Telegram bot:
   ```
   python telegram_bot.py
   ```

2. Open Telegram and search for your bot using the username you set up with BotFather

3. Start a conversation with your bot and use the following commands:
   - `/start`: Get a welcome message
   - `/help`: List available commands
   - `/login`: Log in to your account
   - `/signup`: Create a new account
   - `/logout`: Log out of your account
   - `/add <url>`: Add a new bookmark
   - `/list`: List all saved bookmarks
   - `/fetch <url>`: Fetch content from a URL and offer to download
   - `/website`: Get a link to the web application

## Development

- `app.py`: Contains the Flask web application
- `telegram_bot.py`: Contains the Telegram bot implementation
- `templates/`: Contains HTML templates for the web interface
- `static/`: Contains static files (CSS, JavaScript) for the web interface

## Recent Updates

- Added ability to download fetched content as a text file through Telegram
- Fixed character encoding issues when downloading content
- Improved error handling and user feedback in both web and Telegram interfaces

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.