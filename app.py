import requests
import pandas as pd
import requests
import json
from datetime import datetime
import pytz
import time
from flask import Flask, jsonify, request
from dotenv import load_dotenv
import os
import google.generativeai as genai
import logging
import re
from datetime import datetime
from user_agents import parse as parse_ua

app = Flask(__name__)

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

        # Parse the timestamp
        utc_time = datetime.strptime(res['timestamp'][:26], "%Y-%m-%dT%H:%M:%S.%f")
        utc_time = utc_time.replace(tzinfo=pytz.UTC)

        # Convert to IST
        ist_time = utc_time.astimezone(ist)

        latest_user = {
            "user_email": res['user_email'],
            "timestamp": ist_time.strftime("%Y-%m-%d %H:%M:%S")
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
    
    # URL for GET request to Microsoft Graph API
    Graph_API_User_Profile_Image_URL = f"https://graph.microsoft.com/v1.0/users/{UserData.get('id')}/photo/$value"

    # Set headers for the request
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Send GET request
    Graph_API_User_Profile_Image_response = requests.get(Graph_API_User_Profile_Image_URL, headers=headers)

    # Check if the response is valid
    if Graph_API_User_Profile_Image_response.status_code == 200:
        
        # Save the image to a file
        with open("profile_image.jpg", "wb") as f:
            f.write(Graph_API_User_Profile_Image_response.content)

        # Step 2: Upload to Imgur
        headers_imgur = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}

        retries = 5  # number of retries
        backoff = 2  # start with 2 seconds
        for attempt in range(retries):
            with open("profile_image.jpg", "rb") as img:
                files = {'image': img}
                upload = requests.post("https://api.imgur.com/3/upload", headers=headers_imgur, files=files)
            
            if upload.status_code == 200:
                return upload.json()['data']['link']
            elif upload.status_code == 429:
                print(f"Rate limit hit (attempt {attempt + 1}), retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2  # exponential backoff
            else:
                print(f"Upload failed with {upload.status_code}: {upload.text}")
                break  # break for non-rate-limit errors
        else:
            print("Imgur upload ultimately failed after retries.")
            return None
    else:
        print("Failed to download profile image:", Graph_API_User_Profile_Image_response.status_code)
        print(Graph_API_User_Profile_Image_response.text)

# Get User Profile Image
UserProfileImage = get_user_profile_image()

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
    return "🚀 App is live and running!"

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

        return jsonify(log_entries[-20:])  # Last 20 entries
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)

