from flask import Flask, redirect, url_for, session
from functools import wraps
from flask_login import current_user

def redirect_if_logged_in(f):
    """Decorator to redirect logged in users from the login page."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def redirect_if_zoom_logged_in(f):
    """Decorator to redirect users logged in via Zoom from certain pages."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_zoom_oauth'):
            return redirect(url_for('home'))  # Assuming 'home' is the route where logged-in users should go
        return f(*args, **kwargs)
    return decorated_function