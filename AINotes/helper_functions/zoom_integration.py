import os
import requests
from dotenv import load_dotenv
import base64
import logging

load_dotenv()

log_file_path = os.getenv('LOG_FILE')
logging.basicConfig(filename=log_file_path, filemode='a', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def refresh_zoom_token(refresh_token):

    client_id = os.getenv('ZOOM_CLIENT_ID')
    client_secret = os.getenv('ZOOM_CLIENT_SECRET')
    refresh_url = "https://zoom.us/oauth/token"
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    headers = {
        'Authorization': f'Basic {encoded_credentials}'
    }
    try:
        response = requests.post(refresh_url, headers=headers, data=payload)
        logging.info('response:  %s',response)
        response.raise_for_status()
        # The JSON response contains access_token, refresh_token, and expires_in (seconds)
        tokens = response.json()
        logging.info(tokens)
        if tokens.get('access_token'):
            return {
                'access_token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),  # Zoom might return a new refresh token
                'expires_in': tokens.get('expires_in')
            }
        else:
            return None
    except requests.RequestException as e:
        logging.error('HTTP Request failed: %s', str(e))
        logging.error('Response received: %s', response.text)  # Log the full response text
        return None