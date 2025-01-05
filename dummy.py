import os
from flask import Flask

app = Flask(__name__)

# Use the environment variable or default to 8080
port = os.getenv("PORT", 8080)

@app.route('/')
def home():
    return "Hello World!"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port)
