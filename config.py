from telegram import Bot
import os
from telegram.request import HTTPXRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve API Token, raise an exception if not found
API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    raise ValueError("API Token is missing! Please set it in the .env file.")

# Configure Bot with custom request handler for better performance
bot = Bot(token=API_TOKEN, 
          request=HTTPXRequest(
              connection_pool_size=100, 
              pool_timeout=120, 
              read_timeout=120,  # Add read timeout for long operations
              write_timeout=120  # Add write timeout for long uploads
          ))

# Set up user data folder path
USER_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "userdata")

# Ensure the user data folder exists
if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)
    print(f"Created user data folder at {USER_DATA_FOLDER}")

# More configuration variables could be added here if needed
# Example:
# TIMEZONE = os.getenv('TIMEZONE', 'UTC')  # Default to UTC if TIMEZONE is not set
