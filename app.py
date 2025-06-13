from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
import logging
import re
import threading
from user_agents import parse as parse_ua
from Functions.MongoDB import get_user_portfolio_data, get_user_meta_data
from Functions.TelegramBot import handle_start, handle_message, set_webhook

# Flask app setup
app = Flask(__name__)
CORS(app)

LOG_FILE = 'access.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

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
        return "🚀 App is live and running!"
    except Exception as e:
        print("❌ Error in / route:", str(e))
        return jsonify({"error": str(e)}), 500

# Flask route to handle the /getdata endpoint
@app.route('/getdata', methods=['GET'])
def getdata():

    # Return both dataframes as a JSON response
    response = {
        "User_Detail": get_user_meta_data(),
        "User_Portfolio": get_user_portfolio_data()
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
        handle_message(chat_id, text, df=df)

    return jsonify({"status": "ok"}), 200

# Set WebHook for real time reply
with app.app_context():
    set_webhook()

# Start background thread only once when the app starts
with app.app_context():
    if os.environ.get("FLASK_ENV") == "development":
        print("🔹 Background worker started!")
        thread = threading.Thread(target=load_data, daemon=True)
        thread.start()
        print("Thread Started")

if __name__ == "__main__":
    try:
        port = int(os.environ["PORT"])
        print(f"Assigned Port Number: {port}")
        print(f"App listening on port {port}")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    except Exception as e:
        print(f"❌ Error starting the Flask server: {e}")
