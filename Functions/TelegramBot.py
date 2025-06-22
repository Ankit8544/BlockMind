import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import pandas as pd
from Functions.GeminiAI import AI_Generated_Answer
from Functions.MongoDB import CryptoCoins_Data, UserPortfolio_Data
import time
start_time = time.time()

# Load environment variables
load_dotenv()

# Load API credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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

def send_telegram_post(chat_id, image_path, caption=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        data = {
            "chat_id": chat_id,
            "parse_mode": "Markdown",
        }
        if caption:
            data["caption"] = caption

        if image_path.startswith("http://") or image_path.startswith("https://"):
            # Send remote image URL directly
            data["photo"] = image_path
            response = requests.post(url, data=data)
        else:
            # Send local file
            with open(image_path, "rb") as photo:
                files = {"photo": photo}
                response = requests.post(url, data=data, files=files)

        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Telegram Photo API Error: {e}")
        return {"error": str(e)}

def format_large_number(num):
    if num >= 1_000_000_000_000:  # Trillion
        return f"{num / 1_000_000_000_000:.2f} Trillion"
    elif num >= 1_000_000_000:  # Billion
        return f"{num / 1_000_000_000:.2f} Billion"
    elif num >= 1_000_000:  # Million
        return f"{num / 1_000_000:.2f} Million"
    elif num >= 1_000:  # Thousand
        return f"{num / 1_000:.2f}K"
    else:
        return str(num)  # No conversion needed for small numbers

def Coin_Updates(username):
    messages = []  # To store messages for all rows
    
    # Get the current USD to INR exchange rate
    url = "https://open.er-api.com/v6/latest/USD"
    response = requests.get(url)

    if response.status_code == 200:
        usd = response.json()
        usd_to_inr = usd.get('rates', {}).get('INR', None)
        if usd_to_inr is None:
            raise ValueError("INR exchange rate not found in API response.")
    else:
        raise ConnectionError(f"Failed to fetch exchange rates. Status code: {response.status_code}")

        messages = []

    try:
        user_data = UserPortfolio_Data()
        if not user_data:
            return "⚠️ No user portfolio data found."

        # ✅ Step A: Find all fields like 'telegram_username_1', 'telegram_username_2', etc.
        username_columns = [col for col in user_df.columns if col.startswith('telegram_username')]

        # ✅ Step B: Filter rows where the username exists in any of those columns
        mask = user_df[username_columns].apply(lambda row: username in row.values, axis=1)
        user_df = user_df[mask]

        # ✅ Step C: Handle case when no matching username is found
        if user_df.empty:
            return f"⚠️ No coin data found for username: {username}"


        coin_list = user_df['coin_name'].to_list()

        crypto_data = CryptoCoins_Data()
        if not crypto_data:
            return "⚠️ No crypto data available right now. Please try again later."

        df = pd.DataFrame(crypto_data)
        df = df[df['Coin Name'].isin(coin_list)]
        if df.empty:
            return "⚠️ No matching coins found in analyzed crypto data."

        try:
            for index, row in df.iterrows():
                coin_name = row.get("Coin Name", "N/A")
                current_price = row.get("Current Price", 0)
                market_cap = row.get("Market Cap", 0)
                rank = row.get("Market Cap Rank", "N/A")
                high_price = row.get("24h High Price", 0)
                low_price = row.get("24h Low Price", 0)
                price_change = row.get("24h Price Change", 0)
                price_change_percentage = row.get("24h Price Change Percentage (%)", 0)
                market_cap_change = row.get("24h Market Cap Change", 0)
                market_cap_change_percentage = row.get("24h Market Cap Change Percentage (%)", 0)
                all_time_high_price = row.get("All-Time High Price", 0)
                all_time_high_price_percentage = row.get("All-Time High Change Percentage (%)", 0)

                # Format price change
                if price_change is not None:
                    if price_change < 0:
                        price_change = f"-₹{abs(price_change):,.2f}"
                    else:
                        price_change = f"+₹{price_change:,.2f}"
                else:
                    price_change = "N/A"

                # Format market cap change
                try:
                    mc_prefix = "-" if market_cap_change < 0 else "+"
                    formatted_mc = f"{mc_prefix}₹{format_large_number(abs(market_cap_change * usd_to_inr))}"
                except Exception:
                    formatted_mc = "N/A"

                message = (
                    f"Coin Name: {coin_name}\n"
                    f"💰 Current Price: ₹{(current_price * usd_to_inr):,.2f}\n"
                    f"Market Cap: ₹{format_large_number(market_cap * usd_to_inr)} (Rank #{rank})\n"
                    f"24h High / Low: ₹{(high_price * usd_to_inr):.2f} / ₹{(low_price * usd_to_inr):.2f}\n"
                    f"24h Price Change: {price_change} ({price_change_percentage:.2f}%)\n"
                    f"24h Market Cap Change: {formatted_mc} ({market_cap_change_percentage:.2f}%)\n"
                    f"All-Time High (ATH): ₹{(all_time_high_price * usd_to_inr):.2f} (📉 {all_time_high_price_percentage}% from ATH)\n"
                )

                messages.append(message)
            return '\n'.join(messages)

        except Exception as e:
            print(f"❌ Error while generating messages: {e}")
            return f"⚠️ Error fetching best coin due to {e}. Try again later."

    except Exception as e:
        return f"⚠️ Error fetching best coin due to {e}. Try again later."

def get_market_trends():
    return "📊 Market Trend: Crypto market is showing bullish trends today!"

def get_crypto_news():
    return "📰 Crypto News: Bitcoin surges 5% after institutional investments increase!"

def handle_start(chat_id,user_name):
    # Caption styled like a UI post    
    caption = (
        f"👋 *Welcome {user_name} to the CryptoBot!*\n\n"
        "🔹 *Available Commands:*\n"
        "1️⃣ `/bestcoin` – Get the best coin recommendation\n"
        "2️⃣ `/trends` – See the latest market trends\n"
        "3️⃣ `/news` – Get the latest crypto news\n\n"
        "💬 *Chat with AI:* Just type any question!\n\n"
        "⚙️ Developed by [Ankit Kumar Sharma](https://ankit-sharma-07.netlify.app/) 🚀"
    )

    # Image to send (must be accessible publicly or use multipart/form upload)
    IMAGE_PATH = "https://img.favpng.com/24/9/12/vector-graphics-blockchain-computer-icons-logo-illustration-png-favpng-91s9EcZD7v8JqGgfdLZFfzWqb.jpg"  # Local path
    
    print(f"📩 Sending welcome post to chat ID: {chat_id}")
    send_telegram_post(chat_id, IMAGE_PATH, caption=caption)

def handle_message(chat_id, user_message, df=None, username=None, full_name=None):

    # Prevent spam: Limit the frequency of `/bestcoin` command
    if user_message == "/bestcoin":
        try:
            send_telegram_message(chat_id, "⏳ Please wait...")
            print(f"🔎 Fetching best coin for username: {username}")
            response = Coin_Updates(username=username)
            print(f"📩 Sending Best Coin Details to chat ID: {chat_id}")
            send_telegram_message(chat_id, response)
        except Exception as e:
            print(f"❌ Error in /bestcoin: {e}")
            send_telegram_message(chat_id, f"⚠️ Failed to get best coin. Error: {e}")
    
    elif user_message == "/trends":
        send_telegram_message(chat_id, "⏳ Please wait...")
        response = get_market_trends()
        print(f"📩 Sending Latest Market Trends to chat ID: {chat_id}")
        send_telegram_message(chat_id, response)
    
    elif user_message == "/news":
        send_telegram_message(chat_id, "⏳ Please wait...")
        response = get_crypto_news()
        print(f"📩 Sending Latest Crypto News to chat ID: {chat_id}")
        send_telegram_message(chat_id, response)

    elif user_message in ["hi", "hlo", "hello", "hey", "yo", "heyy"]:
        send_telegram_message(chat_id, f"👋 Hey {full_name}, how can I assist you today?")

    elif user_message in ["thanks", "thank you"]:
        send_telegram_message(chat_id, f"🙏 You're welcome! {full_name}")

    else:
        send_telegram_message(chat_id, "⏳ Please wait...")
        response = AI_Generated_Answer(user_message)  # AI response for other queries
        print(f"📩 Sending AI Response to chat ID: {chat_id}")
        send_telegram_message(chat_id, response)

def set_webhook():
    """Registers the Telegram webhook dynamically."""
    webhook_url = os.getenv("WEBHOOK_URL")  # Set this in .env
    if not webhook_url:
        print("❌ WEBHOOK_URL is missing from .env!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": webhook_url})
    
    if response.status_code == 200:
        print(f"✅ Webhook set successfully: {webhook_url}")
    else:
        print(f"❌ Webhook setup failed: {response.text}")
        
