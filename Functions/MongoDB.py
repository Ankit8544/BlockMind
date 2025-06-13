import pandas as pd
import pytz
from dotenv import load_dotenv
import os
import re
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

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


