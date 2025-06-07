import tweepy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve API credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Authenticate with API v1.1 (Needed for media upload)
auth = tweepy.OAuth1UserHandler(TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
api = tweepy.API(auth)

# Authenticate using OAuth 2.0
client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

def tweets(tweet_text, image_path):
    try:
        # Upload image and get media ID
        media = api.media_upload(image_path)

        # Post tweet with image
        response = client.create_tweet(text=tweet_text, media_ids=[media.media_id])
        print(f"Tweet posted successfully! Tweet ID: {response.data['id']}")

    except tweepy.TweepyException as e:
        print(f"Error: {e}")
        
