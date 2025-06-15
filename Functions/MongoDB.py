import pandas as pd
import pytz
from dotenv import load_dotenv
import os
import re
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import numpy as np

# Load environment variables
load_dotenv()

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

# Get Coin IDs from CoinsList Collection using Coin Name to match with UserPortfolio Collection
def get_coin_ids():
    print("🔍 Checking MongoDB client connection...")
    if client:
        try:
            CryptoCoinsdb = client['CryptoCoins']
            UserPortfolioCollection = CryptoCoinsdb['UserPortfolio']

            if UserPortfolioCollection is not None:
                print("📥 Fetching documents from 'UserPortfolio' collection...")
                data = []
                for doc in UserPortfolioCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    data.append(doc)

                print(f"📊 Total documents fetched: {len(data)}")

                if not data:
                    print("⚠️ No user portfolio data found.")
                    return pd.DataFrame()

                df = pd.DataFrame(data)
                print(f"✅ DataFrame shape: {df.shape}")

                if '_id' in df.columns:
                    df['_id'] = df['_id'].astype(str)

                coin_names_raw = df['coin_name'].unique().tolist()
                print(f"🪙 Unique Coin Names (raw): {coin_names_raw}")

                # Clean names (remove special characters, extra spaces)
                Coin_Names = [re.sub(r'\W+', ' ', name).strip() for name in coin_names_raw]
                print(f"🧼 Cleaned Coin Names: {Coin_Names}")

                CoinlistsCollection = CryptoCoinsdb['CoinsList']

                # Use case-insensitive regex matching for each coin name
                query = {
                    "$or": [{"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}} for name in Coin_Names]
                }

                cursor = CoinlistsCollection.find(query, {"name": 1, "id": 1, "_id": 0})
                result = list(cursor)

                coin_ids = [doc['id'] for doc in result]
                matched_names = [doc['name'] for doc in result]

                print(f"✅ Matched Coin Names: {matched_names}")
                print(f"🆔 Total Coin IDs fetched: {len(coin_ids)}")

                unmatched = {
                    name for name in Coin_Names
                    if name.strip().lower() not in {m.strip().lower() for m in matched_names}
                }
                if unmatched:
                    print(f"❌ Unmatched Coin Names: {unmatched}")
                else:
                    print("✅ All coin names matched successfully.")

                return coin_ids
            else:
                print("❌ 'UserPortfolio' collection not found.")
                return []
        except Exception as e:
            print(f"🚨 Error: {e}")
            return []
    else:
        print("❌ MongoDB client is None.")
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
                print("🗑️ Old data found in 'CryptoAnalysis'. Deleting...")
                CryptoDataCollection.delete_many({})
                
            print("📤 Inserting new data into 'CryptoAnalysis' collection...")
            CryptoDataCollection.insert_many(records)
            print("✅ MongoDB upload completed.")

    except Exception as e:
        print(f"❌ Error while uploading to MongoDB: {e}")

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

# Get User Portfolio Based Crypto Data Collection Data in JSON format
def get_crypto_data():
    try:
        if client:
            CryptoDataDB = client["CryptoCoins"]
            CryptoDataCollection = CryptoDataDB["CryptoAnalysis"]
            
            if CryptoDataCollection is not None:
                print("CryptoData Collection is connected successfully.")
                # Retrieve all documents from the collection and store them in a dict
                CryptoData = []
                for doc in CryptoDataCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    CryptoData.append(doc)
                print(f"Retrieved {len(CryptoData)} assets from CryptoData Collection.")
                return CryptoData
            else:
                print("CryptoData Collection is None. Cannot retrieve data.")
                return {}
        else:
            print("MongoDB client is None. Cannot access user portfolio collection.")
            return {}
    except Exception as e:
        print(f"❌ Error retrieving user portfolio collection: {e}")
        return {}

