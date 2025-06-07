import os
import pandas as pd
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from textblob import TextBlob
from serpapi import GoogleSearch
import pytz
import ccxt
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Download necessary NLTK data
nltk.download("vader_lexicon")

# Initialize Vader Sentiment Analyzer
sia = SentimentIntensityAnalyzer()

# Set up API key 
API_KEY = os.getenv("NEWS_API")

# Function to convert UTC date to IST
def convert_to_ist(date_str):
    # Define IST timezone
    ist = pytz.timezone("Asia/Kolkata")
    utc_dt = datetime.strptime(date_str, "%m/%d/%Y, %I:%M %p, %z UTC")  # Parse UTC datetime
    utc_dt = utc_dt.replace(tzinfo=pytz.utc)  # Set timezone to UTC
    ist_dt = utc_dt.astimezone(ist)  # Convert to IST
    return ist_dt

# Define function to get sentiment scores
def get_sentiment(text):
    if text:
        return sia.polarity_scores(text)["compound"]  # Compound score (-1 to 1)
    return 0  # If text is None, return neutral

# Function to fetch the current price of DOGE/USDT
def Current_price(date_str):
    try:
        
        # Initialize Binance API once (to avoid multiple instances)
        exchange = ccxt.binance()
        
        # Define the format
        date_format = "%d/%m/%Y, %I:%M %p"

        # Convert string to datetime object
        ist = pytz.timezone('Asia/Kolkata')  # IST Timezone
        dt = datetime.strptime(date_str, date_format)

        # Localize the datetime to IST if not already localized
        dt = ist.localize(dt) if dt.tzinfo is None else dt

        # Convert to Unix timestamp (milliseconds)
        timestamp = int(dt.timestamp()) * 1000  

        # Define the trading pair and timeframe
        symbol = 'DOGE/USDT'
        timeframe = '1m'  # 1-minute intervals

        # Fetch OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=timestamp, limit=1)

        # Check if data is received
        if not ohlcv:
            return None  # No data available

        _, open_price, high_price, low_price, close_price, volume = ohlcv[0]
        return close_price

    except Exception as e:
        print(f"Error fetching price for {date_str}: {e}")
        return None

# Function to fetch the current price of DOGE/USDT 1 hour later
def Price_After_1hr(date_str):
    try:
        
        # Initialize Binance API once (to avoid multiple instances)
        exchange = ccxt.binance()
        
        # Define the format
        date_format = "%d/%m/%Y, %I:%M %p"

        # Convert string to datetime object
        ist = pytz.timezone('Asia/Kolkata')  # IST Timezone
        dt = datetime.strptime(date_str, date_format)

        # If datetime is naive, localize it to IST
        if dt.tzinfo is None:
            dt = ist.localize(dt)

        # Add 1 hour
        dt = dt + timedelta(hours=1)

        # Convert to Unix timestamp (milliseconds)
        timestamp = int(dt.timestamp()) * 1000  

        # Define trading pair and timeframe
        symbol = 'DOGE/USDT'
        timeframe = '1m'  # 1-minute intervals

        # Fetch OHLCV data (Limit = 2 to ensure correct candle)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=timestamp, limit=2)

        # Check if data is received
        if len(ohlcv) < 2:
            return None  # No sufficient data

        # Get the closing price of the 2nd candle (approx 1 hour later)
        close_price = ohlcv[1][4]  
        return close_price

    except ccxt.base.errors.RateLimitExceeded:
        print("Rate limit exceeded. Retrying after delay...")
        time.sleep(2)  # Delay before retrying
        return Price_After_1hr(date_str)

    except Exception as e:
        print(f"Error fetching price for {date_str}: {e}")
        return None

def News_Analysis():
    print("Start Fetch News from Google API")
    params = {
    "engine": "google_news",
    "q": "dogecoin",
    "gl": "in",
    "hl": "en",
    "api_key": API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    news_results = results["news_results"]

    df = pd.DataFrame(news_results)
    print("Successfully Converted Into DataFrame")
    
    # Convert date column to IST
    df["date"] = df["date"].apply(convert_to_ist)

    df["date"] = df["date"].dt.strftime("%d/%m/%Y, %I:%M %p")

    # Convert the 'date' column to datetime format
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y, %I:%M %p')

    # Get the current datetime
    current_time = datetime.now()

    # Sort: First, upcoming dates; then, past dates
    df = df.sort_values(by='date', key=lambda x: abs(x - current_time))

    df["date"] = df["date"].dt.strftime("%d/%m/%Y, %I:%M %p")

    # Reindex the DataFrame
    df = df.reset_index(drop=True)

    df["source"] = df["source"].apply(lambda x: x.get("name") if isinstance(x, dict) else None)

    # Drop specific columns (replace 'column1', 'column2' with actual column names)
    columns_to_drop = ['position', 'thumbnail_small']  # Modify with actual column names
    df = df.drop(columns=columns_to_drop, errors='ignore')

    print("Basic Data Cleaning and Formatting Completed Successfully!")
    
    # Apply sentiment analysis on news title
    df["sentiment_vader"] = df["title"].apply(get_sentiment)

    # TextBlob Sentiment Analysis
    df["sentiment_textblob"] = df["title"].apply(lambda x: TextBlob(str(x)).sentiment.polarity)

    # Rename columns (Modify as needed)
    df = df.rename(columns={
        'title': 'News Title',
        'source': 'Source',
        'link': 'News URL',
        'thumbnail': 'Thumbnail',
        'date': 'Date',
        'sentiment_vader': 'Sentiment Vader Score',
        'sentiment_textblob': 'Sentiment Textblob Score'
    })

    # Re-arrange columns in the specified order
    column_order = ['Date', 'News Title', 'Source', 'News URL', 'Thumbnail', 'Sentiment Vader Score', 'Sentiment Textblob Score']
    df = df[column_order]

    print("Sentiment Analysis Completed Successfully!")

    # Ensure "Date" column exists in DataFrame
    if "Date" in df.columns:
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=10) as executor:
            df["Current Price"] = list(executor.map(Current_price, df["Date"]))

        print("Fetching Current Price Processing completed successfully!")
    else:
        print("Error: 'Date' column not found in DataFrame")
        

    # Ensure "Date" column exists in DataFrame
    if "Date" in df.columns:
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=5) as executor:  # Reduce workers to prevent API rate limits
            df["Price After 1 Hr"] = list(executor.map(Price_After_1hr, df["Date"]))

        print("Fetching Price After 1hr Processing completed successfully!")
    else:
        print("Error: 'Date' column not found in DataFrame")
        
    df["Price Change %"] = ((df["Price After 1 Hr"] - df["Current Price"]) / df["Current Price"]) * 100
    
    print("All the Analysis is completed successfully! ")
    
    return df

