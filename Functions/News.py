import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from textblob import TextBlob
from Functions.MongoDB import get_coin_ids, get_coin_names
from dateutil import parser
import pytz

from pymongo import MongoClient  # only if MongoDB is used

# === Load Environment ===
load_dotenv()
nltk.download("vader_lexicon")

# === MongoDB Client ===
client = MongoClient(os.getenv("MONGO_URI"))  # Mongo URI from .env
Status_TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Optional for logs

# === API KEYS ===
api_keys = [
    os.getenv("NEWS_API_ankitkumar875740"),
    os.getenv("NEWS_API_kingoflovee56"),
    os.getenv("NEWS_API_bloodycrewff"),
]
newdata_key = os.getenv("NEWSDATA_API_KEY")
mediastack_key = os.getenv("MEDIASTACK_API_KEY")
contextual_key = os.getenv("CONTEXTUAL_API_KEY")

# === VADER ===
sid = SentimentIntensityAnalyzer()

# === Utility to auto-clean coin names for news search ===
def build_coin_name_map(coin_ids):
    name_map = {}
    for coin_id in coin_ids:
        # Skip short or suspicious tokens (e.g. ticker-like)
        if len(coin_id) < 3 or any(char.isdigit() for char in coin_id):
            print(f"⚠️ Skipping invalid coin: {coin_id}")
            continue
        readable = coin_id.replace("-", " ")
        if len(readable.split()) == 1 and readable.lower() not in ["bitcoin", "ethereum", "dogecoin", "tron", "solana"]:
            readable += " coin"
        name_map[coin_id] = readable.lower().strip()
    return name_map

def get_sentiment(text):
    # VADER Sentiment Analysis
    scores = sid.polarity_scores(text or "")
    compound = scores["compound"]
    vader_sentiment = "positive" if compound > 0.05 else "negative" if compound < -0.05 else "neutral"
    
    # TextBlob Sentiment Analysis
    blob = TextBlob(text)
    textblob_sentiment = "positive" if blob.sentiment.polarity > 0 else "negative" if blob.sentiment.polarity < 0 else "neutral"
    
    # Combine both results for better accuracy (Take the majority sentiment or mixed)
    final_sentiment = vader_sentiment if vader_sentiment == textblob_sentiment else "mixed"
    return final_sentiment, compound

# === News Fetchers ===
def get_newsapi_articles(coin_name, coin, from_date, to_date, min_articles, max_retries=3, delay=1.5):
    articles = []
    for key in api_keys:
        attempt = 0
        while attempt < max_retries:
            try:
                url = (
                    f"https://newsapi.org/v2/everything?q={coin}"
                    f"&from={from_date}&to={to_date}&language=en"
                    f"&sortBy=popularity&pageSize=10&apiKey={key}"
                )
                res = requests.get(url, timeout=10)
                data = res.json()

                if res.status_code == 429 or data.get("code") == "rateLimited":
                    print(f"🔁 NewsAPI rate limit hit for key. Retrying...")
                    time.sleep(delay * (2 ** attempt))  # exponential backoff
                    attempt += 1
                    continue

                if res.status_code != 200:
                    print(f"⚠️ NewsAPI error for {coin}: {res.status_code}")
                    break

                for a in data.get("articles", []):
                    articles.append({
                        "coin": coin_name,
                        "title": a.get("title"),
                        "description": a.get("description"),
                        "url": a.get("url"),
                        "image_url": a.get("urlToImage"),
                        "source": a["source"]["name"],
                        "published": a.get("publishedAt"),
                        "creator": a.get("author"),
                        "country": None,
                        "language": "en",
                        "category": "business"
                    })

                break  # Break retry loop on success

            except requests.exceptions.RequestException as e:
                print(f"⚠️ NewsAPI network error for {coin}: {e}")
                time.sleep(delay * (2 ** attempt))
                attempt += 1

        if len(articles) >= min_articles:
            break

    return articles[:min_articles]

