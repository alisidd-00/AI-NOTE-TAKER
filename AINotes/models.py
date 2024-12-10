# from . import app
import pytz
from datetime import datetime, timedelta 
from AINotes import db, bcrypt
import secrets
from sqlalchemy import Boolean,Text, BigInteger
from AINotes import db, login_manager
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

TOKEN_EXPIRATION_TIME = timedelta(hours=1)
lahore_timezone = pytz.timezone('Asia/Karachi')

@login_manager.user_loader
def load_user(user_id):
    """
    Callback function for Flask-Login to load a user from the database.

    This function is used by Flask-Login to retrieve a User object for a given user ID.
    It attempts to query the User model by the user ID, handling cases where the ID is not
    a valid integer.

    Parameters:
    - user_id (str): The user ID passed from Flask-Login to identify the user.

    Returns:
    - User or None: The User object if found; otherwise, None if the ID is invalid or the user does not exist.
    """
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        # Handle the case where user_id is not a valid integer
        return None

########################################################################## User Table ############################################################################

class User(db.Model, UserMixin):
    """
    User model for application, with fields for authentication and password reset.

    Attributes:
    - id: Unique identifier for the user.
    - fname: First name of the user.
    - lname: Last name of the user.
    - email: Email address of the user, must be unique.
    - password: Hashed password for the user.
    - reset_token: Token for password reset, unique.
    - reset_token_expiration: Expiration date and time for the reset token.
    - email_token: Token for email verification, unique.
    - email_confirmed: Boolean indicating if the email has been confirmed.
    - email_token_expiration: Expiration date and time for the email token.
    - meetings: Relationship to meetings associated with the user.

    Methods:
    - generate_reset_token(): Generates a token for password reset.
    - is_reset_token_expired(): Checks if the reset token has expired.
    - reset_password(new_password): Resets the user's password.
    """
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone)) 
    updated_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone), onupdate=datetime.now(lahore_timezone))
    fname = db.Column(db.String(20), nullable=False)
    lname = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=True)

    zoom_access_token = db.Column(Text(length=2**32-1), nullable=True)
    zoom_refresh_token = db.Column(Text(length=2**32-1), nullable=True)
    zoom_token_expires_at = db.Column(db.DateTime, nullable=True)
    is_zoom_synced = db.Column(db.Boolean, default=False)

    google_access_token = db.Column(Text(length=2**32-1), nullable=True)
    google_refresh_token = db.Column(Text(length=2**32-1), nullable=True)
    google_token_expires_at = db.Column(db.DateTime, nullable=True)
    is_google_synced = db.Column(db.Boolean, default=False)

    reset_token = db.Column(db.String(32), unique=True, nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    email_token = db.Column(db.String(32), unique=True, nullable=True)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_token_expiration = db.Column(db.DateTime, nullable=True)
    
    meetings = db.relationship('Meeting', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.fname}', '{self.lname}', '{self.email}')"

    def generate_reset_token(self):
        # Generate a secure random token
        token = secrets.token_hex(16)

        # Set the reset token and expiration date
        self.reset_token = token
        self.reset_token_expiration = datetime.utcnow() + timedelta(minutes=5)

        db.session.commit()

    def is_reset_token_expired(self):
        if not self.reset_token_expiration:
            return True
        expired = datetime.utcnow() > self.reset_token_expiration
        return expired
        # return datetime.utcnow() > self.reset_token_expiration

    def reset_password(self, new_password):
        # Reset the user's password and clear the reset token
        self.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        self.reset_token = None
        self.reset_token_expiration = None
        db.session.commit()


######################################################### Meeting Table with Soft Delete Column ############################################

class Meeting(db.Model):
    """
    Meeting model for storing meeting details within application.

    Attributes:
    - id: Unique identifier for the meeting.
    - user_id: Foreign key linking to the user who created the meeting.
    - MID: Unique meeting ID provided by the meeting platform.
    - MTopic: Topic or title of the meeting.
    - MDate: Date and time when the meeting is scheduled.
    - Meeting_Link: URL link to join the meeting.
    - Passcode: Passcode required to join the meeting.
    - transcription: Relationship to transcriptions associated with the meeting.
    - deleted: Soft delete flag to indicate if the meeting has been "deleted."
    - source: Indicates the source of the meeting creation ('app' or 'external').

    Methods:
    - __repr__(): Provides a readable string representation of the meeting object.
    """
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone))
    updated_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone), onupdate=datetime.now(lahore_timezone))
    
    MID = db.Column(db.String(100), nullable=False)
    MTopic = db.Column(db.String(20), nullable=False)
    MDate = db.Column(db.DateTime, nullable=False, default=datetime.now(lahore_timezone))
    Meeting_Link = db.Column(db.String(1024), nullable=True)  # Add a new column for meeting link
    Passcode = db.Column(db.String(100), nullable=True)  # Add a new column for meeting passcode, 
    transcription = db.relationship('Transcription', backref='meeting', lazy=True)
    
    # New column for soft delete
    deleted = db.Column(Boolean, default=False)  # Assume 'False' means the record is not deleted

     # New column for meeting source
    source = db.Column(db.String(10), nullable=True, default='app')  # Values can be 'app' or 'external'
    
    def __repr__(self):
        return f"Meeting('{self.MID}', '{self.MTopic}', '{self.MDate.strftime('%Y/%m/%d %H:%M:%S')}', '{self.Meeting_Link}', '{self.Passcode}')"

