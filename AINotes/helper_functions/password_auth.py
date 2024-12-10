import re
import secrets
from flask_mail import Message
from .. import mail
from flask import url_for


def check_password_complexity(password):
    if len(password) < 8:
        return False

    # Check for the presence of uppercase letters
    if not re.search(r'[A-Z]', password):
        return False

    # Check for the presence of lowercase letters
    if not re.search(r'[a-z]', password):
        return False

    # Check for the presence of digits
    if not re.search(r'[0-9]', password):
        return False

    # Check for the presence of special characters
    if not re.search(r'[\W_]', password):  # \W matches any non-word character, _ is included to consider underscore as a special character
        return False

    return True


def generate_unique_token():
    return secrets.token_hex(16) 

def send_password_reset_email(email, reset_token):
    # Create a message object with the reset token
    message = Message('Password Reset', sender='info@ashlarglobal.biz', recipients=[email])
    reset_url = url_for('reset_password', token=reset_token, _external=True)
    message.body = f'Click the following link to reset your password: {reset_url}. This is a one time token. '

    # Send the email
    mail.send(message)