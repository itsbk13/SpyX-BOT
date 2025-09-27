import os
from telegram import Bot
from telegram.request import HTTPXRequest
from dotenv import load_dotenv

# Attempt to load from /etc/secrets/ (Render) first
dotenv_path = '/etc/secrets/.env'
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()  # fallback for local dev

# Retrieve API Token
API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    raise ValueError("API Token is missing! Please set it in the .env file or Render secrets.")

# Configure Bot
bot = Bot(
    token=API_TOKEN,
    request=HTTPXRequest(
        connection_pool_size=100,
        pool_timeout=120,
        read_timeout=120,
        write_timeout=120
    )
)

# User data folder
USER_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "userdata")
if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)
    print(f"Created user data folder at {USER_DATA_FOLDER}")
