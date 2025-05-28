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
import datetime
from user_agents import parse as parse_ua
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Flask app setup
app = Flask(__name__)
CORS(app)

LOG_FILE = 'access.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

# Load environment variables
load_dotenv()

# Azure App credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET_VALUE = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANTID")
GRAPH_API_SCOPE = os.getenv("GRAPH_API_SCOPE")

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



# Authenticate with Azure AD and get an access token
def get_access_token():

    # Token endpoint URL
    Token_Auth_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    # Request access token
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET_VALUE,
        'scope': GRAPH_API_SCOPE
    }
    
    Token_Auth_Response = requests.post(Token_Auth_URL, data=token_data)
    
    if Token_Auth_Response.status_code == 200:
        return Token_Auth_Response.json().get("access_token")
    else:
        raise Exception(f"Failed to get access token: {Token_Auth_Response.text}")

# Get the access token
access_token = get_access_token()

# Check if the access token is valid
if not access_token:
        raise Exception("Failed to get access token")



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

# Access User Portfolio Coins DB Collection and return the collection
def UserPortfolioCoin_Collection():
    if client:
        CryptoCoinsdb = client['CryptoCoins']
        UserPortfolioCollection = CryptoCoinsdb['UserPortfolio']
        return UserPortfolioCollection
    else:
        print("MongoDB client is None. Cannot access user portfolio collection.")
        return None

# Get User Portfolio Coins DB Collection Data in JSON format
def get_user_portfolio_collection():
    try:
        UserPortfolioCollection = UserPortfolioCoin_Collection()
        if UserPortfolioCollection:
            data = []
            for doc in UserPortfolioCollection.find():
                doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                data.append(doc)
            return data
        else:
            print("User Portfolio Collection is None. Cannot retrieve data.")
            return []
    except Exception as e:
        print(f"❌ Error retrieving user portfolio collection: {e}")
        return []

# Add Crypto Coin list from CoinGecko API in MongoDB
def Fetch_CryptoCoinList():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/coins/list', timeout=10)
        CoinsList = response.json()

        if not isinstance(CoinsList, list) or not CoinsList:
            print("❌ Invalid or empty response received.")
            return []

        CryptoCoinsdb = client['CryptoCoins']
        CoinsListcollection = CryptoCoinsdb['CoinsList']

        try:
            result = CoinsListcollection.insert_many(CoinsList)
            print(f"✅ Inserted {len(result.inserted_ids)} documents into the collection.")
        except Exception as e:
            print("❌ Failed to insert data:", e)

        return CoinsList

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching coin list: {e}")
        return []

# Function to get coin list from MongoDB
def CryptoCoinList():
    if client:
        CryptoCoinsdb = client['CryptoCoins']
        CoinsListcollection = CryptoCoinsdb['CoinsList']
        
        # Load all coins without _id field
        CoinsList = list(CoinsListcollection.find({}, {'_id': 0}))
        if not CoinsList:
            print("No coins found in the collection.")
            return []
        print(f"Found {len(CoinsList)} coins in the collection.")
        return CoinsList
    
    else:
        print("MongoDB client is None. Cannot retrieve coin list.")
        return []

def start_scheduler():
    try:
        # Check if the client is connected
        scheduler = BackgroundScheduler()
        
        # Schedule job every day at 21:00 (9 PM)
        trigger = CronTrigger(hour=21, minute=0)
        scheduler.add_job(Fetch_CryptoCoinList, trigger=trigger)
        
        scheduler.start()
        print("📅 Scheduler started to run `get_coin_list` daily at 9 PM.")
    except Exception as e:
        print(f"❌ Failed to start scheduler: {e}")

scheduler_started = False

# Function to validate crypto symbol and name
def is_valid_crypto_symbol(symbol, coin_name=None):
    if not symbol or not isinstance(symbol, str):
        return "invalid_input"

    symbol = symbol.lower().strip()
    coin_name = coin_name.lower().strip() if coin_name and isinstance(coin_name, str) else None

    try:
        CoinsList = CryptoCoinList()

        if not CoinsList:
            return "local_data_empty"

        # Match coin by name
        name_matched_coins = [coin for coin in CoinsList if coin.get('name', '').lower() == coin_name]

        if not name_matched_coins:
            return "name_not_found"

        # Check for matching symbol among name-matched coins
        for coin in name_matched_coins:
            if coin.get('symbol', '').lower() == symbol:
                return "valid"

        return "symbol_mismatch"

    except Exception as e:
        print("❌ Error accessing local database:", e)
        return "db_error"




