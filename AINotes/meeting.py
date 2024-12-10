import json
import time
import requests
import webbrowser
import pytz
from flask import session
#======================================================================================================================================#

meeting_topic = ""
meeting_agenda = ""
meeting_duration = 0
startTime = ""
timeZone = ""
type = 1

settings = {
            "allow_multiple_devices": True,
            "approval_type": 2,
            "audio": "both",
            "audio_conference_info": "test",
            #"auto_recording": "local",
            "calendar_type": 2,
            "close_registration": False,
            "encryption_type": "enhanced_encryption",
            "focus_mode": False,
            "host_video": False,
            "jbh_time": 0,
            "join_before_host": True,
            # "meeting_authentication": True,
            "mute_upon_entry": True,
            "participant_video": False,
            "use_pmi": False,
            "waiting_room": False,
            "host_save_video_order": True,
            "alternative_host_update_polls": True,
            "default_password":True
        }

#======================================================================================================================================#

def S2S_Auth():
    """
    Retrieves an access token for Zoom API using server-to-server OAuth.

    Returns:
    - str: The access token.
    """
    url = "https://zoom.us/oauth/token"
    headers = {
        'Authorization': 'Basic WEI5dlRKc0tSaWhmS3ZIWEpCVEE6WUFkVHYyVXZUa203MFZwcWR0M09IQU1oNkNOV0g1SXE='}
    data = {'grant_type': 'account_credentials',
            'account_id': 'aGYV8_0aROqkgtwgc72olw'}
    response = requests.post(url, headers=headers, params=data)

    data = json.loads(response.text)
    Token = data["access_token"]
    return Token

##################################### Function to Create Meeting##############################################

def createmeetingS2S(auth_token, meeting_topic, meeting_agenda, meeting_duration):
    """
    Creates a Zoom meeting with specified parameters using server-to-server OAuth.

    Parameters:
    - auth_token (str): Authorization token for API access.
    - meeting_topic (str): Title of the meeting.
    - meeting_agenda (str): Agenda or description of the meeting.
    - meeting_duration (int): Duration of the meeting in minutes.

    Returns:
    - dict: Data about the created meeting.
    """
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {'Content-Type': 'application/json', 'Authorization': auth_token}

    payload = json.dumps({
        "topic": meeting_topic,
        "agenda": meeting_agenda,
        "default_password": True,
        "duration": meeting_duration,
        "pre_schedule": False,
        "type": 1,
        "settings":settings,  # existing settings
        "template_id": "Dv4YdINdTk+Z5RToadh5ug=="
    })
    response = requests.request("POST", url, headers=headers, data=payload)
    meetingData = json.loads(response.text)
    return meetingData

def create_meeting(auth_token, meeting_topic, meeting_agenda, meeting_duration):
    """
    Creates a new scheduled Zoom meeting with the provided details.

    This function sends a request to the Zoom API to create a meeting. It handles
    successful responses by returning meeting data and raises an exception for
    unsuccessful requests.

    Parameters:
    - auth_token (str): The authorization token to authenticate with the Zoom API.
    - meeting_topic (str): The title of the meeting.
    - meeting_agenda (str): The agenda or description of the meeting.
    - meeting_duration (int): The duration of the meeting in minutes.

    Returns:
    - dict: A dictionary containing the details of the created meeting on success.

    Raises:
    - Exception: If the API request does not succeed.
    """
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {'Authorization': auth_token, 'Content-Type': 'application/json'}

    payload = json.dumps({
        "topic": meeting_topic,
        "agenda": meeting_agenda,
        "default_password": True,
        "type": 1,  # Instant meeting
        "duration": meeting_duration,
        "settings": settings,
    })

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code in (200, 201):
        meeting_data = response.json()
        return meeting_data
    
    if response.status_code != 200:
        raise Exception(f"Zoom API request failed with status code {response.status_code}: {response.text}")

##################################################################################################################################
def scheduled_meeting(auth_token, meeting_topic, meeting_agenda, meeting_duration, start_time, timezone):
    """
    Creates a scheduled Zoom meeting with detailed configurations including start time and timezone.

    Parameters:
    - auth_token (str): The authorization token for Zoom API access.
    - meeting_topic (str): Title of the meeting.
    - meeting_agenda (str): Detailed agenda or description of the meeting.
    - meeting_duration (int): Duration of the meeting in minutes.
    - start_time (datetime): The start time of the meeting. Should be a timezone-aware datetime object.
    - timezone (str): The timezone of the meeting start time.

    Returns:
    - dict: A dictionary containing the created meeting details on success.
    """
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {'Content-Type': 'application/json', 'Authorization': auth_token}

    desired_timezone = pytz.timezone(timezone)
    start_time = desired_timezone.localize(start_time)
    start_time_utc = start_time.astimezone(pytz.UTC)


    # Convert the start_time to ISO 8601 format with the specified timezone
    start_time_iso = start_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    payload = json.dumps({
        "topic": meeting_topic,
        "agenda": meeting_agenda,
        "default_password": True,
        "duration": meeting_duration,
        "pre_schedule": False,
        "type": 2,  # Scheduled Meeting
        "start_time": start_time_iso,  # Schedule start time in ISO 8601 format
        "timezone": timezone,  # Set the timezone
        "settings": settings,
        "template_id": "Dv4YdINdTk+Z5RToadh5ug=="  # Replace with your template_id if needed
    })

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code in (200, 201):
        meeting_data = json.loads(response.text)
        meeting_data = response.json()
        return meeting_data

##########################################################################################

def end_meeting(meeting_id, auth_token):
    """
    Ends an ongoing Zoom meeting specified by the meeting ID.

    Parameters:
    - meeting_id (str): The unique ID of the Zoom meeting to end.
    - auth_token (str): The bearer token for authorization with the Zoom API.

    Returns:
    - str: A message indicating the outcome of the operation.
    """
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/status"
    headers = {
        'Authorization': f"Bearer {auth_token}",
        'Content-Type': 'application/json'
    }
    data = {
        'action': 'end'
    }
    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 204:
        return f"Meeting {meeting_id} has been successfully ended."
    else:
        return f"Failed to end meeting {meeting_id}. Error: {response.text}"
    
#################################################################################

