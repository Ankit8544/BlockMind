import pandas as pd
import numpy as np
import ta  # Technical Analysis Library
import requests
import os
import time
import tweepy
import praw
from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from cachetools import TTLCache
from Functions.Fetch_Data import get_specific_coin_data
from Functions.MongoDB import get_coin_ids, UserPortfolio_Data, refresh_reddit_post_data
from Functions.BlockMindsStatusBot import send_status_message
import pytz
from Functions.MongoDB import Yearly_MarketChartData_Data

pd.options.mode.chained_assignment = None

ist = pytz.timezone("Asia/Kolkata")

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
        print("🔄 Loading Crypto Data from CoinGecko using User Portfolio Coin IDs.")
        
        # Coins you want to fetch data for
        coin_ids = get_coin_ids()  # Replace with your list
        
        if not coin_ids:
            raise ValueError("No coin IDs returned from get_coin_ids()")

        df = get_specific_coin_data(coin_ids=coin_ids)

        if df.empty:
            raise ValueError("No data returned from get_specific_coin_data")

        print(f"✅ Based on User Portfolio, {df.shape[0]} CryptoCoins data loaded successfully from CoinGecko.")
        return df

    except Exception as e:
        send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error loading crypto analysis data: {e}")
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

def prepare_reddit_post_df(posts, query):
    sia = SentimentIntensityAnalyzer()
    records = []

    # Get timestamps for CoinGecko
    timestamps = [datetime.utcfromtimestamp(p.created_utc) for p in posts]
    if not timestamps:
        return pd.DataFrame()

    start_ts = int(min(timestamps).timestamp())
    end_ts = int(max(timestamps).timestamp()) + 3600 * 6

    # Fetch CoinGecko Price Data
    url = f"https://api.coingecko.com/api/v3/coins/{query.lower()}/market_chart/range"
    params = {"vs_currency": "usd", "from": start_ts, "to": end_ts}
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        price_df = pd.DataFrame(data.get("prices", []), columns=["timestamp", "price"])
        price_df["timestamp"] = price_df["timestamp"] // 1000
    except:
        price_df = pd.DataFrame()

    # Loop through posts and collect data
    for post in posts:
        sentiment = sia.polarity_scores(post.title)
        compound = sentiment['compound']

        t_post = datetime.utcfromtimestamp(post.created_utc)
        t_now = int(t_post.timestamp())
        t_later = t_now + 3600 * 6

        try:
            price_now_df = price_df.iloc[(price_df["timestamp"] - t_now).abs().argsort()[:1]]
            price_later_df = price_df.iloc[(price_df["timestamp"] - t_later).abs().argsort()[:1]]

            price_now = price_now_df["price"].values[0] if not price_now_df.empty else None
            price_later = price_later_df["price"].values[0] if not price_later_df.empty else None
            pct_change = ((price_later - price_now) / price_now * 100) if price_now and price_later else None
        except:
            price_now = price_later = pct_change = None

        records.append({
            "coin": query.lower(),
            "title": post.title,
            "created_utc": t_post.isoformat(),
            "permalink": f"https://www.reddit.com{post.permalink}",
            "author": str(post.author),
            "subreddit": str(post.subreddit),
            "url": post.url,
            "upvotes": post.score,
            "comments": post.num_comments,
            "sentiment_score": compound,
            "price_at_post": price_now,
            "price_6hr_after": price_later,
            "price_change_pct": pct_change
        })

    return pd.DataFrame(records)