def get_newsdata_articles(coin_name, coin, min_needed):
    url = f"https://newsdata.io/api/1/news?apikey={newdata_key}&q={coin}&language=en&category=business"
    res = requests.get(url)
    articles = []
    if res.status_code == 200:
        for a in res.json().get("results", []):
            articles.append({
                "coin": coin_name,
                "title": a.get("title"),
                "description": a.get("description"),
                "url": a.get("link"),
                "image_url": a.get("image_url"),
                "source": a.get("source_id"),
                "published": a.get("pubDate"),
                "creator": a.get("creator", [None])[0] if a.get("creator") else None,
                "country": a.get("country"),
                "language": a.get("language"),
                "category": a.get("category"),
            })
            if len(articles) >= min_needed:
                break
    return articles

def get_mediastack_articles(coin_name, coin, min_needed):
    url = f"http://api.mediastack.com/v1/news?access_key={mediastack_key}&keywords={coin}&languages=en"
    res = requests.get(url)
    articles = []
    if res.status_code == 200:
        for a in res.json().get("data", []):
            articles.append({
                "coin": coin_name,
                "title": a.get("title"),
                "description": a.get("description"),
                "url": a.get("url"),
                "image_url": None,
                "source": a.get("source"),
                "published": a.get("published_at"),
                "creator": None,
                "country": None,
                "language": "en",
                "category": "business",
            })
            if len(articles) >= min_needed:
                break
    return articles

def get_contextual_articles(coin_name, coin, min_needed):
    url = "https://contextualwebsearch-websearch-v1.p.rapidapi.com/api/Search/NewsSearchAPI"
    querystring = {"q": coin, "pageNumber": "1", "pageSize": str(min_needed), "autoCorrect": "true"}
    headers = {
        "X-RapidAPI-Key": contextual_key,
        "X-RapidAPI-Host": "contextualwebsearch-websearch-v1.p.rapidapi.com"
    }
    res = requests.get(url, headers=headers, params=querystring)
    articles = []
    if res.status_code == 200:
        for a in res.json().get("value", []):
            articles.append({
                "coin": coin_name,
                "title": a.get("title"),
                "description": a.get("description"),
                "url": a.get("url"),
                "image_url": a.get("image", {}).get("url"),
                "source": a.get("provider", {}).get("name"),
                "published": a.get("datePublished"),
                "creator": None,
                "country": None,
                "language": "en",
                "category": "business",
            })
            if len(articles) >= min_needed:
                break
    return articles

