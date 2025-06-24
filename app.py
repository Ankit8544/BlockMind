from datetime import datetime
from flask import Flask, jsonify, request, render_template, url_for
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
from Functions.RazorPay import check_payment_status
import razorpay
import time

# Status TELEGRAM CHAT I'D
Status_TELEGRAM_CHAT_ID = os.getenv("Status_TELEGRAM_CHAT_ID")

# Flask app setup
app = Flask(__name__)
CORS(app)

# Configure logging
LOG_FILE = 'access.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

# 🌐 Set for correct URL generation
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.config['SERVER_NAME'] = 'cryptodata-pnzi.onrender.com'  # Replace with your actual domain

# 🔐 Razorpay credentials
RAZORPAY_KEY = os.getenv('RAZORPAY_KEY')
RAZORPAY_SECRET = os.getenv('RAZORPAY_SECRET')

if not RAZORPAY_KEY or not RAZORPAY_SECRET:
    raise ValueError("Razorpay credentials are missing. Set RAZORPAY_KEY and RAZORPAY_SECRET.")

# Razorpay client setup
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

# In-memory store (replace with DB in production)
pending_users = {}

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
            print(f"🔄 Starting periodic data load at {datetime.now(ist).strftime('%H:%M:%S')}.")
            load_data()  # This will refresh MongoDB data via refresh_cryptodata inside load_data()
            print(f"✅ MongoDB 'CryptoAnalysis' collection uploaded successfully at {datetime.now(ist).strftime('%H:%M:%S')}.")
        
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

# Flask route to receive crypto coins detail from Power App with payment
@app.route('/receive-coins-from-power-app-with-paymewnt', methods=['POST'])
def receive_crypto_coins_detail_from_power_app_with_payment():
    try:
        data = request.json

        # Step 1: Basic field presence check
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
                "success": 'False',
                "message": " | ".join(errors)
            }), 200  # Always returning 200

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

        # Step 3: Validate purchase date format
        try:
            purchase_date_str = data['Purchase Date']
            try:
                parsed_date = datetime.strptime(purchase_date_str, "%Y-%m-%d")
            except ValueError:
                parsed_date = datetime.strptime(purchase_date_str, "%m/%d/%Y")
            # Converting to ISO just for validation
            _ = parsed_date.strftime("%Y-%m-%d")
        except Exception:
            return jsonify({
                "success": 'False',
                "message": "Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY."
            }), 200

        # ✅ All validations passed
        return jsonify({
            "success": 'True',
            "message": "Crypto data validated successfully. Proceeding to payment details... "
        }), 200

    except Exception as e:
        return jsonify({
            "success": 'False',
            "message": f"Unexpected error: {str(e)}"
        }), 200

