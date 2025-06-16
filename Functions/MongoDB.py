import pandas as pd
import pytz
from dotenv import load_dotenv
import os
import re
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import numpy as np
import sys
from Functions.BlockMindsStatusBot import send_status_message

# Load environment variables
load_dotenv()

# Load API credentials
Status_TELEGRAM_CHAT_ID = os.getenv("Status_TELEGRAM_CHAT_ID")

# MongoDB Credentials
MONGO_DB_USERNAME = os.getenv("MONGO_DB_USERNAME")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")

# Set the timezone to UTC+5:30
ist = pytz.timezone('Asia/Kolkata')


# Check if environment variables are set
if not MONGO_DB_USERNAME or not MONGO_DB_PASSWORD:
    raise ValueError("MongoDB credentials are not set in the environment variables.")

# MongoDB connection setup
def connect_to_mongo():
    send_status_message(Status_TELEGRAM_CHAT_ID, "Connecting to MongoDB...")
    uri = f"mongodb+srv://{MONGO_DB_USERNAME}:{MONGO_DB_PASSWORD}@cluster0.ou0xiys.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        send_status_message(Status_TELEGRAM_CHAT_ID, "Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB connection error:", e)
        return None

# Connect to MongoDB
client = connect_to_mongo()

# Get Coin IDs from CoinsList Collection using Coin Name to match with UserPortfolio Collection
def get_coin_ids():
    if client:
        try:
            CryptoCoinsdb = client['CryptoCoins']
            UserPortfolioCollection = CryptoCoinsdb['UserPortfolio']

            if UserPortfolioCollection is not None:
                data = []
                for doc in UserPortfolioCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    data.append(doc)

                if not data:
                    return pd.DataFrame()

                df = pd.DataFrame(data)

                if '_id' in df.columns:
                    df['_id'] = df['_id'].astype(str)

                coin_names_raw = df['coin_name'].unique().tolist()

                # Clean names (remove special characters, extra spaces)
                Coin_Names = [re.sub(r'\W+', ' ', name).strip() for name in coin_names_raw]

                CoinlistsCollection = CryptoCoinsdb['CoinsList']

                # Use case-insensitive regex matching for each coin name
                query = {
                    "$or": [{"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}} for name in Coin_Names]
                }

                cursor = CoinlistsCollection.find(query, {"name": 1, "id": 1, "_id": 0})
                result = list(cursor)

                coin_ids = [doc['id'] for doc in result]
                matched_names = [doc['name'] for doc in result]

                unmatched = {
                    name for name in Coin_Names
                    if name.strip().lower() not in {m.strip().lower() for m in matched_names}
                }
                if unmatched:
                    send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Unmatched Coin Names: {unmatched}")

                return coin_ids
            else:
                send_status_message(Status_TELEGRAM_CHAT_ID, "❌ 'UserPortfolio' collection not found.")
                return []
        except Exception as e:
            send_status_message(Status_TELEGRAM_CHAT_ID, f"🚨 Error: {e}")
            return []
    else:
        send_status_message(Status_TELEGRAM_CHAT_ID, "❌ MongoDB client is None.")
        return []

# Insert the Newly Analyzed CryptoData 
def refersh_cryptodata(df):
    try:
        if client:
            CryptoDataDB = client["CryptoCoins"]
            CryptoDataCollection = CryptoDataDB["CryptoAnalysis"]

            # Replace NaN with None for MongoDB compatibility
            df = df.replace({np.nan: None})
            records = df.to_dict(orient='records')

            if CryptoDataCollection.count_documents({}) > 0:
                send_status_message(Status_TELEGRAM_CHAT_ID, "🗑️ Old Crypto Data found in 'CryptoAnalysis' Collection.So We are going to Delete it.")
                CryptoDataCollection.delete_many({})
                
            send_status_message(Status_TELEGRAM_CHAT_ID, "📤 Inserting New Analyzed Crypto Data into 'CryptoAnalysis' collection.")
            CryptoDataCollection.insert_many(records)
            send_status_message(Status_TELEGRAM_CHAT_ID, "✅ MongoDB 'CryptoAnalysis' collection uploaded successfully.")

    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error while uploading to MongoDB: {e}")

# Get User Portfolio Coins DB Collection Data in JSON format
def get_user_portfolio_data():
    try:
        if client:
            CryptoCoinsdb = client['CryptoCoins']
            UserPortfolioCollection = CryptoCoinsdb['UserPortfolio']
            if UserPortfolioCollection is not None:
                # Retrieve all documents from the collection and store them in a dict
                Assets = []
                for doc in UserPortfolioCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    Assets.append(doc)
                return Assets
            else:
                send_status_message(Status_TELEGRAM_CHAT_ID, "User Portfolio Collection is None. Cannot retrieve data.")
                return {}
        else:
            send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB client is None. Cannot access user portfolio collection.")
            return {}
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error retrieving user portfolio collection: {e}")
        return {}

# Get User Meta Data in JSON format
def get_user_meta_data():
    try:
        if client:
            CryptoCoinsdb = client['CryptoCoins']
            UserMetaCollection = CryptoCoinsdb['UserMetadata']
            if UserMetaCollection is not None:
                # Retrieve all documents from the collection and store them in a dict
                Metadata = []
                for doc in UserMetaCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    Metadata.append(doc)
                return Metadata
            else:
                send_status_message(Status_TELEGRAM_CHAT_ID, "User Meta Collection is None. Cannot retrieve data.")
                return {}
        else:
            send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB client is None. Cannot access user meta collection.")
            return {}
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error retrieving user meta collection: {e}")
        return {}

# Get User Portfolio Based Crypto Data Collection Data in JSON format
def get_crypto_data():
    try:
        if client:
            CryptoDataDB = client["CryptoCoins"]
            CryptoDataCollection = CryptoDataDB["CryptoAnalysis"]
            
            if CryptoDataCollection is not None:
                # Retrieve all documents from the collection and store them in a dict
                CryptoData = []
                for doc in CryptoDataCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    CryptoData.append(doc)
                return CryptoData
            else:
                send_status_message(Status_TELEGRAM_CHAT_ID, "CryptoData Collection is None. Cannot retrieve data.")
                return {}
        else:
            send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB client is None. Cannot access user portfolio collection.")
            return {}
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error retrieving user portfolio collection: {e}")
        return {}

