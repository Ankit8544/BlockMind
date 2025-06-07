from dotenv import load_dotenv
import os
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Google Gemini API credentials
GEMINI_API_KEYS = [
    (os.getenv("ankitkumar875740")),
    (os.getenv("kingoflovee56")), 
    (os.getenv("bloodycrewff"))
    ]

# Get Valid Gemini API Key
def get_valid_api_key():
    for key in GEMINI_API_KEYS:
        try:
            genai.configure(api_key=key)
            genai.GenerativeModel('gemini-1.5-pro')  # Only configures the model without generating content
            return key
        except Exception as e:
            print(f"API key {key} failed: {e}")
    return None

# Get a valid Gemini API key
GEMINI_API_KEY = get_valid_api_key()

# Check if a valid API key was found
if not GEMINI_API_KEY:
    raise Exception("No valid Gemini API key found.")

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

# Generate Twitter Post 
def AI_Generated_Tweets(df):
    prompt = f"""
    Generate a **meme-style viral Twitter post** based on the given **Stable Meme Coin** data. The tweet must:  

    😂 Be **hilarious, sarcastic, or witty**—designed to go viral.  
    📊 Include key metrics in a **clever and engaging way**.  
    📉📈 Reflect the coin’s **market trend** with a strong narrative.  
    💎 Be **short, punchy, and focused on the best coin only**.  
    🚀 Use **relevant emojis and hashtags** for maximum reach.  
    🐶 Incorporate **meme-style language & phrases** specific to the coin (e.g., "Much wow" for Dogecoin).  
    🕵️ Add section **[Attach Image:]** which contain detailed image prompt that alings with the post   
        - **Style:** Meme-like, humorous, and visually striking.  
        - **Theme:** Relates to the coin’s performance.  
        - **Elements:** Includes iconic meme characters (e.g., Wojak, Pepe, Doge) **reacting to the market trend**.  
        - **Text Overlay:** Must complement the tweet and reinforce the meme's joke.  
        - **Emotion:** Over-exaggerated expressions to amplify humor. 

    🔹 **Strictly return only the final formatted tweet and image prompt section**—no explanations, no extra text, just the **ready-to-post content** optimized for engagement.   

    Here is the data: {df.iloc[0]}  
    """

    gemini_result = Gemini(prompt)
    
    try:
        result = gemini_result.replace('*', '')
        return result
    except:
        print("⚠️ Unfortunatly, We are not able responed you right now.")
        return "🚫 AI is currently unavailable. Try again later."

def AI_Generated_Answer(user_message):
    gemini_result = Gemini(user_message)
    
    try:
        result = gemini_result.replace('*', '')
        return result
    except:
        print("⚠️ Unfortunatly, We are not able responed you right now.")
        return "🚫 AI is currently unavailable. Try again later."



