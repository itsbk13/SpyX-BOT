import os
import time
import random
import signal
import sys
import requests
import httpx
import logging
from threading import Thread
from flask import Flask, request
from requests.exceptions import RequestException
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram.error import NetworkError, TimedOut

from config import USER_DATA_FOLDER, API_TOKEN
from commands import start, delete_all_command, button, add, remove, list_tracked, help, update_command
import database
from logger import logger

# Flask app for health checks
app = Flask(__name__)

@app.route("/")
def dummy_endpoint():
    return "Bot is running"

@app.route("/healthz")
def health_check():
    return "OK", 200


# Retry helper
def retry_request(func, retries=3, initial_delay=5, backoff_factor=2, max_delay=60):
    attempt = 0
    delay = initial_delay
    while attempt < retries:
        try:
            return func()
        except (NetworkError, TimedOut) as e:
            attempt += 1
            jitter = random.uniform(0, 1)
            delay = min(delay * backoff_factor + jitter, max_delay)
            logger.error(f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Non-recoverable error: {e}")
            raise
    logger.error(f"Failed after {retries} attempts.")
    return None


# Ensure folders exist
if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)

common_data_folder = os.path.join(USER_DATA_FOLDER, "common_data")
if not os.path.exists(common_data_folder):
    os.makedirs(common_data_folder)

logger.info("Starting KOL_SpyX_BOT...")


def check_internet():
    try:
        response = requests.get("https://www.icanhazip.com", timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"Internet connection issue: {e}")
    return False


def stop_flask_server():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()


def signal_handler(signum, frame):
    logger.info("Received interrupt signal. Shutting down gracefully.")
    if "flask_thread" in globals() and flask_thread.is_alive():
        stop_flask_server()
    sys.exit(0)


def main():
    try:
        database.create_tables()
        logger.info("Database tables created or already exist.")
    except Exception as e:
        logger.error(f"Error during table creation: {e}")

    while True:
        try:
            # Telegram bot setup
            application = Application.builder().token(API_TOKEN).build()

            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("add", add))
            application.add_handler(CommandHandler("remove", remove))
            application.add_handler(CommandHandler("list", list_tracked))
            application.add_handler(CommandHandler("delete_all", delete_all_command))
            application.add_handler(CallbackQueryHandler(button))
            application.add_handler(CommandHandler("help", help))
            application.add_handler(CommandHandler("update", update_command))

            logger.info("Command handlers added successfully.")

            # Check internet before starting
            if not retry_request(check_internet):
                logger.error("No internet after retries. Restarting in 10s...")
                time.sleep(10)
                continue

            # Run Flask in a separate thread (Render requires dynamic port)
            def run_flask():
                port = int(os.environ.get("PORT", 5000))
                app.run(host="0.0.0.0", port=port)

            global flask_thread
            flask_thread = Thread(target=run_flask)
            flask_thread.start()

            logger.info("Bot started running")

            # Run bot (blocking call, restarts if it crashes)
            retry_request(lambda: application.run_polling(), retries=5, initial_delay=10, backoff_factor=2, max_delay=60)

            time.sleep(60)  # Safety sleep

        except (NetworkError, TimedOut, httpx.RequestError, RequestException) as e:
            logger.error(f"Network-related error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error("Bot stopped unexpectedly. Restarting in 60s...")
            time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Bot interrupted by user. Exiting...")
            break


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
