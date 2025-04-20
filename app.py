from flask import Flask, jsonify
import pandas as pd
import requests
import datetime
from dotenv import load_dotenv
import os
import pytz
import google.generativeai as genai

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Load API credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

GEMINI_API_KEYS = [
    (os.getenv("ankitkumar875740")), 
    (os.getenv("kingoflovee56")), 
    (os.getenv("bloodycrewff"))
    ]

def get_valid_api_key():
    for key in GEMINI_API_KEYS:
        try:
            genai.configure(api_key=key)
            genai.GenerativeModel('gemini-1.5-pro')  # Only configures the model without generating content
            return key
        except Exception as e:
            print(f"API key {key} failed: {e}")
    return None

GEMINI_API_KEY = get_valid_api_key()

# Configure Gemini AI
def Gemini(user_message):
    """Generates AI response using Gemini API."""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(user_message)
        if response and hasattr(response, "text"):
            return response.text.strip()
        return "I'm unable to process that request right now."
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return "🚫 AI is currently unavailable. Try again later."

def send_telegram_message(chat_id, message):
    """Sends a message to a specific Telegram user."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram API Error: {e}")
        return {"error": str(e)}

@app.route('/getdata', methods=['GET'])
def getdata():
    # Define IST timezone
    ist = pytz.timezone('Asia/Kolkata')

    # Get current UTC timestamp and subtract 24h (86400 seconds)
    end_time = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    start_time = end_time - 86400

    # CoinGecko API - fetch price data
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
    params = {
        'vs_currency': 'usd',
        'from': start_time,
        'to': end_time
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Load into DataFrame
    df = pd.DataFrame(data['prices'], columns=['timestamp_ms', 'price_usd'])

    # Convert to datetime in UTC → IST
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True)
    df['timestamp_ist'] = df['timestamp_utc'].dt.tz_convert(ist).dt.floor('H')

    # Group by hour and calculate average price
    df = df.groupby('timestamp_ist', as_index=False)['price_usd'].mean()

    # Convert datetime to string in 12-hour format for display
    df['Timestamp (IST)'] = df['timestamp_ist'].dt.strftime('%Y-%m-%d %I:%M %p')

    # Final output for Power BI
    df = df[['Timestamp (IST)', 'price_usd']]
    df.rename(columns={'price_usd': 'Bitcoin Price (USD)'}, inplace=True)

    prompt = f"""
        You are a smart AI analyst. Analyze the following Power BI dashboard dataset:

        {df}

        Your task:
        - Identify the domain of the data automatically (e.g., cryptocurrency, e-commerce, call center, healthcare, etc.).
        - Based on that, highlight 3–5 key insights that are **relevant and important** to that domain. 
        - Write it in a natural, executive summary style using plain text.
        - Use relevant emojis to make it engaging (📈📉⚠️✅❌).
        - Do not use Markdown formatting (no *, **, or #).
        - Avoid writing section headers like 'Key Findings'. Just write 3–5 short, punchy insights and end with a one-line performance summary.

        Examples:
        If the data is about Bitcoin, mention price trends, volume changes, volatility, etc.
        If it's about sales, mention top-performing products, revenue changes, etc.
        If it's call center data, talk about call volume, agent performance, satisfaction trends, etc.

        Make it sound like a report a business manager would understand instantly.
    """

    response = Gemini(prompt)
    send_telegram_message(TELEGRAM_CHAT_ID, response)

    # Convert to JSON and return
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
