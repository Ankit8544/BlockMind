import pandas as pd
import numpy as np
import ta  # Technical Analysis Library
import requests
import os
import time
import tweepy
import praw
from textblob import TextBlob
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from cachetools import TTLCache
from Functions.Fetch_Data import get_specific_coin_data
from Functions.MongoDB import get_coin_ids
from Functions.BlockMindsStatusBot import send_status_message

pd.options.mode.chained_assignment = None

# CoinGecko API URL
COINGECKO_API_URL = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")

# Status TELEGRAM CHAT I'D
Status_TELEGRAM_CHAT_ID = os.getenv("Status_TELEGRAM_CHAT_ID")

# Twitter API credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Reddit API credentials
reddit = praw.Reddit(
    client_id = "XQaZSF7aFd169cXHuQs4uA",
    client_secret = "NCF7iHpFDgkSpwYOESMVRlcrHRx3_Q",
    user_agent = "meme-coin-sentiment"
)

# Initialize Twitter Client
twitter_client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

# Cache responses to avoid repeated API calls
cache = TTLCache(maxsize=500, ttl=900)  # Store 100 results for 5 minutes

# Fetched Crypto Data from CoinGecko using get_specific_coin_data function
def load_data():
    try:
        send_status_message(Status_TELEGRAM_CHAT_ID, "🔄 Loading Crypto Data from CoinGecko using User Portfolio Coin IDs.")
        
        # Coins you want to fetch data for
        coin_ids = get_coin_ids()  # Replace with your list
        
        if not coin_ids:
            raise ValueError("No coin IDs returned from get_coin_ids()")

        df = get_specific_coin_data(coin_ids=coin_ids)

        if df.empty:
            raise ValueError("No data returned from get_specific_coin_data")

        send_status_message(Status_TELEGRAM_CHAT_ID, f"✅ Based on User Portfolio, {df.shape[0]} CryptoCoins data loaded successfully from CoinGecko.")
        return df

    except Exception as e:
        print(f"❌ Error loading crypto analysis data: {e}")
        return pd.DataFrame()

# Function to calculate return multiple
def calculate_return_multiple(price_change):
    return_multiple = 1 + (price_change / 100)
    return return_multiple

# Contract Address
def get_contract_address(coin_id, symbol):
    # 1️⃣ Try CoinGecko API first
    coingecko_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    
    try:
        response = requests.get(coingecko_url)
        response.raise_for_status()
        data = response.json()
        
        platforms = data.get("platforms", {})

        # 🛑 If the coin has no platform, it's a native blockchain coin (e.g., Dogecoin)
        if not platforms:
            return "Native Coin (No Contract)"

        # ✅ Return Ethereum contract if available, otherwise return another platform
        return platforms.get("ethereum", next(iter(platforms.values()), "Unknown"))

    except requests.exceptions.RequestException:
        pass  # Ignore and try Dexscreener

    # 2️⃣ Try Dexscreener only for tokens
    dexscreener_url = f"https://api.dexscreener.com/latest/dex/search/?q={symbol}"
    
    try:
        response = requests.get(dexscreener_url)
        response.raise_for_status()
        data = response.json()
        
        if "pairs" in data and data["pairs"]:
            return data["pairs"][0].get("baseToken", {}).get("address", "Not Found")

    except requests.exceptions.RequestException:
        pass

    return "Not Found"

# Liquidity Data Fetching
# Exponential Backoff for handling rate limits
def fetch_with_retries(url, retries=7, base_delay=3):
    for attempt in range(retries):
        response = requests.get(url)
        if response.status_code == 429:
            wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)
            continue  # Retry the request
        response.raise_for_status()
        return response.json()
    return None  # Return None after max retries

# Fetch liquidity from DexScreener for tokens
def get_dex_liquidity(contract_address):
    if not contract_address or contract_address == "Native Coin (No Contract)":
        return None  # Skip if no contract address

    # Avoid calling API for unsupported formats (like Cosmos addresses)
    if not contract_address.startswith("0x"):  # DexScreener only supports Ethereum-style addresses
        return None

    if contract_address in cache:
        return cache[contract_address]  # Return cached result

    url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
    data = fetch_with_retries(url)

    if data and "pairs" in data and isinstance(data["pairs"], list) and len(data["pairs"]) > 0:
        liquidity = data["pairs"][0].get("liquidity", {}).get("usd", 0)
        cache[contract_address] = liquidity  # Cache the result
        time.sleep(random.uniform(1, 2))
        return liquidity

    return 0  # Default to 0 if no data found

