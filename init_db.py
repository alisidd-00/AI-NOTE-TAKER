from AINotes import app, db
from AINotes.models import User, Meeting, Transcription,ScheduledMeeting
import json
from sqlalchemy import inspect

with app.app_context():
    # print('database created')
    db.create_all()
