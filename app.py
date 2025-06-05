import requests
import pandas as pd
import json
from datetime import datetime
import pytz
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import google.generativeai as genai
import logging
import re
from user_agents import parse as parse_ua
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from Analysis import Analysis

# Flask app setup
app = Flask(__name__)
CORS(app)

LOG_FILE = 'access.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

# Load environment variables
load_dotenv()

# Google Gemini API credentials
GEMINI_API_KEYS = [
    (os.getenv("ankitkumar875740")),
    (os.getenv("kingoflovee56")), 
    (os.getenv("bloodycrewff"))
    ]

# Telegram Bot credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Imgur API credentials
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")

# MongoDB Credentials
MONGO_DB_USERNAME = os.getenv("MONGO_DB_USERNAME")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")

# Set the timezone to UTC+5:30
ist = pytz.timezone('Asia/Kolkata')

# Get Valid Gemini API Key
def get_valid_api_key():
    for key in GEMINI_API_KEYS:
        try:
            genai.configure(api_key=key)
            genai.GenerativeModel('gemini-1.5-pro')  # Only configures the model without generating content
            return key
        except Exception as e:
            print(f"API key {key} failed: {e}")
    return None

# Get a valid Gemini API key
GEMINI_API_KEY = get_valid_api_key()

# Check if a valid API key was found
if not GEMINI_API_KEY:
    raise Exception("No valid Gemini API key found.")

# Configure Gemini AI
def Gemini(user_message):
    """Generates AI response using Gemini API."""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(user_message)
        if response and hasattr(response, "text"):
            return response.text.strip()
        return "I'm unable to process that request right now."
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return "🚫 AI is currently unavailable. Try again later."

def AI_Generated_Answer(user_message):
    gemini_result = Gemini(user_message)
    
    try:
        result = gemini_result.replace('*', '')
        return result
    except:
        print("⚠️ Unfortunatly, We are not able responed you right now.")
        return "🚫 AI is currently unavailable. Try again later."

# Configure Telegram Bot to send messages
def send_telegram_message(chat_id, message):
    """Sends a message to a specific Telegram user."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram API Error: {e}")
        return {"error": str(e)}

# Check if environment variables are set
if not MONGO_DB_USERNAME or not MONGO_DB_PASSWORD:
    raise ValueError("MongoDB credentials are not set in the environment variables.")

# MongoDB connection setup
def connect_to_mongo():
    print("Connecting to MongoDB...")
    uri = f"mongodb+srv://{MONGO_DB_USERNAME}:{MONGO_DB_PASSWORD}@cluster0.ou0xiys.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        print("MongoDB connection error:", e)
        return None

# Connect to MongoDB
client = connect_to_mongo()

# Get User Portfolio Coins DB Collection Data in JSON format
def get_user_portfolio_data():
    try:
        if client:
            CryptoCoinsdb = client['CryptoCoins']
            UserPortfolioCollection = CryptoCoinsdb['UserPortfolio']
            if UserPortfolioCollection is not None:
                print("User Portfolio Collection is connected successfully.")
                # Retrieve all documents from the collection and store them in a dict
                Assets = []
                for doc in UserPortfolioCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    Assets.append(doc)
                print(f"Retrieved {len(Assets)} assets from User Portfolio Collection.")
                return Assets
            else:
                print("User Portfolio Collection is None. Cannot retrieve data.")
                return {}
        else:
            print("MongoDB client is None. Cannot access user portfolio collection.")
            return {}
    except Exception as e:
        print(f"❌ Error retrieving user portfolio collection: {e}")
        return {}

# Get User Meta Data in JSON format
def get_user_meta_data():
    try:
        if client:
            CryptoCoinsdb = client['CryptoCoins']
            UserMetaCollection = CryptoCoinsdb['UserMetadata']
            if UserMetaCollection is not None:
                print("User Meta Collection is connected successfully.")
                # Retrieve all documents from the collection and store them in a dict
                Metadata = []
                for doc in UserMetaCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    Metadata.append(doc)
                print(f"Retrieved {len(Metadata)} metadata entries from User Meta Collection.")
                return Metadata
            else:
                print("User Meta Collection is None. Cannot retrieve data.")
                return {}
        else:
            print("MongoDB client is None. Cannot access user meta collection.")
            return {}
    except Exception as e:
        print(f"❌ Error retrieving user meta collection: {e}")
        return {}

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
    
    df = Analysis()
    Crpto_Data = df.to_dict(orient='records')

    # Send the Gemini response to Telegram Bot
    # send_telegram_message(TELEGRAM_CHAT_ID, f"User Details:\n{UserDetail}")

    # Return both dataframes as a JSON response
    response = {
        "User_Detail": get_user_meta_data(),
        "User_Portfolio": get_user_portfolio_data(),
        "Crypto_Data": Crpto_Data
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

# Run the Flask app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)