############################################################ Transcription Table ###############################################################

class Transcription(db.Model):
    """
    Transcription model for storing detailed transcription information related to meetings.

    Attributes:
    - id: Unique identifier for the transcription.
    - meeting_id: linking to the associated meeting in other table.
    - user_id: Foreign key linking to the user associated with the transcription.
    - summary: Text summarizing the key points of the meeting.
    - action: Text detailing the action items identified in the meeting.
    - outline: Structured outline of the meeting content.
    - notes: Additional notes from the meeting.
    - diarization: Information on speaker diarization from the meeting audio.
    - audio: Path or identifier for the associated audio file.
    - keywords: Key terms extracted from the meeting content.

    Methods:
    - __repr__(): Provides a readable string representation of the transcription object.
    """
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime,  default=datetime.now(lahore_timezone))
    updated_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone), onupdate=datetime.now(lahore_timezone))
    meeting_id = db.Column(db.BigInteger, db.ForeignKey('meeting.id'), nullable=True)
    scheduled_meeting_id = db.Column(db.BigInteger, db.ForeignKey('scheduled_meeting.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meeting_date = db.Column(db.DateTime, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    action = db.Column(db.Text, nullable=True)
    diarization = db.Column(db.Text, nullable=True)
    audio = db.Column(db.String(1024), nullable=True)
    keywords=db.Column(db.String(1024), nullable=True)
    positive_percentage = db.Column(db.Float, nullable=True, default=0.0)
    negative_percentage = db.Column(db.Float, nullable=True, default=0.0)
    neutral_percentage = db.Column(db.Float, nullable=True, default=0.0)
    status = db.Column(db.String(240), default='pending', nullable=True)
    def __repr__(self):
        return f"Transcription('{self.summary}', '{self.action}', '{self.outline}', '{self.notes}', '{self.diarization}', '{self.audio}', '{self.keywords}','{self.positive_percentage}', '{self.negative_percentage}', '{self.neutral_percentage}')"



################################################################# Scheduled Meeting Table #######################################################################

class ScheduledMeeting(db.Model):
    """
    Model representing a scheduled meeting within an application, including metadata and access details.

    Attributes:
    - id: The primary key for the meeting record.
    - meeting_id: A unique identifier for the meeting, typically provided by an external service.
    - topic: The title or topic of the meeting.
    - start_time: The scheduled start time of the meeting.
    - timezone: The timezone in which the start time is specified.
    - meeting_link: A URL to access the meeting.
    - passcode: An optional passcode required for meeting access.
    - deleted: A flag indicating if the meeting record has been soft-deleted.
    - user_id: A foreign key linking the meeting to a user who scheduled it.
    - user: A relationship back to the User model, indicating who scheduled the meeting.

    Methods:
    - __repr__(): Provides a readable representation of the meeting for debugging.
    """
    id = db.Column(db.BigInteger, primary_key=True)
    created_at = db.Column(db.DateTime,  default=datetime.now(lahore_timezone))
    updated_at = db.Column(db.DateTime,  default=datetime.now(lahore_timezone), onupdate=datetime.now(lahore_timezone))
    meeting_id = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    timezone = db.Column(db.String(50), nullable=False)
    meeting_link = db.Column(db.String(1024), nullable=True)  # Add a new column for meeting link
    passcode = db.Column(db.String(100), nullable=True)  # Add a new column for meeting passcode, 
    deleted = db.Column(Boolean, default=False)  # Assume 'False' means the record is not deleted
    transcription = db.relationship('Transcription', backref='scheduled_meeting', lazy='dynamic')
    # Define the user_id as a foreign key to establish the relationship with User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Define the relationship to User (back reference)
    user = db.relationship('User', backref='scheduled_meetings', foreign_keys=[user_id])

    def __repr__(self):
        return f"ScheduledMeeting('{self.meeting_id}', '{self.topic}', '{self.start_time}', '{self.timezone}', '{self.meeting_link}', '{self.passcode}')"

#################################################### UPLOADED FILE TABLE ########################################

class FileUpload(db.Model):
    """
    Model for tracking file uploads in the system, associated with users and potential transcriptions.

    Attributes:
    - id: The primary key for the file upload record.
    - user_id: A foreign key linking the file upload to a user.
    - filename: The name of the uploaded file.
    - file_path: The path to the uploaded file on the server.
    - upload_time: The date and time when the file was uploaded.
    - deleted: A flag indicating if the file upload record has been soft-deleted.
    - transcriptions: A relationship to any transcriptions associated with this uploaded file.

    Methods:
    - __repr__(): Provides a readable representation of the file upload for debugging purposes.
    """
    __tablename__ = 'file_upload'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone))
    updated_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone), onupdate=datetime.now(lahore_timezone))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(1024), nullable=False)
    upload_time = db.Column(db.DateTime, nullable=False, default=datetime.now(lahore_timezone))
    deleted = db.Column(Boolean, default=False)  # Assume 'False' means the record is not deleted
    
    transcriptions = db.relationship('UploadedFileTranscription', back_populates='file_upload', lazy=True)


    def __repr__(self):
        return f"FileUpload('{self.filename}', '{self.file_path}', '{self.upload_time}')"

