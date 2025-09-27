import os
import sys
from threading import Thread
import time
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

def test_bot():
    """Test if bot works"""
    try:
        logger.info("=== TESTING BOT TOKEN ===")
        bot_info = bot.get_me()
        logger.info(f"Bot token works! @{bot_info.username}")
        
        logger.info("=== STARTING SIMPLE POLLING ===")
        from telegram.ext import Application, CommandHandler
        from commands import start
        
        app = Application.builder().bot(bot).build()
        app.add_handler(CommandHandler("start", start))
        
        logger.info("Starting polling...")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Bot test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    logger.info("=== MINIMAL BOT TEST ===")
    
    # Start Flask in background
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Give Flask time to start
    time.sleep(2)
    logger.info("Flask started, now testing bot...")
    
    # Test bot
    test_bot()

if __name__ == '__main__':
    main()
