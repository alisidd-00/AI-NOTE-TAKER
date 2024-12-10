from AINotes import app,celery
import logging
import os
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

log_file_path = os.getenv('LOG_FILE')
logging.basicConfig(filename=log_file_path, filemode='a', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.info("Starting application")

if __name__ == "__main__":
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    app.run('localhost',5000, debug=True)
    
        