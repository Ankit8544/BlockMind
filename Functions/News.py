import requests
import pandas as pd
import time
from Functions.MongoDB import get_coin_ids
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

# List of available API keys
api_keys = [
    os.getenv("NEWS_API_ankitkumar875740"),
    os.getenv("NEWS_API_kingoflovee56"),
    os.getenv("NEWS_API_bloodycrewff"),
]

def get_newsapi_headlines(min_articles=5, delay=1.5):
    coin_ids = get_coin_ids()

    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    Today_Date = today.strftime("%Y-%m-%d")
    Yesterday_Date = yesterday.strftime("%Y-%m-%d")

    all_articles = []
    key_index = 0

    for coin_id in coin_ids:
        print(f"🔎 Searching news for: {coin_id}")

        while key_index < len(api_keys):
            current_key = api_keys[key_index]
            url = (
                f"https://newsapi.org/v2/everything?"
                f"q={coin_id}&from={Yesterday_Date}&to={Today_Date}"
                f"&language=en&sortBy=popularity&apiKey={current_key}"
            )

            response = requests.get(url)

            # Handle hard limit per key
            if response.status_code == 429:
                key_index += 1
                continue

            data = response.json()

            # Handle internal API message-based rate limit
            if data.get("status") == "error" and data.get("code") == "rateLimited":
                key_index += 1
                continue

            if response.status_code != 200 or data.get("status") != "ok":
                break  # Don't retry other errors, just skip coin

            # Process articles (limit to 10)
            articles = data.get("articles", [])[:10]
            for article in articles:
                all_articles.append({
                    "coin_name": coin_id,
                    "source": article["source"]["name"],
                    "author": article.get("author"),
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "url": article.get("url"),
                    "urlToImage": article.get("urlToImage"),
                    "publishedAt": article.get("publishedAt"),
                    "content": article.get("content")
                })

            time.sleep(delay)
            break  # break the while loop, move to next coin

        # If all keys exhausted
        if key_index >= len(api_keys):
            print("❌ All API keys exhausted. Stopping further requests.")
            break

    df = pd.DataFrame(all_articles)
    return df