# === All-In-One Fetch + Sentiment + Price ===
def get_all_news_with_analysis(min_articles=100):
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    all_results = []

    # Coin names for news, CoinGecko IDs for price
    coin_names = get_coin_names()
    coin_ids = get_coin_ids()
    coin_map = dict(zip(coin_names, coin_ids))  # { 'Bitcoin': 'bitcoin', 'SPX6900': None, ... }

    for coin in coin_names:
        search_term = coin.lower().strip()

        # Add "coin" if too short or has digits (to improve search quality)
        if len(search_term) < 4 or any(char.isdigit() for char in search_term):
            search_term += " coin"

        print(f"🔍 Fetching news for: {coin} → '{search_term}'")

        articles = []
        try:
            articles = get_newsapi_articles(coin_name=coin, coin = search_term, from_date = yesterday, to_date =today, min_articles= min_articles)
            print(f"✅ NewsAPI returned {len(articles)} articles for {coin}")
        except Exception as e:
            print(f"❌ NewsAPI failed for {coin}: {e}")

        if len(articles) < min_articles:
            try:
                remaining = min_articles - len(articles)
                print(f"⚠️ Fetching {remaining} articles from NewsData.io")
                articles += get_newsdata_articles(coin_name=coin, coin=search_term, min_needed=remaining)
            except Exception as e:
                print(f"❌ NewsData.io failed: {e}")

        if len(articles) < min_articles:
            try:
                remaining = min_articles - len(articles)
                print(f"⚠️ Fetching {remaining} articles from MediaStack")
                articles += get_mediastack_articles(coin_name=coin,coin=search_term, min_needed=remaining)
            except Exception as e:
                print(f"❌ MediaStack failed: {e}")

        if len(articles) < min_articles:
            try:
                remaining = min_articles - len(articles)
                print(f"⚠️ Fetching {remaining} articles from ContextualWeb")
                articles += get_contextual_articles(coin_name=coin, coin=search_term, min_needed=remaining)
            except Exception as e:
                print(f"❌ ContextualWeb failed: {e}")

        # === Clean and enrich articles ===
        valid_articles = []
        for article in articles:
            try:
                if not article.get("title"):
                    continue
                sentiment, score = get_sentiment(article["title"])
                article["sentiment"] = sentiment
                article["sentiment_score"] = score

                creator = article.get("creator")
                if isinstance(creator, list):
                    article["author"] = creator[0] if creator else None
                elif isinstance(creator, str):
                    article["author"] = creator
                else:
                    article["author"] = None

                published = article.get("published")
                dt = parser.parse(published)
                if dt.tzinfo is None:
                    dt = pytz.utc.localize(dt)
                else:
                    dt = dt.astimezone(pytz.utc)

                article["published_dt"] = dt
                article["published"] = dt.isoformat()
                valid_articles.append(article)
            except Exception as e:
                print(f"⚠️ Skipping article due to date parse error: {e}")

        if not valid_articles:
            continue

        # === Use valid CoinGecko ID for price fetching ===
        cg_id = coin_map.get(coin)
        if not cg_id:
            print(f"⚠️ Skipping CoinGecko price fetch for {coin} (no valid ID)")
            for a in valid_articles:
                a["price_at_news"] = None
                a["price_6hr_after"] = None
                a["price_change_pct"] = None
            all_results.extend(valid_articles)
            continue

        # === Fetch price range for coin ===
        timestamps = [a["published_dt"] for a in valid_articles]
        base_start = int(min(timestamps).timestamp())
        base_end = int(max(timestamps).timestamp()) + 3600 * 6

        df = None
        for attempt in range(5):
            delta = attempt * 300  # 5 mins per retry
            start_ts = base_start - delta
            end_ts = base_end + delta

            print(f"📈 Try {attempt + 1}: Fetching CoinGecko prices for {cg_id}: {start_ts} to {end_ts}")
            url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart/range"
            params = {"vs_currency": "usd", "from": start_ts, "to": end_ts}

            try:
                resp = requests.get(url, params=params, timeout=15)
                data = resp.json()
                if "prices" in data and data["prices"]:
                    df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
                    df["timestamp"] = df["timestamp"] // 1000
                    break
                else:
                    print(f"⚠️ No price data on attempt {attempt + 1}, sleeping 50s...")
                    time.sleep(50)
            except Exception as e:
                print(f"❌ API error on attempt {attempt + 1}: {e}")
                time.sleep(50)

        if df is None or df.empty:
            print(f"⚠️ Skipping {coin}: No price data after 5 retries.")
            continue

        # === Assign price to each article ===
        for article in valid_articles:
            try:
                t_news = int(article["published_dt"].timestamp())
                t_later = t_news + 3600 * 6

                if not df.empty:
                    price_now_df = df.iloc[(df["timestamp"] - t_news).abs().argsort()[:1]]
                    price_later_df = df.iloc[(df["timestamp"] - t_later).abs().argsort()[:1]]

                    price_now = price_now_df["price"].values[0] if not price_now_df.empty else None
                    price_later = price_later_df["price"].values[0] if not price_later_df.empty else None

                    pct_change = ((price_later - price_now) / price_now * 100) if price_now and price_later else None
                else:
                    price_now, price_later, pct_change = None, None, None

                article["price_at_news"] = price_now
                article["price_6hr_after"] = price_later
                article["price_change_pct"] = pct_change

            except Exception as e:
                print(f"⚠️ Failed to match price for article: {e}")
                article["price_at_news"] = None
                article["price_6hr_after"] = None
                article["price_change_pct"] = None

        all_results.extend(valid_articles)
        print(f"✅ Total collected for {coin}: {len(valid_articles)}\n")
        time.sleep(1.2)  # Avoid hitting CoinGecko too fast

    return pd.DataFrame(all_results)


