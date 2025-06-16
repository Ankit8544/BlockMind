from dotenv import load_dotenv
import requests
import os
import pandas as pd
import time
import concurrent.futures
import threading
from Functions.BlockMindsStatusBot import send_status_message 

# Load environment variables
load_dotenv()

COINGECKO_API_URL = os.getenv("COINGECKO_API_URL")

# Status TELEGRAM CHAT I'D
Status_TELEGRAM_CHAT_ID = os.getenv("Status_TELEGRAM_CHAT_ID")

# Lock for shared timing (if needed)
lock = threading.Lock()
next_available_time = time.time()

# Parameters
CHUNK_SIZE = 4
WAIT_BETWEEN_CHUNKS = 50  # based on observed reset time
THREADS_PER_CHUNK = 2
MAX_RETRIES = 5


def fetch_coin_data(coin_id):
    global next_available_time
    url = f"{COINGECKO_API_URL}/coins/{coin_id}"
    headers = {
        "Accept": "application/json"
    }

    wait_time = 1.0  # initial wait time for exponential backoff

    for attempt in range(MAX_RETRIES):
        with lock:
            now = time.time()
            if now < next_available_time:
                time.sleep(next_available_time - now)
            next_available_time = time.time() + 1.0  # pacing between threads

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 429:
                rate_limit_hit_time = time.time()

                while True:
                    time.sleep(1)
                    retry_response = requests.get(url, headers=headers)
                    if retry_response.status_code != 429:
                        actual_wait = time.time() - rate_limit_hit_time
                        response = retry_response
                        break

            response.raise_for_status()
            data = response.json()

            market_data = data.get("market_data", {})
            return {
                "Coin ID": data.get("id"),
                "Symbol": data.get("symbol"),
                "Coin Name": data.get("name"),
                "Image URL": data.get("image", {}).get("large"),
                "Current Price": market_data.get("current_price", {}).get("usd"),
                "Market Cap Rank": data.get("market_cap_rank"),
                "Market Cap": market_data.get("market_cap", {}).get("usd"),
                "Fully Diluted Valuation": market_data.get("fully_diluted_valuation", {}).get("usd"),
                "Total Volume": market_data.get("total_volume", {}).get("usd"),
                "24h High Price": market_data.get("high_24h", {}).get("usd"),
                "24h Low Price": market_data.get("low_24h", {}).get("usd"),
                "24h Price Change": market_data.get("price_change_24h"),
                "24h Price Change Percentage (%)": market_data.get("price_change_percentage_24h"),
                "24h Market Cap Change": market_data.get("market_cap_change_24h"),
                "24h Market Cap Change Percentage (%)": market_data.get("market_cap_change_percentage_24h"),
                "Circulating Supply": market_data.get("circulating_supply"),
                "Total Supply": market_data.get("total_supply"),
                "Max Supply": market_data.get("max_supply"),
                "All-Time High Price": market_data.get("ath", {}).get("usd"),
                "All-Time High Change Percentage (%)": market_data.get("ath_change_percentage", {}).get("usd"),
                "All-Time High Date": market_data.get("ath_date", {}).get("usd"),
                "All-Time Low Price": market_data.get("atl", {}).get("usd"),
                "All-Time Low Change Percentage (%)": market_data.get("atl_change_percentage", {}).get("usd"),
                "All-Time Low Date": market_data.get("atl_date", {}).get("usd"),
                "Last Updated": data.get("last_updated")
            }

        except requests.exceptions.RequestException as e:
            send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error fetching data for {coin_id}: {e}")
            time.sleep(wait_time)
            wait_time *= 1  # exponential backoff

    send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Final failure: Could not fetch data for {coin_id} after {MAX_RETRIES} attempts.")
    return None

def chunkify(lst, size):
    return [lst[i:i + size] for i in range(0, len(lst), size)]

def get_specific_coin_data(coin_ids):
    all_data = []
    chunks = chunkify(coin_ids, CHUNK_SIZE)

    for i, chunk in enumerate(chunks, 1):

        with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS_PER_CHUNK) as executor:
            results = list(executor.map(fetch_coin_data, chunk))

        for coin_id, result in zip(chunk, results):
            if result:
                all_data.append(result)
            else:
                print(f"❌ Failed to fetch: {coin_id}")

        if i < len(chunks):
            time.sleep(WAIT_BETWEEN_CHUNKS)

    df = pd.DataFrame(all_data)
    df["Return on Investment"] = ((df["Current Price"] - df["All-Time Low Price"]) / df["All-Time Low Price"]) * 100

    return df