# Fetch market volume from CoinGecko for native coins
def get_native_coin_liquidity(coin_id):
    if coin_id in cache:
        return cache[coin_id]  # Return cached result

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    data = fetch_with_retries(url)

    if data:
        liquidity = data.get("market_data", {}).get("total_volume", {}).get("usd", 0)
        cache[coin_id] = liquidity  # Cache the result

        # Sleep for 1-2 seconds before the next request
        time.sleep(random.uniform(1, 2))

        return liquidity

    return 0  # Default to 0 if no data found

# Determine which liquidity source to use
def get_liquidity(contract_address, coin_id):
    if not contract_address or contract_address == "Native Coin (No Contract)":
        return get_native_coin_liquidity(coin_id)  # Use CoinGecko for native coins
    return get_dex_liquidity(contract_address)  # Use DexScreener for tokens

# Function to get sentiment score & engagement metrics
def get_reddit_sentiment(query, limit=50):
    posts = reddit.subreddit("cryptocurrency+CryptoMarkets").search(query, limit=limit)

    sentiment_score = 0
    count = 0
    total_upvotes = 0
    total_comments = 0
    mention_count = 0

    for post in posts:
        analysis = TextBlob(post.title)
        sentiment_score += analysis.sentiment.polarity
        total_upvotes += post.score  # Upvotes
        total_comments += post.num_comments  # Comments
        mention_count += 1

        count += 1

    avg_sentiment = sentiment_score / count if count > 0 else 0
    avg_upvotes = total_upvotes / count if count > 0 else 0
    avg_comments = total_comments / count if count > 0 else 0

    return avg_sentiment, mention_count, avg_upvotes, avg_comments

