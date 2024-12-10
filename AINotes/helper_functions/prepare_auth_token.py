from AINotes.helper_functions.zoom_integration import refresh_zoom_token
from AINotes import db
from pytz import datetime
from datetime import timedelta,datetime
import logging
import os
from dotenv import load_dotenv

load_dotenv()

log_file_path = os.getenv('LOG_FILE')
logging.basicConfig(filename=log_file_path, filemode='a', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')



def prepare_auth_token(user):
    if datetime.now() < user.zoom_token_expires_at:
        logging.info(user)
        logging.info('token is still valid')
        return 'Bearer ' + user.zoom_access_token
    
    logging.info('token was expired, going to renew')
    refreshed_token = refresh_zoom_token(user.zoom_refresh_token)
    if refreshed_token:
        user.zoom_access_token = refreshed_token['access_token']
        user.zoom_refresh_token = refreshed_token['refresh_token']
        expires_in = refreshed_token.get('expires_in', 3600)
        if expires_in is None:
            expires_in = 3600  # Default to 1 hour if expires_in is None
        user.zoom_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        logging.info('token expiry is')
        logging.info(user.zoom_token_expires_at)
        db.session.commit()
        return 'Bearer ' + user.zoom_access_token
    else:
        raise Exception('Failed to refresh token')
