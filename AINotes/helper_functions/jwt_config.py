import jwt
import time
import os

from dotenv import load_dotenv

load_dotenv()


def generate_jwt():
    client_id = os.getenv('ZOOM_SDK_KEY')
    client_secret = os.getenv('ZOOM_SDK_SECRET')

    # Define token expiration times
    iat = int(time.time())
    exp = iat + 3600  # Token valid for 2 hours

    # Create JWT payload
    payload = {
        'appKey': client_id,
        'iat': iat,
        'exp': exp,
        'tokenExp': exp
    }

    signature = jwt.encode(payload, client_secret, algorithm='HS256')

    return signature


# def generate_config_file(meeting_id, password, user_id, signature, join_token):
#     config_filename = f"config.txt"
#     config_dir = os.getenv('CONFIG_FILE')  # Directory containing all user-specific config files
#     user_config_dir = os.path.join(config_dir, user_id)  # Directory specific to each user
#     config_path = os.path.join(user_config_dir, config_filename)
#     print('join token', join_token)
#     # Create the directory if it doesn't exist
#     os.makedirs(user_config_dir, exist_ok=True)

#     if os.path.isdir(config_path):
#         return None 

#     # Generate the config content
#     config_content = f"""\
# meeting_number: "{meeting_id}"
# token: "{signature}"
# meeting_password: "{password}"
# recording_token: "{join_token}"
# GetAudioRawData: "true"
# SendVideoRawData: "true"
# SendAudioRawData: "true"
# """

#     # Write the config content to the file
#     with open(os.path.join(user_config_dir, "config.txt"), 'w') as config_file:
#         config_file.write(config_content)

#     return config_path  

def generate_config_file(meeting_id, password, user_id, signature, join_token):
    config_filename = "config.txt"
    config_dir = os.getenv('CONFIG_FILE')  # Directory containing all user-specific config files
    user_config_dir = os.path.join(config_dir, user_id)  # Directory specific to each user
    config_path = os.path.join(user_config_dir, config_filename)

    # Create the directory if it doesn't exist
    os.makedirs(user_config_dir, exist_ok=True)

    # If there's already a directory, we might not want to overwrite it, but let's return None for safety.
    if os.path.isdir(config_path):
        return None

    # Generate the config content, including all fields by default
    config_lines = [
        f'meeting_number: "{meeting_id}"',
        f'token: "{signature}"',
        f'meeting_password: "{password}"'
    ]

    # Include recording_token right after meeting_password
    recording_token_line = f'recording_token: "{join_token}"' if join_token else 'recording_token: ""'
    config_lines.append(recording_token_line)

    # Append the remaining configuration settings
    config_lines += [
        'GetAudioRawData: "true"',
        'SendVideoRawData: "true"',
        'SendAudioRawData: "true"'
    ]

    # Join the config lines into a single string
    config_content = "\n".join(config_lines)

    # Write the configuration to the file
    with open(config_path, 'w') as config_file:
        config_file.write(config_content)

    return config_path
