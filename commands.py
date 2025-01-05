from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import re
import os
import subprocess
import database
import asyncio
import shutil
import sqlite3
from config import bot, USER_DATA_FOLDER
import logging
from logger import logger

# Use the logger from logger.py
logger = logging.getLogger('KOL_SpyX_Bot')

# Utility functions
def get_user_folder(chat_id):
    return os.path.join(USER_DATA_FOLDER, str(chat_id))

def get_common_follower_db(tracked_account):
    return os.path.join(USER_DATA_FOLDER, "common_data", f"{tracked_account}.db")

def get_user_follower_db(chat_id, tracked_account):
    user_db_dir = get_user_folder(chat_id)
    if not os.path.exists(user_db_dir):
        os.makedirs(user_db_dir)
    return os.path.join(user_db_dir, f"{tracked_account}.db")

def create_db_and_table(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            name TEXT,
            username TEXT,
            bio TEXT,
            profile_url TEXT,
            followers_count INTEGER,
            created_at TEXT,
            blue_verified BOOLEAN,
            location TEXT
        );
        ''')
        conn.commit()

def sync_db_from_common_to_user(common_db_path, user_db_path):
    with sqlite3.connect(common_db_path) as common_conn, sqlite3.connect(user_db_path) as user_conn:
        common_cursor = common_conn.cursor()
        user_cursor = user_conn.cursor()

    common_cursor.execute("SELECT * FROM followers")
    for row in common_cursor.fetchall():
        user_cursor.execute('''
        INSERT OR REPLACE INTO followers 
        (id, user_id, name, username, bio, profile_url, followers_count, created_at, blue_verified, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', row)
    user_conn.commit()

# Delete user's folder and database entries
async def delete_all_data(chat_id: int):
    user_folder = get_user_folder(chat_id)
    
    try:
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
        database.delete_user_data(chat_id)
        logger.info(f"All data for user {chat_id} deleted.")
    except Exception as e:
        logger.error(f"Error deleting user data for {chat_id}: {e}")

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    user_folder = get_user_folder(chat_id)

    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    welcome_message = """
    Welcome to SpyX Bot 🔍

What can this bot do?

Track Your Favorite KOLs:
Stay ahead by tracking key opinion leaders (KOLs) or any Twitter account. Receive instant notifications when they follow a new user or project.

    EXAMPLE FOLLOWING ALERT 👇

    <a href="https://twitter.com/dogecoin">@dogecoin</a> ← is followed by <a href="https://twitter.com/elonmusk">@elonmusk</a>

    Details of Dogecoin:

    •🗒 Bio: "Dogecoin is an open source peer-to-peer cryptocurrency, favored by shibas worldwide. Elon Musk thinks we're pretty cool. [RTs are not endorsements]"

    •📍 Location: the moon

    •👥 Followers: 4,200,000

    •📅 Account created: 01-12-2013 (4000 days ago)

    •✅ Verified: Yes
    """
    await update.message.reply_text(welcome_message, parse_mode='HTML')

# Delete command with confirmation
async def delete_all_command(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data='delete_yes'),
         InlineKeyboardButton("No", callback_data='delete_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Are you sure you want to delete all your stored data? Please choose below:', reply_markup=reply_markup)

# Callback function to handle button responses
async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id

    if query.data == 'delete_yes':
        await delete_all_data(chat_id)
        await query.edit_message_text(text="Your data has been deleted successfully. All tracked accounts have been removed.")
    elif query.data == 'delete_no':
        await query.edit_message_text(text="Data deletion canceled.")

# Add command
async def add(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    user_folder = get_user_folder(chat_id)

    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    if len(context.args) != 1:
        await update.message.reply_text("❗Please provide a valid username to track. Usage: /add @username")
        return

    username = context.args[0].lstrip('@')
    if len(username) < 3 or not re.match(r'^[A-Za-z0-9_]+$', username):
        await update.message.reply_text(f"🚫 Invalid account: @{username}. Usernames should be at least 3 characters long and contain only letters, numbers, or underscores.")
        return

    if database.is_account_tracked_by_user(username, chat_id):
        await update.message.reply_text(f"⚠️ You are already tracking: <a href='https://twitter.com/{username}'>@{username}</a>", parse_mode='HTML')
        return

    database.add_account(username, chat_id)
    common_db = get_common_follower_db(username)
    user_db = get_user_follower_db(chat_id, username)

    if not os.path.exists(user_db):
        create_db_and_table(user_db)
        if os.path.exists(common_db):
            sync_db_from_common_to_user(common_db, user_db)

    await update.message.reply_text(f"✅ Now tracking: <a href='https://twitter.com/{username}'>@{username}</a>", parse_mode='HTML')

# Remove command
async def remove(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if len(context.args) != 1:
        await update.message.reply_text("❗Please provide a valid username to remove. Usage: /remove @username")
        return

    username = context.args[0].lstrip('@')
    if len(username) < 3 or not re.match(r'^[A-Za-z0-9_]+$', username):
        await update.message.reply_text(f"🚫 Invalid account: @{username}. Usernames should be at least 3 characters long and contain only letters, numbers, or underscores.")
        return

    if not database.is_account_tracked_by_user(username, chat_id):
        await update.message.reply_text(f"⚠️ You are not tracking: <a href='https://twitter.com/{username}'>@{username}</a>", parse_mode='HTML')
        return

    database.remove_account(username, chat_id)
    tracked_account_db = get_user_follower_db(chat_id, username)
    try:
        if os.path.exists(tracked_account_db):
            os.remove(tracked_account_db)
        await update.message.reply_text(f"❌ Stopped tracking: <a href='https://twitter.com/{username}'>@{username}</a>", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error removing account {username} for user {chat_id}: {e}")
        await update.message.reply_text(f"❌ Error occurred while stopping tracking for @{username}.", parse_mode='HTML')

# List command
async def list_tracked(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    tracked_accounts = database.get_tracked_accounts(chat_id)
    
    if tracked_accounts:
        tracked_message = "📝 Currently tracking:\n" + "\n".join(f"<a href='https://twitter.com/{a}'>@{a}</a>" for a in tracked_accounts)
        await update.message.reply_text(tracked_message, parse_mode='HTML')
    else:
        await update.message.reply_text("🛑 You are not tracking any accounts yet.")

# Help command
async def help(update: Update, context: CallbackContext) -> None:
    help_message = """
📜 Here are the commands you can use:
/start - Get a welcome message and bot description.
/add <username> - Start tracking a Twitter account.
/remove <username> - Stop tracking a Twitter account.
/list - Show the list of tracked accounts.
/update - Update the following list for tracked Twitter accounts (manually).
/delete - Delete all stored user data (requires confirmation).
/help - Get a list of all available commands.
"""
    await update.message.reply_text(help_message)

def run_update_followers():
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "update_script.py")
    subprocess.run(['python', script_path])

async def update_command(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    initial_message = await update.message.reply_text("🔄 Updating followers in the background. This might take a while...")

    try:
        await asyncio.to_thread(run_update_followers)
        await bot.delete_message(chat_id=chat_id, message_id=initial_message.message_id)
        await bot.send_message(chat_id=chat_id, text="Followers list is now up-to-date👍.")
    except Exception as e:
        logger.error(f"Error in update followers process: {e}")
        await bot.delete_message(chat_id=chat_id, message_id=initial_message.message_id)
        await bot.send_message(chat_id=chat_id, text="⚠️ An error occurred while updating followers.")