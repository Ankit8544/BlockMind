import requests
import pandas as pd
import json
import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Azure App credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET_VALUE = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANTID")
GRAPH_API_SCOPE = os.getenv("GRAPH_API_SCOPE")

# Imgur API credentials
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")

# Authenticate with Azure AD and get an access token
def get_access_token():

    # Token endpoint URL
    Token_Auth_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    # Request access token
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET_VALUE,
        'scope': GRAPH_API_SCOPE
    }
    
    Token_Auth_Response = requests.post(Token_Auth_URL, data=token_data)
    
    if Token_Auth_Response.status_code == 200:
        return Token_Auth_Response.json().get("access_token")
    else:
        raise Exception(f"Failed to get access token: {Token_Auth_Response.text}")

# Get the access token
access_token = get_access_token()
print("✅ Access token obtained successfully.")
print(f"Access Token: {access_token[:10]}...")  # Print only the first 10 characters for security

# Check if the access token is valid
if not access_token:
        raise Exception("Failed to get access token")
    
# Get User Data from User Principal Name using Microsoft Graph API
def get_user_detail(email):

    # URL for GET request to Microsoft Graph API
    Graph_API_User_Id_URL = f"https://graph.microsoft.com/v1.0/users/{email}"

    # Set headers for the request
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Send GET request
    Graph_API_User_Id_response = requests.get(Graph_API_User_Id_URL, headers=headers)

    # Check if the response is valid
    if Graph_API_User_Id_response.status_code == 200:

        # Parse the JSON response
        Graph_API_User_Id_response = json.loads(Graph_API_User_Id_response.text)
        
        # Extract the user ID
        user_id = Graph_API_User_Id_response.get("id")
        
        if not user_id:
            raise Exception("User ID not found in the response")
        
        # Get User Details using Microsoft Graph API
        Graph_API_User_Data_URL = f"https://graph.microsoft.com/beta/users/{user_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Send GET request to get user data
        Graph_API_User_Data_response = requests.get(Graph_API_User_Data_URL, headers=headers)
        
        # Check if the response is valid
        if Graph_API_User_Data_response.status_code == 200:

            # Parse the JSON response
            UserData = json.loads(Graph_API_User_Data_response.text)

            return UserData
        else:

            raise Exception(f"Failed to get user data: {Graph_API_User_Data_response.text}")
    else:

        raise Exception(f"Failed to get user ID: {Graph_API_User_Id_response.text}")

# Get User Profile Image from Microsoft Graph API
def get_user_profile_image(email):
    try:
        
        # Get User Data
        UserData = get_user_detail(email)
        
        # URL for GET request to Microsoft Graph API
        Graph_API_User_Profile_Image_URL = f"https://graph.microsoft.com/v1.0/users/{UserData.get('id')}/photo/$value"

        # Set headers for the request
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        # Send GET request to Microsoft Graph API
        response = requests.get(Graph_API_User_Profile_Image_URL, headers=headers)

        if response.status_code == 200:
            # Save the image to a file
            image_path = "profile_image.jpg"
            with open(image_path, "wb") as f:
                f.write(response.content)
            print("✅ Profile image downloaded successfully.")

            # Upload to Uploadcare
            your_public_key = "339349e37fa6fcbc472f"
            upload_url = "https://upload.uploadcare.com/base/"

            with open(image_path, 'rb') as file:
                upload_response = requests.post(
                    upload_url,
                    data={
                        "UPLOADCARE_PUB_KEY": your_public_key,
                        "UPLOADCARE_STORE": "1"
                    },
                    files={"file": file}
                )

            if upload_response.status_code == 200:
                file_id = upload_response.json()["file"]
                img_url = f"https://ucarecdn.com/{file_id}/-/scale_crop/300x300/"
                print(f"🔗 Image URL: {img_url}")
                return img_url
            else:
                print("❌ Upload to Uploadcare failed:", upload_response.status_code, upload_response.text)
                return None
        else:
            print("❌ Failed to download profile image:", response.status_code, response.text)
            return None

    except Exception as e:
        print("🚨 An error occurred:", str(e))
        return None

# Arrange User Data in a proper format
def user_metadata(cleaned_data):
    # Fetch user details and profile image
    UserData = get_user_detail(cleaned_data['user_mail'])
    UserProfileImage = get_user_profile_image(cleaned_data['user_mail'])
                    
    # Create a proper UserDetail dictionary
    UserDetail = {
        "User_id": UserData['id'] if 'id' in UserData else "N/A",
        "name":UserData['displayName'] if 'displayName' in UserData else "N/A",
        "mail_address":UserData['userPrincipalName'] if 'userPrincipalName' in UserData else cleaned_data['user_mail'],
        "image_url": UserProfileImage if UserProfileImage else "N/A",
        "job_title": UserData['jobTitle'] if 'jobTitle' in UserData else "N/A",
        "business_phones_number": UserData['businessPhones'] if 'businessPhones' in UserData else "N/A",
        "phone_number": UserData['mobilePhone'] if 'mobilePhone' in UserData else "N/A",
        "other_mail": UserData['otherMails'][0] if UserData['otherMails'] else "N/A",
        "address": UserData['streetAddress'] if 'streetAddress' in UserData else "N/A",
        "city": UserData['city'] if 'city' in UserData else "N/A",
        "state": UserData['state'] if 'state' in UserData else "N/A",
        "country": UserData['country'] if 'country' in UserData else "N/A",
        "postal_code": UserData['postalCode'] if 'postalCode' in UserData else "N/A",
        "preferred_language": UserData['preferredLanguage'] if 'preferredLanguage' in UserData else "N/A",
        "identity_provider": UserData['identities'][0]['issuer'] if UserData['identities'] else "N/A"
        }
    
    return UserDetail