# Get Latest User Princple Name From the Report/Dashboard using My Flask API
def get_latest_user_principal_name_from_api():
    
    # URL for GET request to view stored user data
    Flask_API_URL = 'https://userprofile-ezcl.onrender.com/api/view_data'
    
    # Send GET request
    Flask_API_response = requests.get(Flask_API_URL)
    
    # Check if the response is valid
    if Flask_API_response.status_code == 200:
        # Parse the JSON response
        Flask_API_response = json.loads(Flask_API_response.text)
        
        # Extract the latest user principal name and date
        
        res = Flask_API_response[-1]
        
        print("Latest User Principal Name:", res['user_email'])
        print("Latest User Timestamp:", res['timestamp'])
        
        latest_user = {
            "user_email": res['user_email'],
            "timestamp": res['timestamp']
        }
        
        return latest_user
    else:
        raise Exception(f"Failed to get data from API: {Flask_API_response.get('message')}")

# Get the latest user principal name
latest_user = get_latest_user_principal_name_from_api()

# Get User Data from User Principal Name using Microsoft Graph API
def get_user_detail():

    # URL for GET request to Microsoft Graph API
    Graph_API_User_Id_URL = f"https://graph.microsoft.com/v1.0/users/{latest_user['user_email']}"

    # Set headers for the request
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Send GET request
    Graph_API_User_Id_response = requests.get(Graph_API_User_Id_URL, headers=headers)

    # Check if the response is valid
    if Graph_API_User_Id_response.status_code == 200:

        # Parse the JSON response
        Graph_API_User_Id_response = json.loads(Graph_API_User_Id_response.text)
        
        # Extract the user ID
        user_id = Graph_API_User_Id_response.get("id")
        
        if not user_id:
            raise Exception("User ID not found in the response")
        
        # Get User Details using Microsoft Graph API
        Graph_API_User_Data_URL = f"https://graph.microsoft.com/beta/users/{user_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Send GET request to get user data
        Graph_API_User_Data_response = requests.get(Graph_API_User_Data_URL, headers=headers)
        
        # Check if the response is valid
        if Graph_API_User_Data_response.status_code == 200:

            # Parse the JSON response
            UserData = json.loads(Graph_API_User_Data_response.text)

            return UserData
        else:

            raise Exception(f"Failed to get user data: {Graph_API_User_Data_response.text}")
    else:

        raise Exception(f"Failed to get user ID: {Graph_API_User_Id_response.text}")

# Get User Data
UserData = get_user_detail()

# Get User Profile Image from Microsoft Graph API
def get_user_profile_image():
    try:
        # URL for GET request to Microsoft Graph API
        Graph_API_User_Profile_Image_URL = f"https://graph.microsoft.com/v1.0/users/{UserData.get('id')}/photo/$value"

        # Set headers for the request
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        # Send GET request to Microsoft Graph API
        response = requests.get(Graph_API_User_Profile_Image_URL, headers=headers)

        if response.status_code == 200:
            # Save the image to a file
            image_path = "profile_image.jpg"
            with open(image_path, "wb") as f:
                f.write(response.content)
            print("✅ Profile image downloaded successfully.")

            # Upload to Uploadcare
            your_public_key = "339349e37fa6fcbc472f"
            upload_url = "https://upload.uploadcare.com/base/"

            with open(image_path, 'rb') as file:
                upload_response = requests.post(
                    upload_url,
                    data={
                        "UPLOADCARE_PUB_KEY": your_public_key,
                        "UPLOADCARE_STORE": "1"
                    },
                    files={"file": file}
                )

            if upload_response.status_code == 200:
                file_id = upload_response.json()["file"]
                img_url = f"https://ucarecdn.com/{file_id}/-/scale_crop/300x300/"
                print(f"🔗 Image URL: {img_url}")
                return img_url
            else:
                print("❌ Upload to Uploadcare failed:", upload_response.status_code, upload_response.text)
                return None
        else:
            print("❌ Failed to download profile image:", response.status_code, response.text)
            return None

    except Exception as e:
        print("🚨 An error occurred:", str(e))
        return None

# Get User Profile Image
UserProfileImage = get_user_profile_image()



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

