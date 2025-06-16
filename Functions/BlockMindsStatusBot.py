import os
import requests
from dotenv import load_dotenv
import time
start_time = time.time()

# Load environment variables
load_dotenv()

# Load API credentials
Status_TELEGRAM_BOT_TOKEN = os.getenv("Status_TELEGRAM_BOT_TOKEN")
Status_TELEGRAM_CHAT_ID = os.getenv("Status_TELEGRAM_CHAT_ID")

# https://api.telegram.org/bot7625246763:AAFO5qjmuEV-c1ZHkwT6KavpSegPqrG7xVg/getupdates

def send_status_message(chat_id, message):
    """Sends a message to a specific Telegram user."""
    try:
        url = f"https://api.telegram.org/bot{Status_TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram API Error: {e}")
        return {"error": str(e)}

