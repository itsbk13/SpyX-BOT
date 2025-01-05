import logging
from logging.handlers import RotatingFileHandler

# Set the log file and maximum size
log_file = 'KOL_SpyX_Bot.log'  # You can change the log file name here
max_bytes = 5 * 1024 * 1024  # 5MB max size per log file
backup_count = 3  # Keep up to 3 backup files

log_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
log_handler.setLevel(logging.INFO)  # Set the log level to INFO or DEBUG
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)

# Get the logger and add the handler
logger = logging.getLogger('KOL_SpyX_Bot')
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)  # Set global logging level

# Optionally add a console handler for debugging
if __name__ == '__main__':
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Set console output to DEBUG level for more verbose output
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

# Disable propagation of log messages to the root logger
logger.propagate = False

# Ensure that logs from external libraries like requests and telegram are also captured
external_loggers = ['requests', 'urllib3', 'telegram', 'httpx']
for lib in external_loggers:
    logging.getLogger(lib).setLevel(logging.WARNING)  # Set to capture WARNING and higher

# Log setup info
logger.info("Logging setup initialized.")