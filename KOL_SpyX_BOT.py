import os
import requests
from requests.exceptions import RequestException
from config import USER_DATA_FOLDER, bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram.error import NetworkError, TimedOut
from commands import start, delete_all_command, button, add, remove, list_tracked, help, update_command
import database  
import time
import httpx
import logging
from logger import logger
import random
from flask import Flask, request
from threading import Thread
import signal
import sys

# Use the logger from logger.py
logger = logging.getLogger('KOL_SpyX_Bot')

# Initialize Flask app for dummy endpoint
app = Flask(__name__)

@app.route('/')
def dummy_endpoint():
    return "Bot is running"


@app.route('/healthz')
def health_check():
    return "OK", 200
    
def retry_request(func, retries=3, initial_delay=5, backoff_factor=2, max_delay=60):
    """Retries a function with exponential backoff in case of NetworkError or TimedOut."""
    attempt = 0
    delay = initial_delay
    while attempt < retries:
        try:
            return func()  # Execute the passed function
        except (NetworkError, TimedOut) as e:
            attempt += 1
            jitter = random.uniform(0, 1)  # Add some randomness to prevent synchronized retries
            delay = min(delay * backoff_factor + jitter, max_delay)  # Ensure delay doesn't exceed max_delay
            logger.error(f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Non-recoverable error occurred: {e}")
            raise  # Re-raise the exception if it's not retryable
    logger.error(f"Failed after {retries} attempts.")
    return None

# Ensure the user data folder exists
if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)

# Ensure the common data folder exists within USER_DATA_FOLDER
common_data_folder = os.path.join(USER_DATA_FOLDER, "common_data")
if not os.path.exists(common_data_folder):
    os.makedirs(common_data_folder)

# Log some startup info
logger.info("Starting KOL_SpyX_BOT...")

def check_internet():
    """Check internet connectivity by attempting to reach Google and Twitter."""
    try:
        for url in ['https://www.icanhazip.com']:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
    except requests.RequestException as e:
        logger.error(f"Internet connection issue: {e}")
    return False

def stop_flask_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def signal_handler(signum, frame):
    logger.info("Received interrupt signal. Shutting down gracefully.")
    if 'flask_thread' in globals() and flask_thread.is_alive():
        stop_flask_server()
    sys.exit(0)

def main():
    try:
        # Ensure tables are created
        database.create_tables()
        logger.info("Database tables created or already exist.")
    except Exception as e:
        logger.error(f"Error during table creation: {e}")

    while True:  # Keep the bot running indefinitely
        try:
            application = Application.builder().bot(bot).build() 
            logger.info("Telegram bot application initialized successfully.")

            # Add handlers for commands
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("add", add))
            application.add_handler(CommandHandler("remove", remove))
            application.add_handler(CommandHandler("list", list_tracked))
            application.add_handler(CommandHandler("delete_all", delete_all_command))
            application.add_handler(CallbackQueryHandler(button))
            application.add_handler(CommandHandler("help", help))
            application.add_handler(CommandHandler("update", update_command))

            logger.info("Command handlers added successfully.")

            # Check internet connection and start the bot, retry if no internet
            if not retry_request(check_internet):
                logger.error("Failed to connect to internet after multiple attempts. Restarting in 10 seconds...")
                time.sleep(10)
                continue  # Restart the loop to check internet again

            # Run both Flask server and Telegram bot in separate threads
            def run_flask():
                port = int(os.environ.get('PORT', 5000))
                app.run(host='0.0.0.0', port=port)

            global flask_thread
            flask_thread = Thread(target=run_flask)
            flask_thread.start()

            # Run the bot with retry logic for network issues
            logger.info("Bot started running")
            retry_request(lambda: application.run_polling(), retries=5, initial_delay=10, backoff_factor=2, max_delay=60)
            # If we've made it here, we'll sleep for a bit before the next check to prevent tight loops
            time.sleep(60)  # Sleep for a minute before next cycle

        except NetworkError as ne:
            logger.error(f"NetworkError occurred: {ne}")
        except httpx.RequestError as e:
            logger.error(f"HTTP request failed: {e}")
        except TimedOut as te:
            logger.error(f"TimedOut error occurred: {te}")
        except RequestException as re:
            logger.error(f"RequestException occurred: {re}")
        except Exception as e:
            logger.error(f"Unexpected error during bot execution: {e}")
            logger.error("Bot stopped unexpectedly. Restarting in 60 seconds...")
            time.sleep(60)  # Wait before retrying
        except KeyboardInterrupt:
            logger.info("Bot execution interrupted by user. Exiting gracefully.")
            break  # Exit the while loop

    # Add any cleanup code here if needed

if __name__ == '__main__':
    # Register the signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
