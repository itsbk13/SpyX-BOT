from flask import Flask
import threading
import time

app = Flask(__name__)

@app.route('/')
def index():
    return 'Bot is running!'

def track_followers():
    while True:
        print("Tracking followers...")
        time.sleep(3600)  # Check every hour

if __name__ == "__main__":
    threading.Thread(target=track_followers).start()  # Start background task
    app.run(host="0.0.0.0", port=8080)  # Start Flask server to bind to port 8080
