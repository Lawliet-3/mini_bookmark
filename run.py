import asyncio
from app import app
from telegram_bot import main as run_bot

async def run_flask():
    app.run(debug=True, use_reloader=False)

async def main():
    flask_task = asyncio.create_task(run_flask())
    bot_task = asyncio.create_task(run_bot())
    await asyncio.gather(flask_task, bot_task)

if __name__ == '__main__':
    asyncio.run(main())