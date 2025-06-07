from dotenv import load_dotenv
import requests
import os
import pandas as pd
import time
import concurrent.futures
import threading

# Load environment variables
load_dotenv()

# Crypto API URL and meme category Credentials
COINGECKO_API_URL = os.getenv("COINGECKO_API_URL")

# Shared lock for managing wait time globally
lock = threading.Lock()
next_available_time = time.time()

# Function to fetch coin data from CoinGecko API
def fetch_coin_data(coin_id):
    global next_available_time
    url = f"{COINGECKO_API_URL}/coins/{coin_id}"
    headers = {"Accept": "application/json"}

    max_retries = 5
    wait_time = 3.0

    for attempt in range(max_retries):
        with lock:
            current_time = time.time()
            if current_time < next_available_time:
                time.sleep(next_available_time - current_time)
            next_available_time = time.time() + wait_time

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                wait_time *= 2
                continue
            response.raise_for_status()
            data = response.json()

            # Extract relevant market data
            market_data = data.get("market_data", {})
            return {
                "Coin ID": data.get("id"),
                "Symbol": data.get("symbol"),
                "Coin Name": data.get("name"),
                "Image URL": data.get("image", {}).get("large"),
                "Current Price": market_data.get("current_price", {}).get("usd"),
                "Market Cap Rank": data.get("market_cap_rank"),
                "Market Cap": market_data.get("market_cap", {}).get("usd"),
                "Fully Diluted Valuation": market_data.get("fully_diluted_valuation", {}).get("usd"),  # ✅ NEW
                "Total Volume": market_data.get("total_volume", {}).get("usd"),
                "24h High Price": market_data.get("high_24h", {}).get("usd"),
                "24h Low Price": market_data.get("low_24h", {}).get("usd"),
                "24h Price Change": market_data.get("price_change_24h"),
                "24h Price Change Percentage (%)": market_data.get("price_change_percentage_24h"),
                "24h Market Cap Change": market_data.get("market_cap_change_24h"),  # ✅ NEW
                "24h Market Cap Change Percentage (%)": market_data.get("market_cap_change_percentage_24h"),  # ✅ NEW
                "Circulating Supply": market_data.get("circulating_supply"),  # ✅ NEW
                "Total Supply": market_data.get("total_supply"),  # ✅ NEW
                "Max Supply": market_data.get("max_supply"),  # ✅ NEW
                "All-Time High Price": market_data.get("ath", {}).get("usd"),
                "All-Time High Change Percentage (%)": market_data.get("ath_change_percentage", {}).get("usd"),
                "All-Time High Date": market_data.get("ath_date", {}).get("usd"),
                "All-Time Low Price": market_data.get("atl", {}).get("usd"),
                "All-Time Low Change Percentage (%)": market_data.get("atl_change_percentage", {}).get("usd"),
                "All-Time Low Date": market_data.get("atl_date", {}).get("usd"),
                "Last Updated": data.get("last_updated")
            }

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data for {coin_id}: {e}")
            time.sleep(wait_time)

    return None  # If all retries fail

# Fetch all coins using ThreadPool
def get_specific_coin_data(coin_ids):
    
    print(f"No. of all the coins: {len(coin_ids)}")
    
    all_data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(fetch_coin_data, coin_ids))

    # Filter out None responses
    filtered_results = [res for res in results if res is not None]

    df = pd.DataFrame(filtered_results)

    # ROI Calculation
    df["Return on Investment"] = ((df["Current Price"] - df["All-Time Low Price"]) / df["All-Time Low Price"]) * 100

    print(f"✅ Successfully fetched {len(filtered_results)} CryptoCoins Data from Coingecko API.")
    return df