# Function to get sentiment score & engagement metrics
def get_reddit_sentiment_with_pagination(query, total_posts=500, batch_size=100):
    sia = SentimentIntensityAnalyzer()
    posts = []
    after = None
    fetched_posts = 0

    # For most upvoted post (full metadata)
    top_post_data = {
        "title": "",
        "score": 0,
        "num_comments": 0,
        "created_utc": "",
        "permalink": "",
        "author": "",
        "subreddit": "",
        "url": "",
        "selftext": "",
        "sentiment_score": 0,
        "image_url": ""
    }

    created_times = []

    while fetched_posts < total_posts:
        search_results = reddit.subreddit("cryptocurrency+CryptoMarkets").search(
            query, limit=batch_size, params={'after': after}
        )
        batch_posts = list(search_results)

        if not batch_posts:
            break

        posts.extend(batch_posts)
        fetched_posts += len(batch_posts)
        after = batch_posts[-1].id

        if len(batch_posts) < batch_size:
            break

    # Aggregation variables
    sentiment_score = 0
    total_upvotes = 0
    total_comments = 0
    post_volumes = 0
    sentiment_trends = []
    positive_mentions = 0
    neutral_mentions = 0
    negative_mentions = 0

    for post in posts:
        sentiment = sia.polarity_scores(post.title)
        compound = sentiment['compound']
        sentiment_score += compound
        sentiment_trends.append(compound)

        upvotes = post.score
        comments = post.num_comments
        total_upvotes += upvotes
        total_comments += comments
        post_volumes += 1

        # Save the most upvoted post with full metadata
        if upvotes > top_post_data["score"]:
            # Try to extract image URL
            image_url = ""
            if post.url.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                image_url = post.url
            elif hasattr(post, "preview"):
                try:
                    image_url = post.preview["images"][0]["source"]["url"].replace("&amp;", "&")
                except:
                    image_url = ""
            elif hasattr(post, "thumbnail") and post.thumbnail.startswith("http"):
                image_url = post.thumbnail

            top_post_data = {
                "title": post.title,
                "score": upvotes,
                "num_comments": comments,
                "created_utc": datetime.utcfromtimestamp(post.created_utc).strftime("%Y-%m-%d %H:%M:%S"),
                "permalink": f"https://www.reddit.com{post.permalink}",
                "author": str(post.author),
                "subreddit": str(post.subreddit),
                "url": post.url,
                "selftext": post.selftext[:500] if hasattr(post, "selftext") else "",
                "sentiment_score": compound,
                "image_url": image_url
            }

        # Sentiment breakdown
        if compound >= 0.05:
            positive_mentions += 1
        elif compound <= -0.05:
            negative_mentions += 1
        else:
            neutral_mentions += 1

        # Mention date tracking
        if hasattr(post, "created_utc"):
            created_times.append(datetime.utcfromtimestamp(post.created_utc))

    # Basic metrics
    count = max(post_volumes, 1)
    avg_sentiment = sentiment_score / count
    avg_upvotes = total_upvotes / count
    avg_comments = total_comments / count
    sentiment_trend = np.mean(sentiment_trends) if sentiment_trends else 0
    engagement_rate = (total_upvotes + total_comments) / count
    positive_pct = positive_mentions / count
    negative_pct = negative_mentions / count

    # Mentions per day
    if created_times:
        days_range = max((max(created_times) - min(created_times)).days, 1)
        mentions_per_day = post_volumes / days_range
    else:
        mentions_per_day = 0

    # Trending logic
    trending = "Yes" if sentiment_trend > 0.2 or engagement_rate > 10 else "No"
    
    # Prepare DataFrame from posts
    df = prepare_reddit_post_df(posts, query)
    if not df.empty:
        refresh_reddit_post_data(df)

    # Return the aggregated metrics
    return {
        # Base metrics
        "Avg Sentiment": avg_sentiment,
        "Post Volume": post_volumes,
        "Avg Upvotes": avg_upvotes,
        "Avg Comments": avg_comments,
        "Sentiment Trend": sentiment_trend,
        "Positive Mentions": positive_mentions,
        "Neutral Mentions": neutral_mentions,
        "Negative Mentions": negative_mentions,

        # Engagement & trend insights
        "Engagement Rate": engagement_rate,
        "Positive %": positive_pct,
        "Negative %": negative_pct,
        "Mentions per Day": mentions_per_day,
        "Trending": trending,

        # Top post metadata
        "Top Post Title": top_post_data["title"],
        "Top Post Upvotes": top_post_data["score"],
        "Top Post Comments": top_post_data["num_comments"],
        "Top Post Date": top_post_data["created_utc"],
        "Top Post Link": top_post_data["permalink"],
        "Top Post Author": top_post_data["author"],
        "Top Post Subreddit": top_post_data["subreddit"],
        "Top Post URL": top_post_data["url"],
        "Top Post Body": top_post_data["selftext"],
        "Top Post Sentiment": top_post_data["sentiment_score"],
        "Top Post Image URL": top_post_data["image_url"]
    }