@app.route('/receive-user-portfolio-coin', methods=['POST'])
def receive_user_portfolio_coin():
    try:
        data = request.json

        # Required fields
        required_fields = ["User Mail", "Name of Coin", "Coin Symbol", "Purchase Date"]

        missing_fields = []
        blank_fields = []

        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif str(data[field]).strip() == "":
                blank_fields.append(field)

        # Return specific error messages if any issues
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

        # Validate coin symbol and name
        coin_symbol = data['Coin Symbol']
        coin_name = data['Name of Coin']
        validation_result = is_valid_crypto_symbol(coin_symbol, coin_name)

        if validation_result == "name_not_found":
            return jsonify({
                "success": 'False',
                "message": "No coin available with this name"
            }), 200

        elif validation_result == "symbol_mismatch":
            return jsonify({
                "success": 'False',
                "message": "Symbol not aligned with the name"
            }), 200

        elif validation_result != "valid":
            return jsonify({
                "success": 'False',
                "message": "Coin validation failed due to API or network error"
            }), 200

        # Convert string date to datetime object
        try:
            print("Step 1: Attempting to retrieve 'Purchase Date' from input data...")
            purchase_date_str = data['Purchase Date']
            print(f"Step 2: 'Purchase Date' string received: {purchase_date_str}")

            try:
                print("Step 3: Trying to parse date using format YYYY-MM-DD...")
                parsed_date = datetime.datetime.strptime(purchase_date_str, "%Y-%m-%d")
                print(f"Step 4: Successfully parsed date (YYYY-MM-DD): {parsed_date}")
            except ValueError:
                print("Step 5: Failed to parse with YYYY-MM-DD. Trying MM/DD/YYYY format...")
                parsed_date = datetime.datetime.strptime(purchase_date_str, "%m/%d/%Y")
                print(f"Step 6: Successfully parsed date (MM/DD/YYYY): {parsed_date}")

            data['Purchase Date'] = parsed_date
            print(f"Step 7: Final parsed date stored in data: {data['Purchase Date']}")

        except Exception as e:
            print(f"Step 8: Exception occurred while parsing date: {str(e)}")
            return jsonify({
                "success": False,
                "message": "Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY."
            }), 200


        # Optional debug
        print("Final data to insert:", data)
        
        UserPortfolioCollection = UserPortfolioCoin_Collection()

        # Insert into MongoDB
        result = UserPortfolioCollection.insert_one(data)
        print("Inserted document ID:", result.inserted_id)

        return jsonify({
            "success": 'True',
            "message": "Crypto investment data saved successfully.",
            "id": str(result.inserted_id)
        }), 200

    except Exception as e:
        return jsonify({
            "success": 'False',
            "message": str(e)
        }), 200

# Flask route to handle the /getdata endpoint
@app.route('/getdata', methods=['GET'])
def getdata():

    # Create a proper UserDetail dictionary
    UserDetail = {
        "ID": UserData['id'],
        "Name":UserData['displayName'],
        "Mail Address":UserData['userPrincipalName'],
        "Image URL": UserProfileImage,
        "Job Title": UserData['jobTitle'],
        "business Phones Number": UserData['businessPhones'],
        "Phone Number": UserData['mobilePhone'],
        "Other Mail": UserData['otherMails'][0],
        "Address": UserData['streetAddress'],
        "City": UserData['city'],
        "State": UserData['state'],
        "Country": UserData['country'],
        "Postal Code": UserData['postalCode'],
        "Preferred Language": UserData['preferredLanguage'],
        "Identity Provider": UserData['identities'][0]['issuer'],
        "Timestamp": latest_user['timestamp']
    }
    
    # Create a proper DataFrame from the UserDetail dictionary
    User_Detail_df = pd.DataFrame([UserDetail])
    
    # Send the Gemini response to Telegram Bot
    # send_telegram_message(TELEGRAM_CHAT_ID, f"User Details:\n{UserDetail}")

    # Return both dataframes as a JSON response
    response = {
        "User_Detail": User_Detail_df.to_dict(orient='records')
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

# Initialize the scheduler in the app context
with app.app_context():
    if not scheduler_started:
        print("🚀 Initializing scheduler in app context...")
        start_scheduler()
        scheduler_started = True

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    print("🚨 Uncaught Exception:")
    traceback.print_exc()
    return jsonify({"error": str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)

