import sys
import os
import pandas as pd
import re
import asyncio
from datetime import datetime
import sqlite3
import telegram 
from telegram import Bot
import logging
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_tracked_accounts
from logger import logger

# Use the logger from logger.py
logger = logging.getLogger('KOL_SpyX_Bot')

# Get API Token from environment variables (Render)
API_TOKEN = os.environ.get('API_TOKEN')
if not API_TOKEN:
    logger.error("API_TOKEN not set in environment. Exiting.")
    sys.exit(1)

bot = Bot(token=API_TOKEN)
USER_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "userdata")

# Ensure the common data directory exists
common_data_dir = os.path.join(USER_DATA_FOLDER, "common_data")
if not os.path.exists(common_data_dir):
    os.makedirs(common_data_dir)

# The required columns for the CSV files
required_columns = {
    "User ID": "user_id",
    "Name": "name",
    "Username": "username",
    "Bio": "bio",
    "Profile URL": "profile_url",
    "Follower Count": "followers_count",
    "Created At": "created_at",
    "Blue Verified": "blue_verified",
    "Location": "location"
}

# Utility function to get common data database path
def get_common_follower_db(tracked_account):
    return os.path.join(common_data_dir, f"{tracked_account}.db")

# Utility function to get user-specific database path
def get_user_follower_db(chat_id, tracked_account):
    user_db_dir = os.path.join(USER_DATA_FOLDER, str(chat_id))
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