class UploadedFileTranscription(db.Model):
    """
    Model for storing transcription details of uploaded files.

    Attributes:
    - id: The primary key for the transcription record.
    - file_upload_id: A foreign key linking to the associated file upload.
    - created_at: The date and time when the transcription was created.
    - summary: A text summary of the transcription.
    - action: Action items identified in the transcription.
    - diarization: Speaker diarization information from the transcription.
    - audio: Path or identifier for the associated audio file.
    - keywords: Key terms or keywords extracted from the transcription.
    - file_upload: A relationship back to the FileUpload model.

    Methods:
    - __repr__(): Provides a readable string representation of the transcription object for debugging.
    """
    __tablename__ = 'uploaded_file_transcription'
    id = db.Column(db.Integer, primary_key=True)
    file_upload_id = db.Column(db.Integer, db.ForeignKey('file_upload.id'), nullable=False)  
    created_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone))
    updated_at = db.Column(db.DateTime, default=datetime.now(lahore_timezone), onupdate=datetime.now(lahore_timezone))

    summary = db.Column(db.Text, nullable=False)
    action = db.Column(db.Text, nullable=False)
    diarization = db.Column(db.Text, nullable=False)
    audio = db.Column(db.String(1024), nullable=False)
    keywords=db.Column(db.String(1024), nullable=True)
    positive_percentage = db.Column(db.Float, nullable=True, default=0.0)
    negative_percentage = db.Column(db.Float, nullable=True, default=0.0)
    neutral_percentage = db.Column(db.Float, nullable=True, default=0.0)

    file_upload = db.relationship('FileUpload', back_populates='transcriptions')

    def __repr__(self):
        return f"Transcription('{self.id}', '{self.file_upload_id}', '{self.created_at}', '{self.summary}', '{self.action}', '{self.outline}', '{self.notes}', '{self.diarization}', '{self.audio}', '{self.keywords}')"
