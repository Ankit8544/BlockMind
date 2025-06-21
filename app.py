from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import pytz
import os
import logging
import re
import time
import threading
from user_agents import parse as parse_ua
from Functions.MongoDB import UserPortfolio_Data, UserMetadata_Data, refersh_cryptodata, CryptoCoins_Data, is_valid_crypto_symbol, validate_crypto_payload, CryptoCoinList_Data, validate_crypto_payload, UserMetadata_Collection, UserPortfolioCoin_Collection
from Functions.TelegramBot import handle_start, handle_message, set_webhook
from Functions.BlockMindsStatusBot import send_status_message
from Functions.Analysis import Analysis
from Functions.UserMetaData import user_metadata

# Status TELEGRAM CHAT I'D
Status_TELEGRAM_CHAT_ID = os.getenv("Status_TELEGRAM_CHAT_ID")

# Flask app setup
app = Flask(__name__)
CORS(app)

# Configure logging
LOG_FILE = 'access.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

# Set timezone for status messages
ist = pytz.timezone('Asia/Kolkata')

# Load crypto analysis data
def load_data():
    try:
        df = Analysis()
        print(f"✅ Based on User Portfolio {df.shape[0]} CryptoCoins Data is loaded successfully in the Flask App. {datetime.now(ist).strftime('%H:%M:%S')}")
        if df is None or df.empty:
            raise ValueError("Analysis() returned an empty DataFrame.")
        
        refersh_cryptodata(df=df)
        
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error loading crypto analysis data: {e}")
        return pd.DataFrame()

# Periodic data loader function
def run_periodic_loader():
    
    while True:
        try:
            send_status_message(Status_TELEGRAM_CHAT_ID, f"🔄 Starting periodic data load at {datetime.now(ist).strftime('%H:%M:%S')}.")
            load_data()  # This will refresh MongoDB data via refresh_cryptodata inside load_data()
            send_status_message(Status_TELEGRAM_CHAT_ID, f"✅ MongoDB 'CryptoAnalysis' collection uploaded successfully at {datetime.now(ist).strftime('%H:%M:%S')}.")
        
        except Exception as e:
            send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error in periodic data load: {e}")
        
        finally:
            print(Status_TELEGRAM_CHAT_ID, "⏳ Waiting for 30 minutes to update the data")
            time.sleep(1800)  # Wait after completion of each run

