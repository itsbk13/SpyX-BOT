from telegram import Bot
from telegram.request import HTTPXRequest
import os
import sys

# Ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Retrieve API Token with better error handling
API_TOKEN = os.environ.get('API_TOKEN') or os.getenv('API_TOKEN')
if not API_TOKEN:
    print("ERROR: API_TOKEN environment variable not found!")
    print("Available environment variables:")
    for key in sorted(os.environ.keys()):
        if 'TOKEN' in key.upper() or 'API' in key.upper():
            print(f"  {key}")
    raise ValueError("API Token is missing! Please set 'API_TOKEN' in Render Environment Variables.")

print(f"API Token found: {API_TOKEN[:10]}..." if API_TOKEN else "No API Token")

# Configure Bot with custom request handler for better performance
try:
    bot = Bot(token=API_TOKEN, 
              request=HTTPXRequest(
                  connection_pool_size=100, 
                  pool_timeout=120, 
                  read_timeout=120,  # Add read timeout for long operations
                  write_timeout=120  # Add write timeout for long uploads
              ))
    print("Bot initialized successfully")
except Exception as e:
    print(f"ERROR: Failed to initialize bot: {e}")
    raise

# Set up user data folder path
USER_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "userdata")

# Ensure the user data folder exists
if not os.path.exists(USER_DATA_FOLDER):
    try:
        os.makedirs(USER_DATA_FOLDER)
        print(f"Created user data folder at {USER_DATA_FOLDER}")
    except Exception as e:
        print(f"ERROR: Could not create user data folder: {e}")
        raise
else:
    print(f"User data folder exists at {USER_DATA_FOLDER}")
