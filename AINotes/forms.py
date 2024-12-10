from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, DateTimeLocalField,TextAreaField,SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from AINotes.models import User
from pytz import all_timezones
import pytz
from datetime import datetime
class RegisterationForm(FlaskForm):
    """
    Form for user registration.

    Fields:
    - fname: First name of the user.
    - lname: Last name of the user.
    - email: Email address of the user.
    - password: Password for the user account.
    - confirmPassword: Confirmation for the password.
    - submit: Button to submit the form.

    Methods:
    - validate_email(email): Validates that the email is not already registered.
    """
    fname = StringField('First Name', validators=[DataRequired(), Length(min=3, max=20)])
    lname = StringField('Last Name', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmPassword = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_email(self, email):
        user = User.query.filter_by(email = email.data).first()
        if user:
            raise ValidationError('This email is already taken.')

class LoginForm(FlaskForm):
    """
    Form for user login.

    Fields:
    - email: The user's email address.
    - password: The user's password.
    - remember: Boolean to remember the user's session.
    - submit: Button to submit the form for login.
    """
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class InstantMeetingForm(FlaskForm):
    """
    Form for creating an instant meeting.

    Fields:
    - topic: The meeting topic, required with a minimum length of 3 and maximum of 50 characters.
    - agenda: The meeting agenda, optional.
    - duration: The meeting duration in minutes, required.
    - meetingID: The meeting ID, optional. Can be predefined or left blank for automatic generation.
    - meetingLink: The direct link to join the meeting, optional. Can be predefined or left blank for automatic generation.
    - submit: Button to submit the form and create the meeting.
    """
    topic = StringField('Topic', validators=[DataRequired(), Length(min=3, max=50)])
    agenda = StringField('Agenda')
    duration = IntegerField('Duration', validators=[DataRequired()])
    meetingID = StringField('Meeting ID')
    meetingLink = StringField('Meeting Link')
    submit = SubmitField('Create Meeting')


class PasswordResetRequestForm(FlaskForm):
    """
    Form for requesting a password reset.

    Fields:
    - email: The user's email address for which the password reset is requested.
    - submit: Button to submit the form and initiate the password reset process.
    """
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class PasswordResetForm(FlaskForm):
    """
    Form for setting a new password during the password reset process.

    Fields:
    - new_password: Field for entering the new password, required.
    - confirm_password: Field for confirming the new password, required. Must match the new password.
    - submit: Button to submit the form and apply the new password.
    """
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Reset Password')


# Select time zones specifically from major countries/regions and include UTC/GMT
# major_timezones = [
#     'UTC',              # Coordinated Universal Time
#     'GMT',              # Greenwich Mean Time
#     'Asia/Karachi',     # Pakistan
#     'Asia/Tokyo',       # Japan
#     'Asia/Shanghai',    # China
#     'Asia/Dubai',       # UAE
#     'Europe/London',    # UK
#     'Europe/Berlin',    # Germany
#     'Europe/Paris',     # France
#     'America/New_York',         # USA
#     'America/Los_Angeles',      # USA
#     'America/Toronto',          # Canada
#     'America/Mexico_City',      # Mexico
#     'Australia/Sydney',         # Australia
#     'Australia/Melbourne'       # Australia
# ]


# def get_timezone_offset(tz_name):
#     """Returns the current offset of the given timezone."""
#     tz = pytz.timezone(tz_name)
#     now = datetime.now(tz)
#     offset = now.utcoffset().total_seconds() / 3600
#     return offset

# Create timezone choices with offsets
# timezone_choices = [
#     (tz, f"{tz} (UTC{'+' if get_timezone_offset(tz) >= 0 else ''}{get_timezone_offset(tz):.0f}:{abs(get_timezone_offset(tz) % 1) * 60:02.0f})")
#     for tz in major_timezones
# ]

timezone_choices = [(tz, tz) for tz in all_timezones]


def validate_future_date(form, field):
    if field.data < datetime.now():
        raise ValidationError("Please select a future date and time for the meeting.")

# # Create timezone choices with offsets
# timezone_choices = [
#     (tz, f"{tz} (UTC{'+' if get_timezone_offset(tz) >= 0 else ''}{get_timezone_offset(tz):.0f}:{abs(get_timezone_offset(tz) % 1) * 60:02.0f})")
#     for tz in major_timezones
# ]
timezone_choices = [(tz, tz) for tz in all_timezones]
def validate_future_date(form, field):
    if field.data < datetime.now():
        raise ValidationError("Please select a future date and time for the meeting.")

class ScheduledMeetingForm(FlaskForm):
    """
    Form for scheduling a new meeting.

    Fields:
    - topic: The meeting topic, required with a minimum length of 3 and a maximum of 50 characters.
    - agenda: The detailed agenda or description of the meeting, optional.
    - start_time: The scheduled start date and time of the meeting, required. Uses local datetime format.
    - duration: Dropdown to select the meeting duration, with predefined options in minutes, required.
    - timezone: Dropdown to select the timezone for the meeting start time, required.
    - submit: Button to submit the form and schedule the meeting.
    """
    topic = StringField('Topic', validators=[DataRequired(),Length(min=3, max=50)])
    agenda = TextAreaField('Agenda')
    start_time = DateTimeLocalField('Schedule Date and Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired(), validate_future_date])
    duration = SelectField('Select Duration', choices=[('', 'Select Duration'), ('15', '15 mins'), ('30', '30 mins'), ('45', '45 mins'), ('60', '60 mins')], validators=[DataRequired()], default='')
    timezone = SelectField('Timezone', choices=timezone_choices, validators=[DataRequired()], default='Asia/Karachi')
    submit = SubmitField('Schedule Meeting')



class MeetingForm(FlaskForm):
    """
    Form for entering meeting information to create config file for bot to join meeting.

    Fields:
    - meeting_id: Meeting Number of the meeting.
    - passcode: Password of the meeting.
    - submit: Button to submit the form and schedule the meeting.
    """
    meeting_id = StringField('Meeting ID', validators=[DataRequired()])
    passcode = StringField('Passcode', validators=[DataRequired()])
    submit = SubmitField('Join Meeting')