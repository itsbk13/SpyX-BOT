import os
import sys
from threading import Thread
import time
import asyncio
from flask import Flask

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from logger import logger
from config import bot

# Simple Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running", 200

@app.route('/healthz')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def test_bot_async():
    """Test if bot works - ASYNC VERSION"""
    try:
        logger.info("=== TESTING BOT TOKEN (ASYNC) ===")
        bot_info = await bot.get_me()  # Now properly awaited
        logger.info(f"Bot token works! @{bot_info.username}")
        return True
        
    except Exception as e:
        logger.error(f"Bot test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def start_bot():
    """Start the bot using Application"""
    try:
        logger.info("=== STARTING BOT APPLICATION ===")
        from telegram.ext import Application, CommandHandler
        from commands import start
        
        # Create application
        application = Application.builder().bot(bot).build()
        application.add_handler(CommandHandler("start", start))
        
        logger.info("Starting polling...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
    except Exception as e:
        logger.error(f"Bot startup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    logger.info("=== FIXED ASYNC BOT TEST ===")
    
    # Start Flask in background
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Give Flask time to start
    time.sleep(2)
    logger.info("Flask started, now testing bot...")
    
    # Test bot token with async
    try:
        bot_works = asyncio.run(test_bot_async())
        if bot_works:
            logger.info("Bot test passed! Starting main bot...")
            start_bot()
        else:
            logger.error("Bot test failed! Check your API_TOKEN")
    except Exception as e:
        logger.error(f"Failed to test bot: {e}")

if __name__ == '__main__':
    main()
