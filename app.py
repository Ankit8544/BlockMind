from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
import logging
import re
import time
import threading
from user_agents import parse as parse_ua
from Functions.MongoDB import get_user_portfolio_data, get_user_meta_data, refersh_cryptodata, get_crypto_data
from Functions.TelegramBot import handle_start, handle_message, set_webhook
from Functions.BlockMindsStatusBot import send_status_message
from Functions.Analysis import Analysis
import sys

# Status TELEGRAM CHAT I'D
Status_TELEGRAM_CHAT_ID = os.getenv("Status_TELEGRAM_CHAT_ID")

sys.stdout.reconfigure(line_buffering=True)

# Flask app setup
app = Flask(__name__)
CORS(app)

LOG_FILE = 'access.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

# Load crypto analysis data
def load_data():
    try:
        df = Analysis()
        send_status_message(Status_TELEGRAM_CHAT_ID, f"✅ Based on User Portfolio {df.shape[0]} CryptoCoins Data is loaded successfully in the Flask App.")
        if df is None or df.empty:
            raise ValueError("Analysis() returned an empty DataFrame.")
        
        refersh_cryptodata(df=df)
        
    except Exception as e:
        print(f"❌ Error loading crypto analysis data: {e}")
        return pd.DataFrame()

def run_periodic_loader():
    """Periodically runs load_data every 30 minutes AFTER each successful completion."""
    while True:
        try:
            send_status_message(Status_TELEGRAM_CHAT_ID, f"🔄 Starting periodic data loading at: {datetime.now().strftime('%H:%M:%S')}")
            load_data()  # This will refresh MongoDB data via refersh_cryptodata inside load_data()
        except Exception as e:
            print(f"❌ Error in periodic data load: {e}")
        finally:
            send_status_message(Status_TELEGRAM_CHAT_ID, "⏳ Waiting 10 minutes before next load...")
            time.sleep(600)  # Wait after completion of each run

@app.after_request
def log_request(response):
    logging.info(
        f'{request.remote_addr} - - [{datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] '
        f'"{request.method} {request.path} HTTP/1.1" {response.status_code} {response.calculate_content_length() or "-"} '
        f'"{request.referrer or "-"}" "{request.user_agent}"'
    )
    return response

# Flask route to handle the home page
@app.route('/')
def home():
    try:
        return '''
            <html>
                <head><title>Crypto API</title></head>
                <body>
                    <h1>✅ Crypto API is Live!</h1>
                    <p>Visit <code>/getdata</code> to get the portfolio data in JSON.</p>
                </body>
            </html>
        '''
    except Exception as e:
        print("❌ Error in / route:", str(e))
        return jsonify({"error": str(e)}), 500

# Flask route to handle the /getdata endpoint
@app.route('/getdata', methods=['GET'])
def getdata():

    # Return both dataframes as a JSON response
    response = {
        "User Meta Data": get_user_meta_data(),
        "User Portfolio": get_user_portfolio_data(),
        "User Portfolio Based Crypto Data": get_crypto_data()
    }
    
    # Convert to JSON and return
    return jsonify(response)

@app.route('/getlogs')
def get_logs():
    log_entries = []
    pattern = re.compile(
        r'(?P<ip>\S+) - - \[(?P<datetime>[^\]]+)\] "(?P<method>\S+) (?P<endpoint>\S+) HTTP/\d\.\d" (?P<status>\d{3}) (?P<size>\d+|-) "(?P<referrer>[^"]*)" "(?P<user_agent>[^"]+)"'
        )

    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            match = pattern.search(line)
            
            if match and match.group("endpoint") == "/getdata":
                dt = datetime.strptime(match.group("datetime"), "%d/%b/%Y:%H:%M:%S %z")
                ua_str = match.group("user_agent")
                ua = parse_ua(ua_str)

                log_entries.append({
                    "timestamp": dt.isoformat(),
                    "ip": match.group("ip"),
                    "endpoint": match.group("endpoint"),
                    "method": match.group("method"),
                    "status_code": int(match.group("status")),
                    "response_size": int(match.group("size")) if match.group("size").isdigit() else None,
                    "referrer": match.group("referrer"),
                    "user_agent": ua_str,
                    "device": {
                        "is_mobile": ua.is_mobile,
                        "is_tablet": ua.is_tablet,
                        "is_pc": ua.is_pc,
                        "is_bot": ua.is_bot,
                        "browser": ua.browser.family,
                        "os": ua.os.family,
                        "device_type": ua.device.family
                    }
                })

        return jsonify(log_entries[-1:])  # Last one Entries
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """Receives Telegram messages and responds."""
    update = request.get_json()
    
    if not update or "message" not in update:
        return jsonify({"status": "ignored"}), 400
    
    chat_id = update["message"]["chat"]["id"]
    text = update["message"].get("text", "").strip().lower()

    if text == "/start":
        handle_start(chat_id)
    else:
        handle_message(chat_id, text, df=pd.DataFrame(get_crypto_data()))

    return jsonify({"status": "ok"}), 200

# Set WebHook for real time reply
with app.app_context():
    set_webhook()

# Start the background thread ONCE when the app starts
with app.app_context():
    if os.environ.get("FLASK_ENV") == "development":
        print("🚀 Starting background data loader thread...")
        loader_thread = threading.Thread(target=run_periodic_loader, daemon=True)
        loader_thread.start()
        print("🧵 Data loader thread started.")
