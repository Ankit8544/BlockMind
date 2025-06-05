import requests
import pandas as pd
import json
from datetime import datetime
import pytz
import time
from dotenv import load_dotenv
import os
import re
from user_agents import parse as parse_ua
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

# Get Coin IDs from CoinsList Collection using Coin Name to match with UserPortfolio Collection
def get_coin_ids():
    if client:
        try:
            # Access the UserPortfolio collection
            CryptoCoinsdb = client['CryptoCoins']
            UserPortfolioCollection = CryptoCoinsdb['UserPortfolio']
            if UserPortfolioCollection is not None:

                # Retrieve all documents from the collection
                data = []
                for doc in UserPortfolioCollection.find():
                    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                    data.append(doc)
                
                if not data:
                    return pd.DataFrame()  # Return empty DataFrame if no data

                # Convert list of dictionaries to DataFrame
                df = pd.DataFrame(data)

                # Ensure '_id' is treated as a string
                if '_id' in df.columns:
                    df['_id'] = df['_id'].astype(str)

                # Portfolio Coin Name and Coin Symbol
                assets = {
                    "Coin Name": df['coin_name'].unique().tolist(),
                    "Coin Symbol": df['coin_symbol'].unique().tolist(),
                }
                
                Coin_Names = [re.sub(r'\W+', ' ', name) for name in assets['Coin Name']]
                
                CryptoCoinsdb = client['CryptoCoins']
                CoinlistsCollection = CryptoCoinsdb['CoinsList']

                # Use $in to fetch all matching documents by coin name
                query = {"name": {"$in": Coin_Names}}
                cursor = CoinlistsCollection.find(query, {"name": 1, "id": 1, "_id": 0})  # Only fetch 'id' and 'name'

                coin_ids = [doc['id'] for doc in cursor]
                
                return coin_ids
            else:
                print("User Portfolio Collection is None. Cannot retrieve data.")
                return []
        except Exception as e:
            print(f"❌ Error retrieving user portfolio collection: {e}")
            return []
    else:
        print("MongoDB client is None. Cannot access user portfolio collection.")
        return []