# Full Analysis
def Analysis():
    
    # Load the data globaly 
    df = load_data()
    
    send_status_message(Status_TELEGRAM_CHAT_ID, "🔄 Start Analyzing the Crypto Data which fetched the Coingecko API")

    # Select the Coin ID column and convert it to a list
    crypto_Ids = df['Coin ID'].tolist()

    # Dictionary to store Sharpe Ratios and technical indicators for each Crypto_Id
    crypto_analysis_dict = {}

    for Crypto_Id in crypto_Ids:
        url = f"https://api.coingecko.com/api/v3/coins/{Crypto_Id}/market_chart"
        params = {'vs_currency': 'usd', 'days': '365', 'interval': 'daily'}

        data = None
        for attempt in range(10):  # Retry up to 10 times
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                break
            elif response.status_code == 429:
                time.sleep(60)
            else:
                print(f"Failed to fetch data for {Crypto_Id}: {response.status_code}")
                break

        if not data:
            print(f"Skipping {Crypto_Id} due to missing data.")
            continue

        try:
            # Convert to DataFrame
            prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
            prices['timestamp'] = pd.to_datetime(prices['timestamp'], unit='ms')
            prices.set_index('timestamp', inplace=True)
            
        except KeyError:
            print(f"Skipping {Crypto_Id} due to missing keys in data.")
            continue

        # Calculate daily returns
        prices['returns'] = prices['price'].pct_change()

        # Compute Sharpe Ratio
        risk_free_rate = 0.01
        mean_return = prices['returns'].mean()
        std_dev = prices['returns'].std()
        sharpe_ratio = (mean_return - risk_free_rate) / std_dev if std_dev != 0 else float('nan')

        # --------- Technical Analysis Indicators ---------
        # Moving Averages
        prices['SMA_50'] = prices['price'].rolling(window=50, min_periods=1).mean()
        prices['EMA_20'] = prices['price'].ewm(span=20, adjust=False).mean()

        # RSI
        rsi_indicator = ta.momentum.RSIIndicator(prices['price'], window=14, fillna=True)
        prices['RSI'] = rsi_indicator.rsi()

        # MACD
        macd = ta.trend.MACD(prices['price'], fillna=True)
        prices['MACD'] = macd.macd()
        prices['MACD_Signal'] = macd.macd_signal()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(prices['price'], window=20, fillna=True)
        prices['BB_High'] = bb.bollinger_hband()
        prices['BB_Low'] = bb.bollinger_lband()

        # Buy/Sell Signals based on RSI (Fixing None Values)
        prices['Buy_Signal'] = np.where(prices['RSI'] < 30, prices['price'], np.nan)
        prices['Sell_Signal'] = np.where(prices['RSI'] > 70, prices['price'], np.nan)

        # Fill missing Buy/Sell signals with NaN instead of None
        prices['Buy_Signal'] = prices['Buy_Signal'].fillna(np.nan)
        prices['Sell_Signal'] = prices['Sell_Signal'].fillna(np.nan)

        # Trend Projections
        prices['SMA_Projection'] = (prices['SMA_50'] + prices['price']) / 2
        prices['EMA_Projection'] = (prices['EMA_20'] + prices['price']) / 2
        rsi_adjustment_factor = (50 - prices['RSI']) / 100
        prices['RSI_Projection'] = prices['price'] * (1 + rsi_adjustment_factor)
        macd_adjustment_factor = abs(prices['MACD'] - prices['MACD_Signal']) / 10
        prices['MACD_Projection'] = prices['price'] * (1 + macd_adjustment_factor)
        prices['BB_Mid'] = (prices['BB_High'] + prices['BB_Low']) / 2
        prices['BB_Projection'] = (prices['BB_Mid'] + prices['price']) / 2

        # Final Predicted Price Calculation
        prices['Predicted_Price'] = prices[['SMA_Projection', 'EMA_Projection', 'RSI_Projection', 'MACD_Projection', 'BB_Projection']].mean(axis=1)

        # Store data in dictionary
        crypto_analysis_dict[Crypto_Id] = prices

    # --------- Update Main DataFrame ---------
    df['Sharpe Ratio'] = df['Coin ID'].map({
        k: v['returns'].mean() / v['returns'].std() if v['returns'].std() != 0 else float('nan')
        for k, v in crypto_analysis_dict.items()
    })
    
    df['Simple Moving Average Over 50 Days'] = df['Coin ID'].map({k: v['SMA_50'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    df['Exponential Moving Average Over 20 Days'] = df['Coin ID'].map({k: v['EMA_20'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    df['Relative Strength Index'] = df['Coin ID'].map({k: v['RSI'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    df['Moving Average Convergence Divergence'] = df['Coin ID'].map({k: v['MACD'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    df['Moving Average Convergence Divergence Signal'] = df['Coin ID'].map({k: v['MACD_Signal'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    df['Bollinger Bands High'] = df['Coin ID'].map({k: v['BB_High'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    df['Bollinger Bands Low'] = df['Coin ID'].map({k: v['BB_Low'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    df['Buy Signal'] = df['Coin ID'].map({k: v['Buy_Signal'].dropna().iloc[-1] if not v['Buy_Signal'].dropna().empty else np.nan for k, v in crypto_analysis_dict.items()})
    df['Sell Signal'] = df['Coin ID'].map({k: v['Sell_Signal'].dropna().iloc[-1] if not v['Sell_Signal'].dropna().empty else np.nan for k, v in crypto_analysis_dict.items()})
    df['Predicted Price'] = df['Coin ID'].map({k: v['Predicted_Price'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    df["Contract Address"] = df.apply(lambda row: get_contract_address(row["Coin ID"], row["Symbol"]), axis=1)
    df["Liquidity"] = df.apply(lambda row: get_liquidity(row["Contract Address"], row["Coin ID"]), axis=1)
    df[["Reddit Sentiment", "Reddit Mentions", "Avg Reddit Upvotes", "Avg Reddit Comments"]] = df["Coin Name"].apply(lambda x: pd.Series(get_reddit_sentiment(x)))
    
    # --------- Price Change Percentage Fix ---------
    df['7d Price Change Percentage (%)'] = df['Coin ID'].map(
        lambda coin_id: ((crypto_analysis_dict[coin_id]['price'].iloc[-1] - 
                          crypto_analysis_dict[coin_id]['price'].iloc[-8]) / 
                          crypto_analysis_dict[coin_id]['price'].iloc[-8]) * 100
        if coin_id in crypto_analysis_dict and len(crypto_analysis_dict[coin_id]) > 7 else np.nan
    )

    df['30d Price Change Percentage (%)'] = df['Coin ID'].map(
        lambda coin_id: ((crypto_analysis_dict[coin_id]['price'].iloc[-1] - 
                        crypto_analysis_dict[coin_id]['price'].iloc[-31]) / 
                        crypto_analysis_dict[coin_id]['price'].iloc[-31]) * 100
        if coin_id in crypto_analysis_dict and len(crypto_analysis_dict[coin_id]) > 30 else np.nan
    )

    df['1y Price Change Percentage (%)'] = df['Coin ID'].map(
        lambda coin_id: ((crypto_analysis_dict[coin_id]['price'].iloc[-1] - 
                        crypto_analysis_dict[coin_id]['price'].iloc[0]) / 
                        crypto_analysis_dict[coin_id]['price'].iloc[0]) * 100
        if coin_id in crypto_analysis_dict and len(crypto_analysis_dict[coin_id]) > 364 else np.nan
    )

    df = df.replace({np.nan: None})  # <-- CLEANING
    send_status_message(Status_TELEGRAM_CHAT_ID, "✅ All Analysis Completed Successfully.")
    return df