# Flask route to start payment
@app.route('/start-payment', methods=['POST', 'GET'])
def start_payment():
    if request.method == 'POST':
        try:
            data = request.get_json(force=True)
            
            # ✅ Step 1: Field presence validation
            required_fields = ['name', 'email', 'mobile', 'amount']
            missing_fields = []
            blank_fields = []

            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
                elif str(data.get(field)).strip() == "":
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

            # ✅ Step 2: Normalize inputs
            name = data.get('name')
            email = data.get('email')
            mobile = data.get('mobile')
            amount = float(data.get('amount'))
            try:
                amount = float(data['amount'])
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": "Amount must be numeric."
                }), 200

            user_id = f"{email}_{mobile}"
            
            wait_url = url_for('wait_for_payment', user_id=user_id, _external=True)
            print("🔑 User ID generated:", user_id)
            print("🔗 Wait URL generated:", wait_url)

            # ✅ Step 3: Create Razorpay order
            order_data = {
                "amount": int(amount * 100),  # convert to paise
                "currency": "INR",
                "receipt": user_id,
                "payment_capture": 1
            }

            order = razorpay_client.order.create(order_data)

            created_at = int(time.time())
            expires_at = created_at + 120  # 2 min TTL

            pending_users[user_id] = {
                'name': name,
                'email': email,
                'mobile': mobile,
                'amount': amount,
                'status': 'pending',
                'razorpay_order_id': order['id'],
                'razorpay_payment_id': None,
                'created_at': created_at,
                'expires_at': expires_at
            }

            payment_url = url_for('start_payment', user_id=user_id, _external=True)
            return jsonify({
                "success": True,
                "message": "Payment session created successfully.",
                "payment_url": payment_url,
                "wait_url": wait_url,
                "razorpay_key": RAZORPAY_KEY,
                "order_id": order['id'],
                "user_id": user_id
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 200

    # GET: Render payment.html
    user_id = request.args.get('user_id')
    if user_id in pending_users:
        now = int(time.time())
        if now > pending_users[user_id]['expires_at']:
            return "Payment session expired", 410

        return render_template('payment.html',
                               user=pending_users[user_id],
                               user_id=user_id,
                               order_id=pending_users[user_id]['razorpay_order_id'],
                               razorpay_key=RAZORPAY_KEY)
    else:
        return "Invalid or expired session", 404

# Flask route to handle payment status check
@app.route('/check-payment-status', methods=['GET', 'POST'])
def check_payment_status_via_route():
    try:
        order_id = None
        timeout_minutes = 20
        poll_interval = 5

        if request.method == 'GET':
            order_id = request.args.get('order_id')
            timeout_minutes = int(request.args.get('timeout', 20))
            poll_interval = int(request.args.get('interval', 5))

        elif request.method == 'POST':
            data = request.get_json(force=True)
            order_id = data.get('order_id')
            timeout_minutes = int(data.get('timeout', 20))
            poll_interval = int(data.get('interval', 5))

        # Validate order_id
        if not order_id:
            return jsonify({
                "success": False,
                "status": "error",
                "message": "Missing or invalid 'order_id'.",
                "order_id": None,
                "payment_id": None
            }), 200

        print(f"🔍 Checking payment status for order_id: {order_id}, timeout={timeout_minutes} min, interval={poll_interval}s")

        # Call the core function with all parameters
        result = check_payment_status(order_id, timeout_minutes, poll_interval)

        print(f"✅ Payment check result: {result['status']} for order_id: {order_id}")

        return jsonify(result), 200

    except Exception as e:
        print(f"❌ Error during payment status check: {str(e)}")
        return jsonify({
            "success": False,
            "status": "error",
            "message": f"Internal server error: {str(e)}",
            "order_id": None,
            "payment_id": None
        }), 200

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
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip().lower()

    # Extract user info
    user_info = message.get("from", {})
    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    username = user_info.get("username", "")
    full_name = f"{first_name} {last_name}"
    print(f"Received message from {full_name} with the username as '{username}' in chat {chat_id}: {text}")

    if text == "/start":
        handle_start(chat_id, full_name)
    else:
        handle_message(chat_id, text, username=username, full_name=full_name)

    return jsonify({"status": "ok"}), 200

# ✅ Flask route to add Telegram username WITHOUT verifying it
@app.route('/subscribe', methods=['POST'])
def add_telegram_username():
    try:
        data = request.json
        email = data.get("email")
        new_username = data.get("telegram_username")

        if not email or not new_username:
            print("❌ Missing email or telegram_username in request.")
            return jsonify({
                "success": False,
                "message": "Both 'email' and 'telegram_username' are required."
            }), 400

        portfolio_collection = UserPortfolioCoin_Collection()
        users = list(portfolio_collection.find({"user_mail": email}))

        if len(users) == 0:
            print(f"❌ No user portfolio found for email: {email}")
            return jsonify({
                "success": False,
                "message": f"No user portfolio found for email: {email}"
            }), 404

        updated = False
        for user in users:
            # Collect existing telegram_username_* fields
            username_fields = {k: v for k, v in user.items() if k.startswith("telegram_username")}
            existing_usernames = list(username_fields.values())

            if new_username in existing_usernames:
                print(f"⚠️ Username '{new_username}' already exists for email: {email}. Skipping.")
                continue

            # Find the next available field name
            index = 1
            while f"telegram_username_{index}" in user:
                index += 1

            new_field = f"telegram_username_{index}"
            portfolio_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {new_field: new_username}}
            )
            print(f"✅ Added '{new_username}' to field '{new_field}' for email: {email}")
            updated = True

        if updated:
            return jsonify({
                "success": True,
                "message": f"✅ Telegram username '{new_username}' added in a new field for email '{email}'."
            }), 200
        else:
            return jsonify({
                "success": True,
                "message": f"⚠️ Telegram username '{new_username}' already exists for email '{email}'. No update needed."
            }), 200

    except Exception as e:
        print(f"🔥 Error: {str(e)}")
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
    app.run()