from dotenv import load_dotenv
import requests
import os
import pandas as pd
import pytz
from Functions.MongoDB import connect_to_mongo  # Import the connect_to_mongo function

# Timezone
ist = pytz.timezone("Asia/Kolkata")

# Load environment variables
load_dotenv()

COINGECKO_API_URL = os.getenv("COINGECKO_API_URL")

# Status TELEGRAM CHAT ID
Status_TELEGRAM_CHAT_ID = os.getenv("Status_TELEGRAM_CHAT_ID")

# Connect to MongoDB using the function from MongoDB.py
client = connect_to_mongo()  # Use the connect_to_mongo function

# Function to fetch and store data
def fetch_and_store_data(coin_id):
    try:
        print(f"Fetching data for coin: {coin_id}")
        
        # MongoDB collections
        yearly_market_chart_collection = client['Yearly_MarketChartData'][coin_id.lower()]
        hourly_market_chart_collection = client['Hourly_MarketChartData'][coin_id.lower()]
        yearly_candlestick_data_collection = client['Yearly_CandlestickData'][coin_id.lower()]
        hourly_candlestick_data_collection = client['Hourly_CandlestickData'][coin_id.lower()]
        
        # --- Fetch Yearly MarketChart Data ---
        url_yearly = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params_yearly = {"vs_currency": "usd", "days": "365"}  # 365 days for yearly data
        response_yearly = requests.get(url_yearly, params=params_yearly)

        if response_yearly.status_code == 200:
            data_yearly = response_yearly.json()
            df_yearly = pd.DataFrame(data_yearly["prices"], columns=["timestamp", "price"])
            df_yearly["timestamp"] = pd.to_datetime(df_yearly["timestamp"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
            df_yearly["timestamp"] = df_yearly["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")  # Format the timestamp

            # Insert Yearly MarketChart Data into MongoDB
            if yearly_market_chart_collection is not None:  # Check if the collection exists
                existing_data_yearly = yearly_market_chart_collection.find({"coin_id": coin_id})
                
                # Use len(list(cursor)) to count documents
                if len(list(existing_data_yearly)) == 0:
                    df_yearly["coin_id"] = coin_id
                    records_yearly = df_yearly.to_dict(orient="records")
                    yearly_market_chart_collection.insert_many(records_yearly)
                    print(f"✅ Yearly MarketChart Data for '{coin_id}' inserted successfully.")
                else:
                    print(f"⚠️ Yearly MarketChart Data for '{coin_id}' already exists.")
        else:
            print(f"❌ Failed to fetch Yearly MarketChart data for '{coin_id}' with status code: {response_yearly.status_code}")

        # --- Fetch Hourly MarketChart Data ---
        url_hourly = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params_hourly = {"vs_currency": "usd", "days": "1"}  # 1 day for hourly data
        response_hourly = requests.get(url_hourly, params=params_hourly)

        if response_hourly.status_code == 200:
            data_hourly = response_hourly.json()
            df_hourly = pd.DataFrame(data_hourly["prices"], columns=["timestamp", "price"])
            df_hourly["timestamp"] = pd.to_datetime(df_hourly["timestamp"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
            
            latest_time = df_hourly["timestamp"].max()
            cutoff_time = latest_time - pd.Timedelta(hours=24)
            df_hourly = df_hourly[df_hourly["timestamp"] > cutoff_time]
            df_hourly["timestamp"] = df_hourly["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")  # Format the timestamp

            # Insert Hourly MarketChart Data into MongoDB
            if hourly_market_chart_collection is not None:  # Check if the collection exists
                existing_data_hourly = hourly_market_chart_collection.find({"coin_id": coin_id})
                
                # Use len(list(cursor)) to count documents
                if len(list(existing_data_hourly)) == 0:
                    df_hourly["coin_id"] = coin_id
                    records_hourly = df_hourly.to_dict(orient="records")
                    hourly_market_chart_collection.insert_many(records_hourly)
                    print(f"✅ Hourly MarketChart Data for '{coin_id}' inserted successfully.")
                else:
                    print(f"⚠️ Hourly MarketChart Data for '{coin_id}' already exists.")
        else:
            print(f"❌ Failed to fetch Hourly MarketChart data for '{coin_id}' with status code: {response_hourly.status_code}")

        # --- Fetch Yearly OHLC Data ---
        url_yearly_ohlc = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params_yearly_ohlc = {"vs_currency": "usd", "days": "365"}  # 365 days for yearly OHLC data
        response_yearly_ohlc = requests.get(url_yearly_ohlc, params=params_yearly_ohlc)

        if response_yearly_ohlc.status_code == 200:
            data_yearly_ohlc = response_yearly_ohlc.json()
            df_yearly_ohlc = pd.DataFrame(data_yearly_ohlc, columns=["timestamp", "open", "high", "low", "close"])
            df_yearly_ohlc["timestamp"] = pd.to_datetime(df_yearly_ohlc["timestamp"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
            df_yearly_ohlc["timestamp"] = df_yearly_ohlc["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")  # Format the timestamp
            
            # Insert Yearly OHLC Data into MongoDB
            if yearly_candlestick_data_collection is not None:  # Check if the collection exists
                existing_data_yearly_ohlc = yearly_candlestick_data_collection.find({"coin_id": coin_id})
                
                # Use len(list(cursor)) to count documents
                if len(list(existing_data_yearly_ohlc)) == 0:
                    df_yearly_ohlc["coin_id"] = coin_id
                    records_yearly_ohlc = df_yearly_ohlc.to_dict(orient="records")
                    yearly_candlestick_data_collection.insert_many(records_yearly_ohlc)
                    print(f"✅ Yearly OHLC Data for '{coin_id}' inserted successfully.")
                else:
                    print(f"⚠️ Yearly OHLC Data for '{coin_id}' already exists.")
        else:
            print(f"❌ Failed to fetch Yearly OHLC data for '{coin_id}' with status code: {response_yearly_ohlc.status_code}")

        # --- Fetch Hourly OHLC Data ---
        url_hourly_ohlc = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params_hourly_ohlc = {"vs_currency": "usd", "days": "1"}  # 1 day for hourly OHLC data
        response_hourly_ohlc = requests.get(url_hourly_ohlc, params=params_hourly_ohlc)

        if response_hourly_ohlc.status_code == 200:
            data_hourly_ohlc = response_hourly_ohlc.json()
            df_hourly_ohlc = pd.DataFrame(data_hourly_ohlc, columns=["timestamp", "open", "high", "low", "close"])
            df_hourly_ohlc["timestamp"] = pd.to_datetime(df_hourly_ohlc["timestamp"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
            df_hourly_ohlc["timestamp"] = df_hourly_ohlc["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")  # Format the timestamp
            
            # Insert Hourly OHLC Data into MongoDB
            if hourly_candlestick_data_collection is not None:  # Check if the collection exists
                existing_data_hourly_ohlc = hourly_candlestick_data_collection.find({"coin_id": coin_id})
                
                # Use len(list(cursor)) to count documents
                if len(list(existing_data_hourly_ohlc)) == 0:
                    df_hourly_ohlc["coin_id"] = coin_id
                    records_hourly_ohlc = df_hourly_ohlc.to_dict(orient="records")
                    hourly_candlestick_data_collection.insert_many(records_hourly_ohlc)
                    print(f"✅ Hourly OHLC Data for '{coin_id}' inserted successfully.")
                else:
                    print(f"⚠️ Hourly OHLC Data for '{coin_id}' already exists.")
        else:
            print(f"❌ Failed to fetch Hourly OHLC data for '{coin_id}' with status code: {response_hourly_ohlc.status_code}")

    except Exception as e:
        print(f"⚠️ Error fetching or inserting data for '{coin_id}': {e}")

# Function for real-time updates
def real_time_update():
    # Corrected coin_id for XRP
    coin_id = "floki"
    fetch_and_store_data(coin_id)

# Trigger real-time update
real_time_update()