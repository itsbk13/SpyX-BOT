import sqlite3
import logging
from logger import logger
from sqlite3 import Error
from typing import List, Dict

DATABASE_FILE = 'kol_spyx_bot.db'

# Use the logger from logger.py
logger = logging.getLogger('KOL_SpyX_Bot')

def create_connection():
    """Create and return a connection to the database."""
    try:
        conn = sqlite3.connect(DATABASE_FILE, timeout=10.0)  # Added timeout for better handling of concurrent access
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error creating database connection: {e}")
        raise

def create_tables():
    """Create necessary tables if they don't exist."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()

            # Table for tracking which accounts users are following
            cursor.execute('''CREATE TABLE IF NOT EXISTS tracked_accounts (
                                username TEXT,
                                chat_id TEXT,
                                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                PRIMARY KEY (username, chat_id))''')


            # Indexing to improve query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracked_accounts_chat_id ON tracked_accounts(chat_id)")

        logger.info("Database tables created or verified.")
    except Error as e:
        logger.error(f"Error creating tables: {e}")
        raise

def add_account(username: str, chat_id: str) -> None:
    """Add a tracked account and associate it with a chat ID."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO tracked_accounts (username, chat_id) VALUES (?, ?)", (username, chat_id))
        logger.info(f"Account '{username}' added for chat_id {chat_id}.")
    except Error as e:
        logger.error(f"Error adding account '{username}' for chat_id {chat_id}: {e}")
        raise

def remove_account(username: str, chat_id: str) -> None:
    """Remove a tracked account for a specific user."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tracked_accounts WHERE username=? AND chat_id=?", (username, chat_id))
        logger.info(f"Account '{username}' removed for chat_id {chat_id}.")
    except Error as e:
        logger.error(f"Error removing account '{username}' for chat_id {chat_id}: {e}")
        raise

def get_tracked_accounts(chat_id: str) -> List[str]:
    """Retrieve all tracked accounts for a specific user."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM tracked_accounts WHERE chat_id=?", (chat_id,))
            return [row["username"] for row in cursor.fetchall()]
    except Error as e:
        logger.error(f"Error retrieving tracked accounts for chat_id {chat_id}: {e}")
        raise

def is_account_tracked_by_user(username: str, chat_id: str) -> bool:
    """Check if a specific user (chat_id) is tracking the account."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM tracked_accounts WHERE username=? AND chat_id=?", (username, chat_id))
            return cursor.fetchone() is not None
    except Error as e:
        logger.error(f"Error checking if account '{username}' is tracked by chat_id {chat_id}: {e}")
        raise

def delete_user_data(chat_id: str) -> None:
    """Delete all tracked accounts for a specific user."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tracked_accounts WHERE chat_id=?", (chat_id,))
        logger.info(f"All data for chat_id {chat_id} deleted.")
    except Error as e:
        logger.error(f"Error deleting user data for chat_id {chat_id}: {e}")
        raise

def add_follower_bulk(tracked_account: str, followers_data: List[Dict]) -> None:
    """Add multiple followers at once to improve performance."""
    try:
        if not followers_data:
            logger.info(f"No followers to add for tracked_account '{tracked_account}'.")
            return
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''INSERT INTO followers (
                                    tracked_account, user_id, name, username, bio, profile_url, 
                                    followers_count, created_at, blue_verified, location)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                  [(tracked_account, f['user_id'], f['name'], f['username'], f['bio'], 
                                    f['profile_url'], f['followers_count'], f['created_at'], 
                                    f['blue_verified'], f['location']) for f in followers_data])
        logger.info(f"Bulk followers added for tracked_account '{tracked_account}'.")
    except Error as e:
        logger.error(f"Error adding bulk followers for tracked account '{tracked_account}': {e}")
        raise

def get_followers(tracked_account: str) -> List[Dict]:
    """Retrieve all followers for a tracked account."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM followers WHERE tracked_account=?", (tracked_account,))
            return [dict(row) for row in cursor.fetchall()]
    except Error as e:
        logger.error(f"Error retrieving followers for tracked account '{tracked_account}': {e}")
        raise

def delete_followers(tracked_account: str) -> None:
    """Delete all followers for a specific tracked account."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM followers WHERE tracked_account=?", (tracked_account,))
        logger.info(f"All followers deleted for tracked_account '{tracked_account}'.")
    except Error as e:
        logger.error(f"Error deleting followers for tracked account '{tracked_account}': {e}")
        raise

def update_follower(tracked_account: str, follower_username: str, follower_data: Dict) -> None:
    """Update an existing follower's information."""
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM followers WHERE tracked_account=? AND username=?", (tracked_account, follower_username))
            if cursor.fetchone()[0] > 0:
                cursor.execute('''UPDATE followers SET 
                                    user_id=?, name=?, bio=?, profile_url=?, 
                                    followers_count=?, created_at=?, blue_verified=?, location=? 
                                  WHERE tracked_account=? AND username=?''', 
                                  (follower_data['user_id'], follower_data['name'], follower_data['bio'], 
                                   follower_data['profile_url'], follower_data['followers_count'], 
                                   follower_data['created_at'], follower_data['blue_verified'], 
                                   follower_data['location'], tracked_account, follower_username))
                logger.info(f"Follower '{follower_username}' updated for tracked_account '{tracked_account}'.")
            else:
                logger.info(f"Follower '{follower_username}' not found for tracked_account '{tracked_account}'.")
    except Error as e:
        logger.error(f"Error updating follower '{follower_username}' for tracked account '{tracked_account}': {e}")
                     
# Initialize tables when the module is loaded
create_tables()

if __name__ == "__main__":
    # Test database setup and log outcomes
    try:
        logger.info("Running database.py script.")
        create_tables()  # This ensures the tables are created, if not already
        logger.info("Database setup completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during standalone execution: {e}")