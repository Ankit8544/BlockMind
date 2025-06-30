import pandas as pd
import pytz
from dotenv import load_dotenv
import os
import requests
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
    print("Connecting to MongoDB...")
    uri = f"mongodb+srv://{MONGO_DB_USERNAME}:{MONGO_DB_PASSWORD}@cluster0.ou0xiys.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB connection error:", e)
        return None

# Connect to MongoDB
client = connect_to_mongo()

# Check if the client is connected
if client is None:
    print("Failed to connect to MongoDB. Exiting...")
    sys.exit(1)


# -------------------------- Accessing MongoDB Collections -------------------------- #

# Access Coins List DB Collection and return the collection
def CoinsList_Collection():
    if client:
        CryptoCoinsdb = client['CryptoCoins']
        CoinsListCollection = CryptoCoinsdb['CoinsList']
        return CoinsListCollection
    else:
        print("MongoDB client is None. Cannot access coins list collection.")
        return None

# Access User Portfolio Coins DB Collection and return the collection
def UserPortfolioCoin_Collection():
    if client:
        CryptoCoinsdb = client['CryptoCoins']
        UserPortfolioCollection = CryptoCoinsdb['UserPortfolio']
        return UserPortfolioCollection
    else:
        print("MongoDB client is None. Cannot access user portfolio collection.")
        return None
    
# Access User Metadata DB Collection and return the collection
def UserMetadata_Collection():
    if client:
        CryptoCoinsdb = client['CryptoCoins']
        UserMetadataCollection = CryptoCoinsdb['UserMetadata']
        return UserMetadataCollection
    else:
        print("MongoDB client is None. Cannot access user metadata collection.")
        return None

# Access Crypto Data DB Collection and return the collection
def CryptoData_Collection():
    if client:
        CryptoDataDB = client["CryptoCoins"]
        CryptoDataCollection = CryptoDataDB["CryptoAnalysis"]
        return CryptoDataCollection
    else:
        print("MongoDB client is None. Cannot access crypto data collection.")
        return None

# Access Price History DB Collection and return the collection
def PriceHistory_Collection():
    if client:
        PriceHistory_Collection = client["PriceHistory"]
        return PriceHistory_Collection
    else:
        print("MongoDB client is None. Cannot access price history collection.")
        return None

# -------------------------- Getting Data from MongoDB -------------------------- # 

# Function to get coin list from MongoDB
def CryptoCoinList_Data():
    try:
        if client:
            CryptoCoinsdb = client['CryptoCoins']
            CoinsListCollection = CryptoCoinsdb['CoinsList']
            if CoinsListCollection is not None:
                # Retrieve all documents from the collection and store them in a list
                CoinsList = []
                for doc in CoinsListCollection.find():
                    doc['_id'] = str(doc['_id'])
                    CoinsList.append(doc)
                return CoinsList
            else:
                send_status_message(Status_TELEGRAM_CHAT_ID, "Coins List Collection is None. Cannot retrieve data.")
                return {}
        else:
            send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB client is None. Cannot access coins list collection.")
            return {}
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error retrieving coins list collection: {e}")
        return {}

# Get User Portfolio Coins DB Collection Data in JSON format
def UserPortfolio_Data():
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
def UserMetadata_Data():
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
def CryptoCoins_Data():
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

# Get Hourly Market Data in JSON format
def Hourly_MarketChartData_Data():
    try:
        if client:
            HourlyMarketChartDatadb = client['Hourly_MarketChartData']

            # List to hold all DataFrames
            all_dataframes = []

            # Iterate through all collections
            for collection_name in HourlyMarketChartDatadb.list_collection_names():
                collection = HourlyMarketChartDatadb[collection_name]
                
                data = list(collection.find())
                if not data:
                    continue  # Skip empty collections

                df = pd.DataFrame(data)

                # Remove MongoDB default _id column
                if "_id" in df.columns:
                    df.drop(columns=["_id"], inplace=True)

                # Capitalize the first letter of each column name
                df.columns = [col[0].upper() + col[1:] if col else col for col in df.columns]

                all_dataframes.append(df)

            # Combine all DataFrames
            if all_dataframes:
                final_df = pd.concat(all_dataframes, ignore_index=True)
                return final_df.to_dict(orient="records")
            else:
                return []
        else:
            send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB client is None. Cannot access market chart data.")
            return []
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error retrieving market chart data: {e}")
        return []