# Get Price on the Purchase Date from CoinGecko
def get_crypto_price_on_purchase_date(symbol: str, date_str: str) -> float:
    try:
        timestamp = int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())
        url = f"https://min-api.cryptocompare.com/data/pricehistorical?fsym={symbol.upper()}&tsyms=USD&ts={timestamp}"
        headers = {
            "Accept": "application/json",
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        return data[symbol.upper()]["USD"]
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

# Full Analysis
def Analysis():
    
    # Load the data globaly 
    df = load_data()
    print("🔄 Start Analyzing the Crypto Data which fetched the Coingecko API")

    # Select the Coin ID column and convert it to a list
    crypto_Ids = df['Coin ID'].tolist()

    # Dictionary to store Sharpe Ratios and technical indicators for each Crypto_Id
    crypto_analysis_dict = {}

    # Coin loop
    for Crypto_Id in crypto_Ids:
        try:
            # ✅ Fetch all market chart data from MongoDB once
            full_market_data = pd.DataFrame(Yearly_MarketChartData_Data())
        
            # ✅ Filter data for this coin
            coin_data = full_market_data[full_market_data['Coin_id'] == Crypto_Id].copy()

            if coin_data.empty:
                send_status_message(Status_TELEGRAM_CHAT_ID, f"⚠️ No historical market data found for {Crypto_Id}. Skipping.")
                continue

            # ✅ Convert timestamp and prepare price series
            coin_data['Timestamp'] = pd.to_datetime(coin_data['Timestamp'])
            coin_data.set_index('Timestamp', inplace=True)
            prices = coin_data[['Price']].rename(columns={'Price': 'price'}).sort_index()

        except Exception as e:
            send_status_message(Status_TELEGRAM_CHAT_ID, f"❌ Error processing market chart data for {Crypto_Id}: {e}")
            continue
        
        # Price on Purchase Date
        Assets = UserPortfolio_Data()
        Assets_df = pd.DataFrame(Assets)
        symbol = df[df['Coin ID'] == Crypto_Id]['Symbol'].iloc[0]
        purchase_date =  Assets_df[Assets_df['coin_symbol'] == symbol]['purchase_date'].iloc[0]
        
        prices['Price on Puchase Date'] = get_crypto_price_on_purchase_date(symbol=symbol, date_str=purchase_date)

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
    
    reddit_data = df["Coin Name"].apply(get_reddit_sentiment_with_pagination)
    df["Reddit Sentiment"] = reddit_data.apply(lambda x: x["Avg Sentiment"])
    df["Reddit Mentions"] = reddit_data.apply(lambda x: x["Post Volume"])
    df["Avg Reddit Upvotes"] = reddit_data.apply(lambda x: x["Avg Upvotes"])
    df["Avg Reddit Comments"] = reddit_data.apply(lambda x: x["Avg Comments"])
    df["Sentiment Trend"] = reddit_data.apply(lambda x: x["Sentiment Trend"])
    df["Positive Mentions"] = reddit_data.apply(lambda x: x["Positive Mentions"])
    df["Neutral Mentions"] = reddit_data.apply(lambda x: x["Neutral Mentions"])
    df["Negative Mentions"] = reddit_data.apply(lambda x: x["Negative Mentions"])
    df["Engagement Rate"] = reddit_data.apply(lambda x: x["Engagement Rate"])
    df["Positive %"] = reddit_data.apply(lambda x: x["Positive %"])
    df["Negative %"] = reddit_data.apply(lambda x: x["Negative %"])
    df["Top Post Title"] = reddit_data.apply(lambda x: x["Top Post Title"])
    df["Top Post Upvotes"] = reddit_data.apply(lambda x: x["Top Post Upvotes"])
    df["Mentions per Day"] = reddit_data.apply(lambda x: x["Mentions per Day"])
    df["Trending"] = reddit_data.apply(lambda x: x["Trending"])    
    df["Top Post Title"] = reddit_data.apply(lambda x: x["Top Post Title"])
    df["Top Post Upvotes"] = reddit_data.apply(lambda x: x["Top Post Upvotes"])
    df["Top Post Comments"] = reddit_data.apply(lambda x: x["Top Post Comments"])
    df["Top Post Date"] = reddit_data.apply(lambda x: x["Top Post Date"])
    df["Top Post Link"] = reddit_data.apply(lambda x: x["Top Post Link"])
    df["Top Post Author"] = reddit_data.apply(lambda x: x["Top Post Author"])
    df["Top Post Subreddit"] = reddit_data.apply(lambda x: x["Top Post Subreddit"])
    df["Top Post URL"] = reddit_data.apply(lambda x: x["Top Post URL"])
    df["Top Post Body"] = reddit_data.apply(lambda x: x["Top Post Body"])
    df["Top Post Sentiment"] = reddit_data.apply(lambda x: x["Top Post Sentiment"])
    df["Top Post Image URL"] = reddit_data.apply(lambda x: x["Top Post Image URL"])
    
    df["Price on Puchase Date"]=df['Coin ID'].map({k: v['Price on Puchase Date'].iloc[-1] for k, v in crypto_analysis_dict.items()})
    
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
    print("✅ All Analysis Completed Successfully.")
    return df

