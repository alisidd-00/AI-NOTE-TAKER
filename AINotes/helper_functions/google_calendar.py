from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
from datetime import timedelta,datetime
from pytz import timezone
import logging
from dotenv import load_dotenv
import requests
from AINotes import db

load_dotenv()

log_file_path = os.getenv('LOG_FILE')
logging.basicConfig(filename=log_file_path, filemode='a', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def create_google_calendar_event(user, meeting_details):
    """Create an event in the user's Google Calendar."""
    # Always refresh the token
    if not refresh_google_token(user):
        raise Exception("Failed to refresh Google access token.")
    
    # Extracting necessary details
    event_topic = meeting_details['topic']
    join_url = meeting_details['join_url']
    meeting_id = meeting_details['meeting_id']
    passcode = meeting_details['passcode']
    start_time = meeting_details['start_time']
    duration = meeting_details['duration']
    event_timezone = meeting_details.get('timezone', 'Asia/Karachi')  # Default to Asia/Karachi if no timezone is provided

    # Adjust the timezone
    tz = timezone(event_timezone)
    if start_time.tzinfo is None:
        start_time_aware = tz.localize(start_time)
    else:
        start_time_aware = start_time.astimezone(tz)
    
    end_time_aware = start_time_aware + timedelta(minutes=duration)

    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET')
    )
    service = build('calendar', 'v3', credentials=creds)
    event = {
        'summary': event_topic,
        'location': 'Online Meeting',
        'description': f"Join URL: {join_url}\nMeeting ID : {meeting_id}\nPasscode: {passcode}",
        'start': {
            'dateTime': start_time_aware.isoformat(),
            'timeZone': event_timezone,
        },
        'end': {
            'dateTime': end_time_aware.isoformat(),
            'timeZone': event_timezone,
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event['htmlLink']

def refresh_google_token(user):
    """Refresh the Google access token using the refresh token."""
    refresh_url = 'https://oauth2.googleapis.com/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
        'refresh_token': user.google_refresh_token,
        'grant_type': 'refresh_token',
    }
    response = requests.post(refresh_url, headers=headers, data=data)
    token_info = response.json()

    if response.status_code == 200 and 'access_token' in token_info:
        user.google_access_token = token_info['access_token']
        user.google_token_expires_at = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
        db.session.commit()
        logging.info(f'Google access token refreshed successfully for user {user.id}')
        return True
    else:
        logging.error(f'Failed to refresh Google access token for user {user.id}: {token_info}')
        return False


def refresh_if_expired(user):
    if user.google_token_expires_at is None or datetime.utcnow() >= user.google_token_expires_at:
        logging.info(f'Token expired or not set, refreshing token for user {user.id}')
        return refresh_google_token(user)
    return True
