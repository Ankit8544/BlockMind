import requests
from PIL import Image
from io import BytesIO

def generate_image(prompt, save_path = "generated_image.png"):
    try:
        # Construct the URL
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?nologo=true"
        
        # Fetch the image
        response = requests.get(url)
        response.raise_for_status()
        
        # Open and save the image
        image = Image.open(BytesIO(response.content))
        image.save(save_path)
        
        return save_path
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image: {e}")
        return ""