# Get Yearly Market Data in JSON format
def Yearly_MarketChartData_Data():
    try:
        if client:
            YearlyMarketChartDatadb = client['Yearly_MarketChartData']

            # List to hold all DataFrames
            all_dataframes = []

            # Iterate through all collections
            for collection_name in YearlyMarketChartDatadb.list_collection_names():
                collection = YearlyMarketChartDatadb[collection_name]
                
                data = list(collection.find())
                if not data:
                    continue  # Skip empty collections

                df = pd.DataFrame(data)

                # Remove MongoDB default _id column
                if "_id" in df.columns:
                    df.drop(columns=["_id"], inplace=True)

                # Capitalize the first letter of each column name
                df.columns = [col[0].upper() + col[1:] if col else col for col in df.columns]

                all_dataframes.append(df)

            # Combine all DataFrames
            if all_dataframes:
                final_df = pd.concat(all_dataframes, ignore_index=True)
                return final_df.to_dict(orient="records")
            else:
                return []
        else:
            send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB client is None. Cannot access market chart data.")
            return []
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error retrieving market chart data: {e}")
        return []

# Get Cabdlestick Data in JSON format
def CandlestickData_Data():
    try:
        if client:
            CandlestickDatadb = client['CandlestickData']

            # List to hold all DataFrames
            all_dataframes = []

            # Iterate through all collections
            for collection_name in CandlestickDatadb.list_collection_names():
                collection = CandlestickDatadb[collection_name]
                
                data = list(collection.find())
                if not data:
                    continue  # Skip empty collections

                df = pd.DataFrame(data)

                # Remove MongoDB default _id column
                if "_id" in df.columns:
                    df.drop(columns=["_id"], inplace=True)

                # Capitalize the first letter of each column name
                df.columns = [col[0].upper() + col[1:] if col else col for col in df.columns]

                all_dataframes.append(df)

            # Combine all DataFrames
            if all_dataframes:
                final_df = pd.concat(all_dataframes, ignore_index=True)
                return final_df.to_dict(orient="records")
            else:
                return []
        else:
            send_status_message(Status_TELEGRAM_CHAT_ID, "MongoDB client is None. Cannot access market chart data.")
            return []
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error retrieving market chart data: {e}")
        return []


# -------------------------- Processing Data Before inserting to MongoDB -------------------------- #


# Fetch and update all coins list in MongoDB
def fetch_and_store_all_coin_ids():
    url = "https://api.coingecko.com/api/v3/coins/list"

    try:
        response = requests.get(url)
        response.raise_for_status()
        coins_data = response.json()

        if not coins_data:
            print("No coins data received from CoinGecko.")
            return

        collection = CoinsList_Collection()
        if collection is not None:
            # Clear existing data
            existing_count = collection.count_documents({})
            if existing_count > 0:
                collection.delete_many({})
                print(f"Deleted {existing_count} existing documents from 'CoinsList' collection.")

            # Insert new data
            collection.insert_many(coins_data)
            print(f"Inserted {len(coins_data)} new coin documents into MongoDB.")
        else:
            print("Collection not accessible.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching coins list from CoinGecko: {e}")

# Get Coin IDs based on Portfolio Assets
def get_coin_ids():
    user_df = pd.DataFrame(UserPortfolio_Data())
    crypto_list_df = pd.DataFrame(CryptoCoinList_Data())

    # Unique coin names and symbols from user portfolio
    coin_names = user_df['coin_name'].unique().tolist()
    coin_symbols = user_df['coin_symbol'].unique().tolist()

    coin_ids = []

    # Match symbol and name to find the correct ID from crypto list
    for symbol, name in zip(coin_symbols, coin_names):
        match = crypto_list_df[
            (crypto_list_df['symbol'] == symbol) & 
            (crypto_list_df['name'] == name)
        ]
        if not match.empty:
            coin_ids.append(match['id'].iloc[0])
        else:
            coin_ids.append(None)  # Or handle differently

    return coin_ids

