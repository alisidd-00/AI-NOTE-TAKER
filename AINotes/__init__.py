from flask import Flask,session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from flask_cors import CORS, cross_origin
from celery import Celery
import sentry_sdk

load_dotenv()

app = Flask(__name__, template_folder='templateFiles', static_folder='staticFiles')
csrf = CSRFProtect(app)
csrf.init_app(app)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['MAIL_DEBUG'] = os.getenv('MAIL_DEBUG') == 'True'
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = (os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
app.config['ZOOM_CLIENT_ID'] = os.getenv('ZOOM_CLIENT_ID')
app.config['ZOOM_CLIENT_SECRET'] = os.getenv('ZOOM_CLIENT_SECRET')
app.config['WTF_CSRF_ENABLED'] = False
app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND')
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1 Gigabyte


sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)


# Flask app configuration
app.config.update(
    SERVER_NAME=os.getenv('SERVER_NAME'),
    APPLICATION_ROOT='/',
    PREFERRED_URL_SCHEME='https'
)



db = SQLAlchemy(app)  # Initialize db after creating the app instance
bcrypt = Bcrypt(app)  # Initialize bcrypt after creating the app instance
mail = Mail(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app) # Initialize login manager after creating the app instance
login_manager.login_view = 'login' # Set the login view to the login route function name
login_manager.login_message_category = 'info' # Set the login message category to info


# OAuth configuration for OAuth App
zoom_oauth = OAuth(app)

def zoom_login():
    """
    Registers the Zoom OAuth client with the application using credentials and URIs defined in environment variables.

    Utilizes the OAuth2 consumer application credentials (client ID and client secret) along with
    the authorization, access token URLs, and redirect URI to register the Zoom OAuth client.
    This enables OAuth2 authentication and authorization for accessing the Zoom API with
    specific scopes for reading and writing meetings.

    Note: Ensure that ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, and REDIRECT_URI environment variables are correctly set.
    """
    zoom_oauth.register(
    name='zoom',
    client_id=os.getenv('ZOOM_CLIENT_ID'),
    client_secret=os.getenv('ZOOM_CLIENT_SECRET'),
    authorize_url='https://zoom.us/oauth/authorize',
    access_token_url='https://zoom.us/oauth/token',
    refresh_token_url=None,
    redirect_uri=os.getenv('REDIRECT_URI'),  # Make sure this matches the URI in Zoom App Marketplace
    client_kwargs={'scope': 'meeting:write meeting_token:read:local_recording user:read user_zak:read'},
)

zoom_login()


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)
from AINotes import routes