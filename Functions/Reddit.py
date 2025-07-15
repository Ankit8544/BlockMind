import praw
import os
import time
import numpy as np
import pandas as pd
import random
from datetime import datetime
import pytz

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from dotenv import load_dotenv
from Functions.MongoDB import get_coin_names
from Functions.BlockMindsStatusBot import send_status_message

# === Environment Setup ===
load_dotenv()
ist = pytz.timezone("Asia/Kolkata")

# Reddit API credentials
reddit = praw.Reddit(
    client_id = "XQaZSF7aFd169cXHuQs4uA",
    client_secret = "NCF7iHpFDgkSpwYOESMVRlcrHRx3_Q",
    user_agent = "meme-coin-sentiment"
)

# === Sentiment Analyzer ===
sia = SentimentIntensityAnalyzer()

# === Fetch Reddit Posts with Sentiment ===
def get_reddit_sentiment_with_pagination(query, total_posts=200, batch_size=100):
    posts_data = []
    after = None
    fetched = 0

    while fetched < total_posts:
        results = reddit.subreddit("cryptocurrency+CryptoMarkets").search(query, limit=batch_size, params={'after': after})
        batch = list(results)

        if not batch:
            break

        for post in batch:
            if not post.title:
                continue

            sentiment = sia.polarity_scores(post.title)
            compound = sentiment["compound"]
            sentiment_label = (
                "positive" if compound >= 0.05 else
                "negative" if compound <= -0.05 else
                "neutral"
            )

            posts_data.append({
                "coin": query,
                "title": post.title,
                "url": f"https://reddit.com{post.permalink}",
                "image_url": post.thumbnail if post.thumbnail and post.thumbnail.startswith("http") else None,
                "score": post.score,
                "num_comments": post.num_comments,
                "created_utc": datetime.fromtimestamp(post.created_utc, tz=pytz.utc).astimezone(ist).isoformat(),
                "sentiment": sentiment_label,
                "sentiment_score": compound,
                "author": str(post.author),
                "subreddit": post.subreddit.display_name,
                "post_id": post.id,
                "permalink": post.permalink,
                "is_video": post.is_video,
                "is_self": post.is_self,
                "upvote_ratio": post.upvote_ratio,
                "stickied": post.stickied,
                "spoiler": post.spoiler,
                "over_18": post.over_18,
                "domain": post.domain
            })


            fetched += len(batch)
            after = batch[-1].id

            if len(batch) < batch_size:
                break

            time.sleep(random.uniform(1, 2))  # avoid rate limits

        return posts_data


# === Analysis Across All Portfolio Coins ===
def get_all_reddit_sentiment_with_analysis(min_posts=100):
    print("🔄 Fetching Reddit sentiment for portfolio coins...")
    coin_names = get_coin_names()
    all_posts = []

    for coin in coin_names:
        print(f"🔍 Analyzing Reddit posts for: {coin}")
        posts = get_reddit_sentiment_with_pagination(coin, total_posts=min_posts)

        for post in posts:
            post["coin"] = coin

        all_posts.extend(posts)
        time.sleep(1)

    print(f"✅ Total posts collected: {len(all_posts)}")
    return pd.DataFrame(all_posts)