def check_table_exists(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='followers';")
        return cursor.fetchone() is not None

def fetch_new_followers(tracked_account):
    """
    Fetch new followers from the uploaded CSV file and ensure it matches the required columns.
    """
    csv_path = os.path.join(common_data_dir, f"{tracked_account}.csv")
    if os.path.exists(csv_path):
        try:
            followers_df = pd.read_csv(csv_path)
            normalized_data = {sql_col: followers_df[csv_col] if csv_col in followers_df.columns else 
                               (0 if sql_col in ["blue_verified", "followers_count"] else 
                                (datetime.now().strftime('%Y-%m-%d %H:%M:%S') if sql_col == "created_at" else None))
                               for csv_col, sql_col in required_columns.items()}
            normalized_df = pd.DataFrame(normalized_data)
            os.remove(csv_path)
            logger.info(f"CSV for {tracked_account} processed and deleted.")
            return normalized_df
        except Exception as e:
            logger.error(f"Error processing CSV for {tracked_account}: {e}")
    else:
        logger.warning(f"No CSV found for {tracked_account}.")
    return pd.DataFrame(columns=required_columns.values())

def insert_followers_to_db(db_path: str, followers: pd.DataFrame) -> None:
    try:
        if not followers.empty:
            followers = followers[list(required_columns.values())]
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                for _, follower in followers.iterrows():
                    # Check for duplicates in common DB
                    cursor.execute("SELECT 1 FROM followers WHERE username = ?", (follower['username'],))
                    if not cursor.fetchone():  # If no match, follower does not exist
                        cursor.execute('''INSERT INTO followers 
                                          (user_id, name, username, bio, profile_url, 
                                           followers_count, created_at, blue_verified, location)
                                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                          tuple(follower))
                        logger.info(f"Inserted new follower {follower['username']} into {db_path}")
                    else:
                        logger.info(f"Skipped duplicate follower {follower['username']} in {db_path}")
                conn.commit()
            logger.info(f"{len(followers)} followers processed for {db_path}")
        else:
            logger.info(f"No followers to insert into {db_path}")
    except sqlite3.Error as e:
        logger.error(f"Error inserting followers into {db_path}: {e}")

async def send_follower_notification(chat_id, follower_details):
    created_at_date = datetime.strptime(follower_details['created_at'], "%a %b %d %H:%M:%S %z %Y")
    days_ago = (datetime.now(created_at_date.tzinfo) - created_at_date).days

    location = follower_details['location'] if pd.notna(follower_details['location']) else " - "
    bio = follower_details.get('bio', " - ")
    if pd.notna(bio):
        bio = re.sub(r'(?<![\w@])@(\w+)(?![\w.])', r'<a href="https://twitter.com/\1">@\1</a>', bio)
        for url in re.findall(r'(https?://(?:t\.co|t\.me)/[^\s]+)', bio):
            bio = bio.replace(url, f'<a href="{url}">🔗Links</a>')

    message = (
        f"🚨 NEW FOLLOWING ALERT : \n\n"
        f"<a href='{follower_details['profile_url']}'>@{follower_details['username']}</a> "
        f"← is followed by "
        f"<a href='https://twitter.com/{follower_details['tracked_account']}'>@{follower_details['tracked_account']}</a>\n\n"
        f"Details of {follower_details['name']}:\n\n"
        f"•🗒 Bio: \"{bio}\"\n\n"
        f"•📍 Location: {location}\n\n"
        f"•👥 Followers: {follower_details['followers_count']}\n\n"
        f"•📅 Account created: {created_at_date.strftime('%d-%m-%Y')} ({days_ago} days ago)\n\n"
        f"•✅ Verified: {follower_details['blue_verified']}"
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            break
        except telegram.error.TimedOut:
            await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
            if attempt == max_retries - 1:
                logger.error(f"Failed to send notification to chat {chat_id} after {max_retries} attempts")
        except Exception as e:
            logger.error(f"An error occurred while sending notification to chat {chat_id}: {e}")
            break

async def update_followers(chat_id, tracked_account):
    common_db = get_common_follower_db(tracked_account)
    user_db = get_user_follower_db(chat_id, tracked_account)

    if not check_table_exists(common_db):
        logger.info(f"Creating table in {common_db}...")
        create_db_and_table(common_db)

    if not check_table_exists(user_db):
        logger.info(f"Creating table in {user_db}...")
        create_db_and_table(user_db)

    try:
        new_data = fetch_new_followers(tracked_account)
        if not new_data.empty:
            insert_followers_to_db(common_db, new_data)

        with sqlite3.connect(common_db) as common_conn, sqlite3.connect(user_db) as user_conn:
            common_cursor = common_conn.cursor()
            user_cursor = user_conn.cursor()

            common_cursor.execute("SELECT username FROM followers")
            common_usernames = set(row[0] for row in common_cursor.fetchall())

            user_cursor.execute("SELECT username FROM followers")
            user_usernames = set(row[0] for row in user_cursor.fetchall())

            if not user_usernames:
                logger.info(f"First population of user {chat_id}'s database for account {tracked_account}. No notifications will be sent.")
                for username in common_usernames:
                    common_cursor.execute("SELECT * FROM followers WHERE username = ?", (username,))
                    follower = common_cursor.fetchone()
                    if follower:
                        user_cursor.execute('''INSERT INTO followers 
                            (user_id, name, username, bio, profile_url, followers_count, created_at, blue_verified, location) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                            follower[1:])  # Excluding the ID column
                user_conn.commit()
                logger.info(f"User {chat_id}'s database for {tracked_account} has been populated.")
                return  # Skip further processing for initial population

            # Find new followers
            new_followers = common_usernames - user_usernames
            logger.info(f"New followers found for account {tracked_account} for user {chat_id}: {new_followers}")

            if new_followers:
                for username in new_followers:
                    common_cursor.execute("SELECT * FROM followers WHERE username = ?", (username,))
                    follower = common_cursor.fetchone()
                    if follower:
                        user_cursor.execute("SELECT 1 FROM followers WHERE username = ?", (username,))
                        if not user_cursor.fetchone():  # Check if this follower exists in the user's DB
                            user_cursor.execute('''INSERT INTO followers 
                                (user_id, name, username, bio, profile_url, followers_count, created_at, blue_verified, location) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                follower[1:])  # Excluding the ID column
                            # Prepare the dictionary for notification, excluding tracked_account since it's not in the schema
                            follower_details = dict(zip(required_columns.values(), follower[1:]))
                            follower_details['tracked_account'] = tracked_account  # Add for notification purposes only
                            await send_follower_notification(chat_id, follower_details)
                        else:
                            logger.info(f"Follower {username} already exists in user {chat_id}'s database for {tracked_account}. Skipping.")
                user_conn.commit()
                logger.info(f"Updated followers for account {tracked_account} for user {chat_id}.")
            else:
                logger.info(f"No new followers for account {tracked_account} for user {chat_id}.")

    except sqlite3.Error as e:  # Handle database-specific errors
        logger.error(f"SQLite error updating followers for account {tracked_account} for user {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating followers for account {tracked_account} for user {chat_id}: {e}")

async def process_all_users():
    tasks = []
    for chat_id in [chat_id for chat_id in os.listdir(USER_DATA_FOLDER) if os.path.isdir(os.path.join(USER_DATA_FOLDER, chat_id))]:
        try:
            tracked_accounts = get_tracked_accounts(chat_id)
            if tracked_accounts:
                for account in tracked_accounts:
                    tasks.append(update_followers(chat_id, account))
        except Exception as e:
            logger.error(f"Error processing user {chat_id}: {e}")

    if tasks:
        # Use asyncio.gather with a timeout to manage long-running tasks
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=300)  # 5 minutes timeout
        except asyncio.TimeoutError:
            logger.error("Timeout occurred while processing all users.")
    else:
        logger.info("No users or tracked accounts found to process.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(process_all_users())
    except Exception as e:
        logger.error(f"An error occurred during the execution of the script: {e}")