# Insert the Newly Analyzed CryptoData 
def refersh_analyzed_data(df):
    try:
        if client:
            CryptoDataDB = client["CryptoCoins"]
            CryptoDataCollection = CryptoDataDB["Analyzed_CryptoCurrency_Data"]

            # Replace NaN with None for MongoDB compatibility
            df = df.replace({np.nan: None})
            records = df.to_dict(orient='records')

            if CryptoDataCollection.count_documents({}) > 0:
                print(Status_TELEGRAM_CHAT_ID, "🗑️ Old Crypto Data found in 'CryptoAnalysis' Collection.So We are going to Delete it.")
                CryptoDataCollection.delete_many({})
                
            print(Status_TELEGRAM_CHAT_ID, "📤 Inserting New Analyzed Crypto Data into 'CryptoAnalysis' collection.")
            CryptoDataCollection.insert_many(records)
            print(Status_TELEGRAM_CHAT_ID, "✅ MongoDB 'CryptoAnalysis' collection uploaded successfully.")

    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error while uploading to MongoDB: {e}")



# Function to validate crypto symbol and name
def is_valid_crypto_symbol(symbol, coin_name=None):
    if not symbol or not isinstance(symbol, str):
        return "invalid_input"

    symbol = symbol.lower().strip()
    coin_name = coin_name.lower().strip() if coin_name and isinstance(coin_name, str) else None

    try:
        CoinsList = CryptoCoinList_Data()

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

# Function to validate MongoDB payload
def validate_crypto_payload(cleaned_data):
    """
    Ensures all required keys are present and not null/blank.
    """
    required_fields = ["user_mail", "coin_name", "coin_symbol", "purchase_date"]
    missing_fields = []
    blank_fields = []

    for field in required_fields:
        if field not in cleaned_data:
            missing_fields.append(field)
        elif str(cleaned_data[field]).strip() == "":
            blank_fields.append(field)

    if missing_fields or blank_fields:
        errors = []
        if missing_fields:
            errors.append(f"Missing fields: {', '.join(missing_fields)}")
        if blank_fields:
            errors.append(f"Blank fields: {', '.join(blank_fields)}")
        return False, " | ".join(errors)

    return True, "Valid"

# Function to check if user's coin data already exists
def is_user_portfolio_exist(user_mail, coin_name):
    try:
        collection = UserPortfolioCoin_Collection()

        query = {
            "user_mail": {"$regex": f"^{user_mail.strip()}$", "$options": "i"},
            "coin_name": {"$regex": f"^{coin_name.strip()}$", "$options": "i"}
        }

        result = collection.find_one(query)
        if result:
            return {
                "success": True,
                "message": "✅ This coin already exists in the user's portfolio.",
                "status_code": 200
            }
        else:
            return {
                "success": False,
                "message": "🔍 No duplicate coin found for this user.",
                "status_code": 200
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Error while checking existing data: {str(e)}",
            "status_code": 500
        }




def refresh_hourly_market_chart_data(df, crypto_id):
    try:
        if client:
            db = client["Hourly_MarketChartData"]
            collection_name = crypto_id.lower()

            if collection_name in db.list_collection_names():
                db.drop_collection(collection_name)

            # Add the coin ID as a column
            df["coin_id"] = crypto_id
            
            df = df.replace({np.nan: None})
            records = df.to_dict(orient="records")

            db[collection_name].insert_many(records)
            print(f"✅ Hourly market chart for '{crypto_id}' inserted successfully.")
            #send_status_message(Status_TELEGRAM_CHAT_ID, f"✅ Market Chart Data for '{crypto_id}' inserted successfully.")
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error inserting hourly market chart data for '{crypto_id}': {e}")
    return True

def refresh_yearly_market_chart_data_with_all_indecators(df, crypto_id):
    try:
        if client:
            db = client["Yearly_MarketChartData"]
            collection_name = crypto_id.lower()

            if collection_name in db.list_collection_names():
                db.drop_collection(collection_name)

            # Add the coin ID as a column
            df["coin_id"] = crypto_id
            
            df = df.replace({np.nan: None})
            records = df.to_dict(orient="records")

            db[collection_name].insert_many(records)
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error inserting hourly market chart data for '{crypto_id}': {e}")
    return True

def refresh_ohlc_data(df, crypto_id):
    try:
        if client:
            db = client["CandlestickData"]
            collection_name = crypto_id.lower()

            if collection_name in db.list_collection_names():
                db.drop_collection(collection_name)
                
            # Add the coin ID as a column
            df["coin_id"] = crypto_id

            df = df.replace({np.nan: None})
            records = df.to_dict(orient="records")
            
            db[collection_name].insert_many(records)
            print(f"✅ Candlestick Data for '{crypto_id}' inserted successfully.")
            #send_status_message(Status_TELEGRAM_CHAT_ID, f"✅ Candlestick Data for '{crypto_id}' inserted successfully.")
    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error inserting OHLC data for '{crypto_id}': {e}")

