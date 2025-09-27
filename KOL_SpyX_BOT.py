import os
import sys
from threading import Thread
import time
import asyncio
from flask import Flask
import signal

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from logger import logger
from config import bot

# Simple Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "KOL SpyX Bot is running", 200

@app.route('/healthz')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def test_bot_async():
    """Test if bot works - ASYNC VERSION"""
    try:
        logger.info("=== TESTING BOT TOKEN (ASYNC) ===")
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot token works! @{bot_info.username}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Bot test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def start_bot_with_retry():
    """Start the bot with retry logic"""
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"=== STARTING BOT (Attempt {retry_count + 1}/{max_retries}) ===")
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler
            from commands import (start, add, remove, list_tracked, help, 
                                 delete_all_command, button, update_command)
            
            # Create application
            application = Application.builder().bot(bot).build()
            
            # Add all handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("add", add))
            application.add_handler(CommandHandler("remove", remove))
            application.add_handler(CommandHandler("list", list_tracked))
            application.add_handler(CommandHandler("help", help))
            application.add_handler(CommandHandler("delete_all", delete_all_command))
            application.add_handler(CommandHandler("update", update_command))
            application.add_handler(CallbackQueryHandler(button))
            
            logger.info("✅ Command handlers added successfully")
            logger.info("🚀 Starting bot polling...")
            
            # This will block here and keep running
            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
                poll_interval=2.0
            )
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"❌ Bot failed (attempt {retry_count}): {e}")
            if retry_count < max_retries:
                wait_time = min(30 * retry_count, 300)  # Max 5 minutes
                logger.info(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("❌ Max retries reached, giving up on bot")
                break

# Global flag to keep main thread alive
keep_running = True

def signal_handler(signum, frame):
    global keep_running
    logger.info(f"Received signal {signum}, shutting down...")
    keep_running = False
    sys.exit(0)

def main():
    global keep_running
    logger.info("🚀 === STARTING KOL SPYX BOT ===")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize database
        import database
        database.create_tables()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Start Flask in background
    logger.info("🌐 Starting Flask server...")
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Give Flask time to start
    time.sleep(3)
    logger.info("✅ Flask server started")
    
    # Test bot token
    logger.info("🔑 Testing bot token...")
    try:
        bot_works = asyncio.run(test_bot_async())
        if not bot_works:
            logger.error("❌ Bot token test failed! Check your API_TOKEN")
            # Keep Flask alive even if bot fails
            logger.info("🌐 Keeping Flask server alive for debugging...")
            while keep_running:
                time.sleep(10)
            return
    except Exception as e:
        logger.error(f"❌ Failed to test bot: {e}")
        logger.info("🌐 Keeping Flask server alive for debugging...")
        while keep_running:
            time.sleep(10)
        return
    
    # Start bot in a separate thread so main thread stays alive
    logger.info("🤖 Starting bot in background thread...")
    bot_thread = Thread(target=start_bot_with_retry, daemon=False)  # Not daemon!
    bot_thread.start()
    
    # Keep main thread alive
    try:
        while keep_running and bot_thread.is_alive():
            time.sleep(5)
            # Optional: Add periodic health check here
            
        if not bot_thread.is_alive():
            logger.error("❌ Bot thread died, restarting...")
            # Could implement bot restart logic here
            
    except KeyboardInterrupt:
        logger.info("👋 Shutting down gracefully...")
    finally:
        logger.info("🛑 Application shutting down")

if __name__ == '__main__':
    main()