# Load initial data
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
        send_status_message(Status_TELEGRAM_CHAT_ID, "❌ Error in / route:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/receive-coins-from-power-app', methods=['POST'])
def receive_crypto_coins_detail_from_power_app():
    try:
        data = request.json

        # Step 1: Basic field presence check (original keys)
        required_fields = ["User Mail", "Name of Coin", "Coin Symbol", "Purchase Date"]
        missing_fields = []
        blank_fields = []

        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif str(data[field]).strip() == "":
                blank_fields.append(field)

        if missing_fields or blank_fields:
            errors = []
            if missing_fields:
                errors.append(f"Missing fields: {', '.join(missing_fields)}")
            if blank_fields:
                errors.append(f"Blank fields: {', '.join(blank_fields)}")
            return jsonify({
                "success": False,
                "message": " | ".join(errors)
            }), 200

        # Step 2: Validate coin name and symbol
        coin_symbol = data['Coin Symbol']
        coin_name = data['Name of Coin']
        validation_result = is_valid_crypto_symbol(coin_symbol, coin_name)

        if validation_result == "name_not_found":
            return jsonify({"success": 'False', "message": "No coin available with this name"}), 200
        elif validation_result == "symbol_mismatch":
            return jsonify({"success": 'False', "message": "Symbol not aligned with the name"}), 200
        elif validation_result != "valid":
            return jsonify({"success": 'False', "message": "Coin validation failed due to API or network error"}), 200

        # Step 3: Handle and format purchase date: ensure it's in string ISO format (YYYY-MM-DD)
        try:
            import datetime
            purchase_date_str = data['Purchase Date']
            try:
                parsed_date = datetime.datetime.strptime(purchase_date_str, "%Y-%m-%d")
            except ValueError:
                parsed_date = datetime.datetime.strptime(purchase_date_str, "%m/%d/%Y")
            iso_date = parsed_date.strftime("%Y-%m-%d")
        except Exception:
            return jsonify({"success": 'False', "message": "Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY."}), 200

        from datetime import datetime
        
        # Step 4: Normalize data
        cleaned_data = {
            "user_mail": data['User Mail'].strip(),       # normalize email
            "coin_name": coin_name.strip(),
            "coin_symbol": coin_symbol.strip().lower(),
            "purchase_date": iso_date                             # ISO string format
        }
        
        # Step 6: Insert User Metadata
        try:
            # Initialize collection
            UserMetaDataCollection = UserMetadata_Collection()
            
            # Check for existing user by email
            existing_user = UserMetaDataCollection.find_one({"mail_address": cleaned_data['user_mail']})

            if existing_user:
                print(f"User with email {cleaned_data['user_mail']} already exists. Skipping insertion.")
            else:
                print("Inserting User MetaData:")
                try:
                    # Create a proper UserDetail dictionary 
                    UserDetail = user_metadata(cleaned_data['user_mail'])
                    UserMetaDataCollection.insert_one(UserDetail)
                    print("User MetaData inserted successfully.")
                except Exception as e:
                    print(f"⚠️ Skipping User Metadata insertion due to error: {e}")
        except Exception as e:
            print(f"⚠️ Failed to process User Metadata logic: {e}")
        
        # Step 7: Validate MongoDB Payload Format
        is_valid, msg = validate_crypto_payload(cleaned_data)
        if not is_valid:
            return jsonify({"success": 'False', "message": msg}), 200

        # Step 8: Insert into MongoDB
        UserPortfolioCollection = UserPortfolioCoin_Collection()
        result = UserPortfolioCollection.insert_one(cleaned_data)
        print(f"✅ Data inserted with ID: {result.inserted_id}")
        print(f"Inserted data: {cleaned_data}")

        # Step 9: Return success response
        print("🚀 Crypto investment data saved successfully.")
        return jsonify({
            "success": 'True',
            "message": "Crypto investment data saved successfully.",
            "id": str(result.inserted_id)
        }), 200

    except Exception as e:
        return jsonify({"success": 'False', "message": str(e)}), 200

# Flask route to get data
@app.route('/getdata', methods=['GET'])
def getdata():

    # Return both dataframes as a JSON response
    response = {
        "User Meta Data": UserMetadata_Data(),
        "User Portfolio": UserPortfolio_Data(),
        "User Portfolio Based Crypto Data": CryptoCoins_Data()
    }
    
    # Convert to JSON and return
    return jsonify(response)

# Flask route to get logs
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

# Flask route to handle Telegram webhook
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json()

    if not update or "message" not in update:
        return jsonify({"status": "ignored"}), 400

    message = update["message"]
    print(f"Received message: {message}")
    chat_id = message["chat"]["id"]
    print(f"Chat ID: {chat_id}")
    text = message.get("text", "").strip().lower()
    print(f"Message text: {text}")

    # Extract user info
    user_info = message.get("from", {})
    print(f"User info: {user_info}")
    first_name = user_info.get("first_name", "")
    print(f"First name: {first_name}")
    last_name = user_info.get("last_name", "")
    print(f"Last name: {last_name}")
    username = user_info.get("username", "")
    print(f"Username: {username}")
    full_name = first_name or username or "there"
    print(f"Full name: {full_name}")

    if text == "/start":
        handle_start(chat_id, full_name)
    else:
        handle_message(chat_id, text, df=pd.DataFrame(CryptoCoins_Data()))

    return jsonify({"status": "ok"}), 200

# ✅ Flask route to add Telegram username WITHOUT verifying it
@app.route('/subscribe', methods=['POST'])
def add_telegram_username():
    try:
        data = request.json
        email = data.get("email")
        telegram_username = data.get("telegram_username")

        if not email or not telegram_username:
            return jsonify({
                "success": False,
                "message": "Both 'email' and 'telegram_username' are required."
            }), 400

        # ✅ SKIP: no sending message, no checking UserMetadata

        # ✅ Directly update all UserPortfolio docs with this email:
        portfolio_collection = UserPortfolioCoin_Collection()
        result = portfolio_collection.update_many(
            {"user_mail": email},
            {
                "$set": {
                    "telegram_username": telegram_username
                }
            },
            upsert=False
        )

        if result.matched_count == 0:
            return jsonify({
                "success": False,
                "message": f"No user portfolio found for email: {email}"
            }), 404

        return jsonify({
            "success": True,
            "message": f"✅ Telegram username '{telegram_username}' saved for all portfolio entries for email '{email}'."
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

# Flask route to handle keepalive pings
@app.route('/keepalive')
def keep_alive():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"🟢 Keepalive ping received at {now}")
    return jsonify({"status": "alive", "time": now}), 200

# Set WebHook for real time reply
with app.app_context():
    set_webhook()

# Start the background thread ONCE when the app starts
with app.app_context():
    Flask_ENV = os.environ.get("FLASK_ENV", "production")
    print(f"Flask ENV: {Flask_ENV}")
    if os.environ.get("FLASK_ENV") == "development":
        print("🚀 Starting background data loader thread.")
        loader_thread = threading.Thread(target=run_periodic_loader, daemon=True)
        loader_thread.start()
        print("🧵 Data loader thread started.")

if __name__ == '__main__':
    # Run the Flask app
    app.run()