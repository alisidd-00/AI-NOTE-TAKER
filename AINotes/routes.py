import os
import json
import pandas as pd
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, session, redirect, url_for, flash, send_file
from markupsafe import Markup
from AINotes import app, db, bcrypt,zoom_oauth, celery
from AINotes.forms import RegisterationForm, LoginForm, InstantMeetingForm,PasswordResetRequestForm,PasswordResetForm,ScheduledMeetingForm,MeetingForm
from AINotes.models import User, Meeting, Transcription,ScheduledMeeting,FileUpload,UploadedFileTranscription
from flask_login import login_user, current_user, logout_user, login_required
from AINotes.meeting import S2S_Auth, create_meeting, end_meeting,scheduled_meeting,createmeetingS2S
from AINotes.decorators import redirect_if_logged_in,redirect_if_zoom_logged_in
from AINotes.transc import get_audio_path_by_meeting_id, convert_video_to_audio,pcm_to_wav_ffmpeg,run_diarization,parse_diarization_file,process_audio_file,transcribe_segments,pipeline,model,process_transcription,folder_path,analyze_sentiments,is_audio_mostly_silent
from AINotes.openai import get_chatbot_response
from AINotes.helper_functions.google_calendar import create_google_calendar_event
from AINotes.helper_functions.docker_funcs import build_docker_image,run_docker_container, send_transcription_email
from AINotes.helper_functions.jwt_config import generate_jwt,generate_config_file
from AINotes.helper_functions.password_auth import check_password_complexity,generate_unique_token,send_password_reset_email
from AINotes.helper_functions.prepare_auth_token import prepare_auth_token
import re
from flask_mail import Message
from . import mail
from werkzeug.utils import secure_filename
from authlib.common.security import generate_token
from flask_login import current_user, login_required
from flask_bcrypt import generate_password_hash
import requests
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from requests.auth import HTTPBasicAuth
from uuid import uuid4
from pytz import timezone
import pytz
import shutil
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from sqlalchemy import desc
from bs4 import BeautifulSoup 



log_file_path = os.getenv('LOG_FILE')
logging.basicConfig(filename=log_file_path, filemode='a', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
scheduler = BackgroundScheduler(jobstores=jobstores)
logging.info(f'scheduler: {scheduler}')
scheduler.start()
logging.info("Scheduler started!")

load_dotenv()

path_file = os.getenv('PATH-FILE')
path = os.getenv('PATH')


@app.route("/error")
def hello_world():
    1/0  # raises an error
    return "<p>Hello, World!</p>"

@app.route("/")
@app.route("/main")
#@redirect_if_logged_in
@redirect_if_zoom_logged_in
def main():
    messagee = session.pop('flash', None)
    return render_template("main.html", messagee=messagee)

# =============================================================  Login ======================================================================================================#

# @app.route("/login", methods=["GET", "POST"])
# @redirect_if_logged_in
# def login():
#     if current_user.is_authenticated:
#         # Redirect them to the home page as they are already logged in
#         return redirect(url_for('home'))
    
#     message = session.pop('flash', None)
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         if user and bcrypt.check_password_hash(user.password, form.password.data):
#             if user.email_confirmed:
#                 # User's email is confirmed; log them in
#                 login_user(user, remember=form.remember.data)  # Log the user in
#                 session['flash']=f"Login successful."
#                 return redirect(url_for('home'))  # Redirect to authenticated part of your application
#             else:
#                 flash("Please confirm your email address before logging in.", "warning")
#         else:
#             flash("Incorrect Email or Password", "danger")
#     return render_template("login.html", form=form,message=message)


@app.route("/logout")
def logout():
     session['flash'] = f'You have logged out!'  # Store flash message in session
     logout_user()
     session.pop('zoom_access_token', None)
     session.pop('is_zoom_oauth', None)
     session.clear()
     return redirect(url_for('main'))

#============================================================================= Home Route=============== =============================================================================#

@app.route("/home")
@login_required
def home():
    message = session.pop('flash', None)
    current_time = datetime.now()  # Get the current datetime
    upcoming_meetings = get_upcoming_meetings(current_user)
    session['user_id'] = current_user.get_id()
    return render_template('home.html', upcoming_meetings=upcoming_meetings, message=message, now=current_time,user_id=current_user.get_id())

@app.route("/account")
@login_required
def account():
    return render_template("account.html")

@app.route("/uploads")
@login_required
def uploads():
    return render_template("uploads.html")

#========================================================================== Meeting Routes ===========================================================================================#

@app.route("/meetings")
@login_required
def meetings():
    form = InstantMeetingForm()
    sform=ScheduledMeetingForm()
    topic = request.args.get('topic')
    agenda = request.args.get('agenda')
    duration = request.args.get('duration')
    join_URL = session.get('join_URL')
    meeting_id = session.get('meeting_id')
    return render_template("meetings.html", form = form, topic=topic, agenda=agenda, duration=duration, meeting_id=meeting_id, join_URL=join_URL,sform=sform)

@app.route('/meetings/instant', methods=["GET", "POST"])
@login_required
def instant_meeting():
    form = InstantMeetingForm()
    meeting_id = None  # Assign a default value
    join_URL = None  # Assign a default value
    if form.validate_on_submit():
        user = User.query.get(current_user.id)
        email = current_user.email

        topic = form.topic.data
        agenda = form.agenda.data
        duration = form.duration.data
        start_time = datetime.now(pytz.utc)
        is_zoom_oauth = session.get('is_zoom_oauth', False)

        # Always refresh the Zoom token
        try:
            auth_token = prepare_auth_token(user)
            if auth_token is None:
                flash('Please sync your zoom accoun to be able to create a meeting','error')
                raise Exception('Failed to prepare authentication token.')
        except Exception as e:
            error_message = str(e)
            response_data = {
                'success': False,
                'error_message': error_message,
            }
            return jsonify(response_data), 500


        try:
            create_meeting_function = create_meeting
            meeting_data = create_meeting_function(auth_token, topic, agenda, duration)
            meeting_id = meeting_data.get('id')
            join_URL = meeting_data.get('join_url')
            passcode = meeting_data.get('password')
            date = datetime.now()

            # Storing meeting information in session
            session['meeting_id'] = meeting_id
            session['join_URL'] = join_URL

            new_meeting = Meeting(user_id=str(user.id), MID=meeting_id, MTopic=topic, MDate=date, Meeting_Link=join_URL, Passcode=passcode)
            db.session.add(new_meeting)
            db.session.commit()

            meeting_datetime = new_meeting.MDate
            # start_time = datetime.now(pytz.utc)  # Start 30 seconds from now to avoid immediate execution issues
            start_time = start_time
            logging.info(f'start_time {start_time}')
            user = User.query.get(current_user.id)
            scheduler.add_job(join_meeting_bot, 'date', run_date=start_time, args=[meeting_id, passcode, user, str(user.id), meeting_datetime, email])
            logging.info('scheduler job added')

            meeting_details = {
                'topic': topic,
                'join_url': join_URL,
                'meeting_id': meeting_id,
                'passcode': passcode,
                'start_time': start_time,
                'duration': duration,
                'timezone': 'Asia/Karachi',  # Default to Asia/Karachi for instant meetings
            }

            try:
                calendar_link = create_google_calendar_event(user, meeting_details)
                logging.info('Google Calendar event created successfully')
                response_data = {
                'success': True,
                'meeting_id': meeting_id,
                'join_URL': join_URL,
                'passcode' : passcode,
                'calendar_link': calendar_link
            }
            except Exception as e:
                logging.error(f'Failed to create Google Calendar event: {e}')
                response_data = {
                'success': True,
                'meeting_id': meeting_id,
                'join_URL': join_URL,
                'passcode' : passcode,
                'calendar_link': 'not synced with google'
            }

            return jsonify(response_data), 200
        except Exception as e:
            error_message = str(e)
            response_data = {
                'success': False,
                'error_message': error_message,
            }
            return jsonify(response_data), 500

    # If form validation fails, return an error response
    error_messages = [str(error) for error in form.errors.values()]
    response_data = {
        'success': False,
        'error_messages': error_messages,
    }
    return jsonify(response_data), 400



@app.route('/schedule-meeting', methods=["GET", "POST"])
@login_required
def schedule_meeting():
    sform = ScheduledMeetingForm()
    upcoming_meetings = None  # Assign a default value
    user_id = str(current_user.id)
    if sform.validate_on_submit():
        user = User.query.get(current_user.id)
        email=current_user.email

        topic = sform.topic.data
        agenda = sform.agenda.data
        duration = int(sform.duration.data)  # Convert duration to int
        start_time = sform.start_time.data
        timezone = sform.timezone.data

        # Check if user logged in via Zoom OAuth
        is_zoom_oauth = session.get('is_zoom_oauth', False)

        # auth_token = prepare_auth_token(current_user)

        try:
            auth_token = prepare_auth_token(user)
            if auth_token is None:
                flash('Please sync your zoom account to be able to create a meeting','error')
                raise Exception('Failed to prepare authentication token.')
        except Exception as e:
            error_message = str(e)
            response_data = {
                'success': False,
                'error_message': error_message,
            }
            return jsonify(response_data), 500
        

        upcoming_meetings = get_upcoming_meetings(current_user)

        try:
            # Create the meeting and get the meeting_data using the appropriate function
            create_meeting_function = scheduled_meeting 
            meeting_data = create_meeting_function(auth_token, topic, agenda, duration, start_time, timezone)

            meeting_id = meeting_data.get('id')
            join_URL = meeting_data.get('join_url')
            passcode = meeting_data.get('password')

            user = current_user.id

            # Storing meeting information in session
            session['meeting_id'] = meeting_id
            session['join_URL'] = join_URL
            # session['auth_token'] = auth_token

            # Create a ScheduledMeeting instance with the meeting link
            scheduled_meeting_entry = ScheduledMeeting(
                meeting_id=meeting_id,
                topic=topic,
                start_time=start_time,
                user=current_user,
                timezone=timezone,
                meeting_link=join_URL,  # Set the meeting_link value
                passcode=passcode
            )

            db.session.add(scheduled_meeting_entry)
            db.session.commit()
            meeting_datetime = scheduled_meeting_entry.start_time
            user = User.query.get(user_id)
            # utc_start_time = start_time.astimezone(pytz.utc) - timedelta(minutes=1)
            start_time=start_time
            # start_time_bot=start_time - timedelta(minutes=1)
            scheduler.add_job(join_meeting_bot, 'date', run_date=start_time, args=[meeting_id, passcode, user, user_id,meeting_datetime,email])
            logging.info('scheduler job added')
            meeting_details = {
                    'topic': topic,
                    'join_url': join_URL,
                    'meeting_id': meeting_id,
                    'passcode': passcode,
                    'start_time': start_time,
                    'duration': duration,
                    'timezone':timezone,
                }
       
            try:
                calendar_link = create_google_calendar_event(current_user, meeting_details)
                response_data = {
                'success': True,
                'meeting_id': meeting_id,
                'join_URL': join_URL,
                'passcode' : passcode,
                'calendar_link': calendar_link
            }

            except Exception as e:
                 logging.error(f'Failed to create Google Calendar event: {e}')
                 response_data = {
                'success': True,
                'meeting_id': meeting_id,
                'join_URL': join_URL,
                'passcode' : passcode,
                'calendar_link': 'not synced with google'
            }

            return jsonify(response_data),200
        
        except Exception as e:
            error_message = str(e)
            response_data = {
                'success': False,
                'error_message': error_message,
            }
            return jsonify(response_data), 500

    # If form validation fails, return an error response
    error_messages = [str(error) for error in sform.errors.values()]
    response_data = {
        'success': False,
        'error_messages': error_messages,
    }
    logging.info(f'error messages {error_messages}')
    return jsonify(response_data), 400


def join_meeting_bot(meeting_id, passcode,user,user_id,meeting_datetime,email):
    with app.app_context():
        logging.info('in bot function')
        auth_token = prepare_auth_token(user)
        formatted_time = meeting_datetime.strftime("%Y%m%d_%H%M%S")
        try:
            response = requests.get(
                f'https://api.zoom.us/v2/meetings/{meeting_id}/jointoken/local_recording',
                headers={'Authorization': auth_token}
            )
            if response.status_code == 200:
                join_token = response.json().get('token')  # Make sure 'token' is the correct key
            else:
                logging.info(f"Failed to obtain local recording join token. Status code: {response.status_code}")
            
            headers = {
            'Authorization': auth_token,
            'Content-Type': 'application/json'
            }
            url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
            try:
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    meeting_details = response.json()
                    actual_passcode = meeting_details.get('password')
                    if actual_passcode == passcode:
                        lahore_timezone = pytz.timezone('Asia/Karachi')
                        date = datetime.now(lahore_timezone)
                        signature = generate_jwt()  
                        config_file_path = generate_config_file(meeting_id, passcode, user_id, signature,join_token)
                        image_tag = f"user_{user_id}_image"
                        dockerfile_dir = os.getenv('DOCKER_FILE_DIR')
                        demo_dir_path = os.getenv('DEMO_DIR')

                        destination_file_path = os.path.join(demo_dir_path, os.path.basename(config_file_path))
                        try:
                            shutil.copyfile(config_file_path, destination_file_path)
                        except Exception as e:
                            logging.info(f"Failed to copy file: {e}")

                        image_tag = build_docker_image(image_tag, config_file_path, dockerfile_dir, demo_dir_path)  
                        run_docker_container(image_tag, user_id, meeting_id, destination_file_path,formatted_time,email)
            except Exception as e:
                logging.info(f"API request failed: {e}")
        except Exception as e:
            logging.info(f"Error in join_meeting_bot: {e}")

############################################### Soft Delete Instant and Scheduled Meeting Data ###################################################
@app.route("/delete-meeting/<int:meeting_id>/<meeting_type>", methods=["GET"])
@login_required
def delete_meeting(meeting_id, meeting_type):
    if meeting_type == 'meeting':
        meeting = Meeting.query.get(meeting_id)
    elif meeting_type == 'scheduled_meeting':
        meeting = ScheduledMeeting.query.get(meeting_id)
    else:
        flash("Invalid meeting type specified", "error")
        return redirect(url_for('previous_meetings'))

    if meeting:
        meeting.deleted = True
        db.session.commit()
        flash("Meeting has been deleted", "success")
    else:
        flash("Meeting not found", "error")

    return redirect(url_for('previous_meetings'))

########################################################################## Fetch Upcoming Meetings ######################################################################

def get_all_meetings(user):
    if user.is_authenticated:
        all_meetings = ScheduledMeeting.query.filter(
            ScheduledMeeting.user_id == user.id,
            ScheduledMeeting.deleted == False
        ).order_by(ScheduledMeeting.start_time.desc()).all()  # Fetch all meetings and order them by start time
        return all_meetings
    return []

def get_upcoming_meetings(user):
    current_time = datetime.now()  # Get the current datetime
    upcoming_meetings=[]

    if user.is_authenticated:
        upcoming_meetings = ScheduledMeeting.query.filter(
            ScheduledMeeting.user_id == user.id,
            ScheduledMeeting.start_time > current_time,
            ScheduledMeeting.deleted == False
        ).all()
    return upcoming_meetings

#=========================================================================Transcribe Routes============================================================================================#

@app.route('/transcribe_page', methods=["POST"])
@login_required
def transcribe_page():
    meeting_id = request.form.get('meeting_id')
    user_id = current_user.id
    email = current_user.email
    meeting_datetime = request.form.get('meeting_datetime')
    meeting_date = datetime.strptime(meeting_datetime, '%Y%m%d_%H%M%S')
    # Check if transcription already exists
    transcription_data = Transcription.query.filter_by(meeting_id=meeting_id, meeting_date=meeting_date, status='completed').first()
    if transcription_data:
        if transcription_data.status == 'completed':
            flash('Meeting is already transcribed', 'success')
            return redirect(url_for('previous_meetings'))
        elif transcription_data.status == 'pending':
            flash('Process is still pending', 'info')
    else:
        transcription_data = Transcription(user_id=user_id, meeting_id=meeting_id, meeting_date=meeting_date, status='pending')
        db.session.add(transcription_data)
    # Get the audio path
    video_path = get_audio_path_by_meeting_id(folder_path, meeting_id, meeting_datetime)
    if video_path is None or not os.path.exists(video_path):
        flash('Meeting audio not available. Please take the meeting and ensure it is recorded !!!.', 'error')
        return redirect(url_for('previous_meetings'))
    if video_path.endswith('.pcm'):
        # Convert video to WAV format if it's a PCM file
        audio_file, duration = pcm_to_wav_ffmpeg(video_path)
    else:
        audio_file = video_path
    

    if audio_file is None:
        flash('Error converting meeting audio to WAV format.', 'error')
        return redirect(url_for('previous_meetings'))
    
    # Check for PATH_FILE environment variable
    path_file = os.getenv('PATH_FILE')
    if path_file is None:
        flash('Configuration error: PATH_FILE environment variable is not set.', 'error')
        return redirect(url_for('previous_meetings'))
    
    audio_file = os.path.join(path_file, audio_file)
    # Run diarization and transcription
    diarization_dir=os.getenv('DIARIZATION_DIR')
    user_dir = os.path.join(diarization_dir, str(user_id))
    diarization_file_path=os.path.join(user_dir, f"{meeting_id}_diarization.txt")
    if os.path.exists(diarization_file_path):
        diarization=diarization_file_path
    else:
        diarization = run_diarization(pipeline, audio_file,user_id,meeting_id)

    speakers = parse_diarization_file(diarization)
    audio_path = process_audio_file(audio_file)
    transcriptions = transcribe_segments(speakers, audio_path, model,user_id)
    # Collect and sort transcriptions
    all_transcripts = [
        {'start': segment['start'], 'end': segment['end'], 'speaker': speaker, 'text': segment['transcription']}
        for speaker, segments in transcriptions.items() for segment in segments
    ]
    all_transcripts.sort(key=lambda x: x['start'])
    sentiment_results,sentiment_counts, positive_percentage, negative_percentage, neutral_percentage = analyze_sentiments(all_transcripts)
    # Save results
    save_path = "output/transcript_result.csv"
    txt_save_path = "output/transcript_result.txt"
    df_results = pd.DataFrame(all_transcripts)
    df_results.columns = ['Start', 'End', 'Speaker', 'Text']
    df_results.to_csv(save_path, index=False)
    df_results.to_csv(txt_save_path, sep='\t', index=False)
    # Process transcription data
    df = pd.read_csv(save_path)
    text = process_transcription(df, txt_save_path)
    keywords = get_chatbot_response('keywords', text)
    summarized_meeting = get_chatbot_response("summary", text)
    action_meeting = get_chatbot_response("action", text)
    action_items_list = action_meeting.strip().split('\n')

     # Process the outline_meeting data into a structured format
    transcription_html = '''
    <table class="table table-striped table-bordered">
        <thead>
            <tr>
                <th>Start</th>
                <th>End</th>
                <th>Speaker</th>
                <th>Text</th>
            </tr>
        </thead>
        <tbody>
    '''

    index = 0  # Initialize an index variable
    for transcript in all_transcripts:
        transcription_html += f'''
            <tr>
                <td>{transcript['start']}</td>
                <td>{transcript['end']}</td>
                <td><span contenteditable="true" class="editable-label" data-meeting-id="{meeting_id}" data-original="{transcript['speaker']}" onblur="saveSpeakerLabel(this, '{meeting_id}', {index})">{transcript['speaker']}</span></td>
                <td>{transcript['text']}</td>
            </tr>
        '''
        index += 1  # Increment the index for the next row

    # Close the table
    transcription_html += '</tbody></table>'

    transcription_data.summary = summarized_meeting
    transcription_data.action = '\n'.join(action_items_list)
    transcription_data.diarization = transcription_html
    transcription_data.audio = audio_file
    transcription_data.keywords = keywords
    transcription_data.positive_percentage = positive_percentage
    transcription_data.negative_percentage = negative_percentage
    transcription_data.neutral_percentage = neutral_percentage
    transcription_data.status='completed'  # Set status to 'completed'

    db.session.commit()
    send_transcription_email(email,meeting_id,meeting_datetime)
    return render_template('transcribe.html', keywords=keywords, summary=summarized_meeting, action=action_items_list, 
                        csv_table=transcription_html, audio_file=audio_file, positive_percentage=positive_percentage,
        negative_percentage=negative_percentage, neutral_percentage=neutral_percentage)
    return render_template('transcribe.html')

@app.route('/transcribe', methods=['POST'])
@login_required
def transcribe():
    user_id = current_user.id
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url) ## user will be redirected back to the form submission page.

    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url) ## user will be redirected back to the form submission page.

    if file:
        upload_dir = os.path.join(app.root_path, 'dataFiles', 'uploads')
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        original_filename = secure_filename(file.filename)
        unique_filename = f"{timestamp}_{original_filename}"
        uploaded_file_path = os.path.join(upload_dir, unique_filename)
        try:
            file.save(uploaded_file_path)
        except Exception as e:
            flash(f'An error occurred while saving the file: {e}', 'error')
            return redirect(request.url) ## user will be redirected back to the form submission page.

        # Save file information in FileUpload table
        new_file_upload = FileUpload(
            user_id=current_user.id,
            filename=unique_filename,
            file_path=uploaded_file_path,
            upload_time=datetime.now()  # Assuming datetime.now(lahore_timezone) is valid
        )
        db.session.add(new_file_upload)
        db.session.commit()
        path_file = os.getenv('OUTPUT_FOLDER_PATH')
        file_ext = os.path.splitext(uploaded_file_path)[1].lower()
        if file_ext == '.wav':
            audio_file = uploaded_file_path
        elif file_ext == '.pcm':
            try:
                audio_file,duration=pcm_to_wav_ffmpeg(uploaded_file_path)
            except Exception as e:
                flash(f'An error occurred while converting PCM to WAV: {e}', 'error')
                return redirect(request.url)
        else:
            try:
                audio_file,duration=convert_video_to_audio(uploaded_file_path)
            except Exception as e:
                flash(f'An error occurred while converting video to audio: {e}', 'error')
                return redirect(request.url)
        audio_file = os.path.join(path_file, audio_file)
        diarization = run_diarization(pipeline, audio_file,user_id,unique_filename)
        speakers = parse_diarization_file(diarization)
        audio_path = process_audio_file(audio_file)
        transcriptions = transcribe_segments(speakers, audio_path, model,user_id)
        # Collect and sort transcriptions
        all_transcripts = [
        {'start': segment['start'], 'end': segment['end'], 'speaker': speaker, 'text': segment['transcription']}
        for speaker, segments in transcriptions.items() for segment in segments
        ]
        all_transcripts.sort(key=lambda x: x['start'])

        sentiment_results,sentiment_counts, positive_percentage, negative_percentage, neutral_percentage = analyze_sentiments(all_transcripts)
        df_results = pd.DataFrame(all_transcripts)
        df_results.columns = ['Start', 'End', 'Speaker', 'Text']
        csv_path = os.path.join(app.root_path, 'dataFiles', 'audio2csv', 'transcript_result.csv')
        df_results.to_csv(csv_path,index=False)
        # Process transcription for summarization
        output_dir = os.path.join(app.root_path, 'dataFiles', 'csv2txt', 'transcript_result.txt')

        text = process_transcription(df_results, output_dir)
        keywords=get_chatbot_response('keywords',text)
        # Generate summaries and other outputs
        summarized_meeting = get_chatbot_response("summary", text)
        action_meeting = get_chatbot_response("action", text)

         # Process the outline_meeting data into a structured format
        transcription_html = '''
        <table class="table table-striped table-bordered">
            <thead>
                <tr>
                    <th>Start</th>
                    <th>End</th>
                    <th>Speaker</th>
                    <th>Text</th>
                </tr>
            </thead>
            <tbody>
        '''

        index = 0  # Initialize an index variable
        for transcript in all_transcripts:
            transcription_html += f'''
                <tr>
                    <td>{transcript['start']}</td>
                    <td>{transcript['end']}</td>
                    <td><span contenteditable="true" class="editable-label" data-file-upload-id="{new_file_upload.id}" data-original="{transcript['speaker']}" onblur="saveSpeakerLabel(this, '{new_file_upload.id}', {index})">{transcript['speaker']}</span></td>
                    <td>{transcript['text']}</td>
                </tr>
            '''
            index += 1  # Increment the index for the next row

        # Close the table
        transcription_html += '</tbody></table>'

        # Save the transcription and summaries in UploadedFileTranscription table
        new_transcription = UploadedFileTranscription(
            file_upload_id=new_file_upload.id,
            summary=summarized_meeting,
            action=action_meeting,
            diarization=transcription_html,
            audio=uploaded_file_path,
            keywords=keywords,
            positive_percentage=positive_percentage,
            negative_percentage=negative_percentage,
            neutral_percentage=neutral_percentage
        )
        db.session.add(new_transcription)
        db.session.commit()


        return jsonify({'success': True, 'redirect_url': url_for('uploaded_file_info', file_id=new_file_upload.id)})
    return render_template('transcribe.html')


@app.route('/transcribe_meeting_route', methods=["GET", "POST"])
@login_required
def transcribe_meeting_route():
    return render_template('transcribe.html')

####################################################################### Fetching Previous Meeting Data ##############################################################

@app.route("/previous-meetings", methods=["GET", "POST"])
@login_required
def previous_meetings():
    try:
        current_time = datetime.now()
        # Fetch non-deleted meetings from both tables
        instant_meetings = Meeting.query.filter(Meeting.user_id == current_user.id, Meeting.deleted == False).order_by(desc(Meeting.MDate)).all()
        scheduled_meetings = ScheduledMeeting.query.filter(ScheduledMeeting.user_id == current_user.id, ScheduledMeeting.deleted == False).order_by(desc(ScheduledMeeting.start_time)).all()

        # Combine lists
        all_meetings = instant_meetings + scheduled_meetings

         # Sort combined list by date
        all_meetings.sort(key=lambda x: x.MDate if hasattr(x, 'MDate') else x.start_time, reverse=True)

        # Initialize lists
        upcoming_meetings = []
        occurred_meetings = []

        for meeting in all_meetings:
            meeting_date = meeting.MDate if hasattr(meeting, 'MDate') else meeting.start_time
            if meeting_date > current_time:
                upcoming_meetings.append(meeting)
            else:
                occurred_meetings.append(meeting)

        uploaded_files = FileUpload.query.filter_by(deleted=False, user_id=current_user.id).all()
        
        return render_template("previous_meetings.html",
                               upcoming_meetings=upcoming_meetings,
                               occurred_meetings=occurred_meetings,
                               uploaded_files=uploaded_files,
                               current_time=current_time,
                               meeting_has_transcription=meeting_has_transcription)
    except Exception as e:
        return str(e)

@app.route('/prev_meeting_info/<string:meeting_id>/<meeting_date>', methods=["GET", "POST"])
@login_required
def prev_meeting_info(meeting_id,meeting_date):
    try:
        meeting_date = datetime.strptime(meeting_date, '%Y%m%d_%H%M%S')
        try:
            # Attempt to convert meeting_id to an integer
            meeting_id = int(meeting_id.replace(" ", ""))
        except ValueError:
            # Log the error or send an alert if necessary
            flash('Invalid Meeting ID. Please check the ID and try again.', 'error')
            return redirect(url_for('previous_meetings'))
        # Fetch the meeting's transcription data from the Transcription table
        
        

        transcription_data = Transcription.query.filter_by(meeting_id=meeting_id,meeting_date=meeting_date).first()
        if transcription_data:
            if transcription_data.status == 'in_progress':
                flash('The transcription for this meeting is currently in progress. Please try again later.', 'warning')
                return redirect(url_for('previous_meetings'))
            elif transcription_data.status == 'incomplete':
                flash('The audio of this meeting was less than 2 minutes or mostly silent', 'warning')
                return redirect(url_for('previous_meetings'))
            else:
                return render_template(
                    'transcribe.html', 
                    meeting_id=meeting_id,
                    meeting_date=meeting_date,  # Pass the string format directly
                    keywords=transcription_data.keywords,
                    summary=transcription_data.summary, 
                    action=transcription_data.action.split('\n'),  # Convert action to a list
                    csv_table=transcription_data.diarization,
                    audio_file=transcription_data.audio,
                    positive_percentage=transcription_data.positive_percentage,
                    negative_percentage=transcription_data.negative_percentage,
                    neutral_percentage=transcription_data.neutral_percentage)
        else:
            flash('Transcription data not found for the selected meeting.', 'warning')
            return redirect(url_for('previous_meetings'))
        
    except Exception as e:
        return str(e)  
    
@app.route('/share_meeting_data/<string:meeting_id>/<meeting_date>', methods=["GET", "POST"])
def share_meeting_data(meeting_id,meeting_date):
    try:
        meeting_date = datetime.strptime(meeting_date, '%Y%m%d_%H%M%S')
        try:
            # Attempt to convert meeting_id to an integer
            meeting_id = int(meeting_id.replace(" ", ""))
        except ValueError:
            # Log the error or send an alert if necessary
            flash('Invalid Meeting ID. Please check the ID and try again.', 'error')
            return redirect(url_for('previous_meetings'))
        # Fetch the meeting's transcription data from the Transcription table
        transcription_data = Transcription.query.filter_by(meeting_id=meeting_id,meeting_date=meeting_date).first()
        if transcription_data:
            return render_template(
                'share_transcription.html', 
                meeting_id=meeting_id,
                meeting_date=meeting_date,  
                keywords=transcription_data.keywords,
                summary=transcription_data.summary, 
                action=transcription_data.action.split('\n'),  # Convert action to a list
                csv_table=transcription_data.diarization,
                audio_file=transcription_data.audio,
                positive_percentage=transcription_data.positive_percentage,
                negative_percentage=transcription_data.negative_percentage,
                neutral_percentage=transcription_data.neutral_percentage)
        else:
            flash('Transcription data not found for the selected meeting. Please click on transcribe button', 'warning')
            return redirect(url_for('previous_meetings'))
        
    except Exception as e:
        return str(e)  
@app.route('/get_audio/<path:audio_file_name>', methods=["GET", "POST"])
def get_audio(audio_file_name):
    # Extract the base name without the extension and append '.wav' extension
    base_name = os.path.splitext(audio_file_name)[0]
    wav_file_name = f"{base_name}.wav"
    # Construct the full path to the WAV file
    wav_path_recordings = os.path.join(app.root_path, 'dataFiles', 'recordings', wav_file_name)
    wav_path_video2audio = os.path.join(app.root_path, 'dataFiles', 'Video2Audio', wav_file_name)
    if os.path.exists(wav_path_recordings):
        return send_file(wav_path_recordings, mimetype='audio/wav')
    # If not found, check in the 'Video2Audio' directory
    elif os.path.exists(wav_path_video2audio):
        return send_file(wav_path_video2audio, mimetype='audio/wav')
    else:
        return "File not found", 404

def meeting_has_transcription(meeting_id, meeting_datetime):
    meeting_date = datetime.strptime(meeting_datetime, '%Y%m%d_%H%M%S')
    transcription_from_meeting = Transcription.query.filter_by(meeting_id=meeting_id, meeting_date=meeting_date).first()
    transcription_from_scheduled_meeting = Transcription.query.filter_by(scheduled_meeting_id=meeting_id, meeting_date=meeting_date).first()
    transcription = transcription_from_meeting or transcription_from_scheduled_meeting
    
    return transcription


######################################################################### Uploaded File Routes #########################################################################

@app.route('/uploaded_file_info/<int:file_id>', methods=["GET", "POST"])
@login_required
def uploaded_file_info(file_id):
    # Fetch the meeting's transcription data from the Transcription table
    data = UploadedFileTranscription.query.filter_by(file_upload_id=file_id).first()
    if data:
        # Proceed with rendering the template using the possibly adjusted outline
        return render_template(
            'transcribe.html',
            keywords=data.keywords, 
            summary=data.summary, 
            action=data.action.split('\n'),  # Convert action to a list
            csv_table=data.diarization,
            audio_file=data.audio,
            positive_percentage=data.positive_percentage,
            negative_percentage=data.negative_percentage,
            neutral_percentage=data.neutral_percentage)
    else:
        flash('Transcription data not found for the selected meeting.', 'warning')
        return redirect(url_for('previous_meetings'))

@app.route('/share_file_data/<int:file_id>', methods=["GET", "POST"])
def share_file_data(file_id):
    # Fetch the meeting's transcription data from the Transcription table
    transcription_data = UploadedFileTranscription.query.filter_by(file_upload_id=file_id).first()

    if transcription_data:
        return render_template(
            'share_transcription.html', 
            keywords=transcription_data.keywords,
            summary=transcription_data.summary, 
            action=transcription_data.action.split('\n'),  # Convert action to a list
            csv_table=transcription_data.diarization,
            audio_file=transcription_data.audio,
            positive_percentage=transcription_data.positive_percentage,
            negative_percentage=transcription_data.negative_percentage,
            neutral_percentage=transcription_data.neutral_percentage)
    else:
        flash('Transcription data not found for the selected file. Please upload your file again and transcribe', 'warning')
        return redirect(url_for('previous_meetings'))

    

@app.route("/delete_file/<int:file_id>", methods=["GET"])
@login_required
def delete_file(file_id):
    file = FileUpload.query.get(file_id)

    if file:
        # Mark the meeting as deleted by setting the 'deleted' column to True
        file.deleted = True
        db.session.commit()
        flash("File has been marked as deleted", "success")
    else:
        flash("File not found", "error")

    return redirect(url_for('previous_meetings'))  # Redirect to your previous meetings page

####################################################################### Google Sign In / Sign Up ####################################################################

google_oauth = OAuth(app)

@app.route('/google/')
def google_login():

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    google_oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=CONF_URL,
        client_kwargs={
            'scope': 'openid email profile https://www.googleapis.com/auth/calendar',
            'access_type': 'offline',  # Important for getting the refresh token
        }
    )

    # Redirect to google_auth function
    redirect_uri = url_for('google_auth', _external=True,_scheme='https')
    session['nonce'] = generate_token()
    return google_oauth.google.authorize_redirect(redirect_uri, access_type='offline', nonce=session['nonce'])

@app.route('/google/auth/')
def google_auth():
    message = session.pop('flash', None)
    token = google_oauth.google.authorize_access_token()
    google_user = google_oauth.google.parse_id_token(token, nonce=session['nonce'])  # Renamed variable to google_user
    
    if google_user:  # Check if google_user is not None
        google_email = google_user['email']
        existing_user = User.query.filter_by(email=google_email).first()  # Renamed variable to existing_user
        
        if existing_user:
            # login_user(existing_user)
            existing_user.google_access_token = token['access_token']
            refresh_token = token.get('refresh_token')
            print('refresh token ', refresh_token)
            if refresh_token:
                existing_user.google_refresh_token = refresh_token
            expires_in = token.get('expires_in')


            if expires_in:
                existing_user.google_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            existing_user.is_google_synced = True

            db.session.commit() 
            return redirect(url_for('meetings'))
        
        else:
            new_user = User(
                fname=google_user['given_name'],
                lname=google_user['family_name'],
                email=google_user['email'],
                password=None,
                email_confirmed=True
            )
            print('new user', new_user)
            new_user.google_access_token = token['access_token']
            refresh_token = token.get('refresh_token')
            print('refresh token', refresh_token)
            if refresh_token:
                new_user.google_refresh_token = refresh_token
                print('set in db')
                
            expires_in = token.get('expires_in')


            if expires_in:
                new_user.google_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            new_user.is_google_synced = True


            db.session.add(new_user)
            db.session.commit()
            
            
            login_user(new_user)  # Directly login the new user object
            session['flash'] = "Login successful."
            return redirect(url_for('home'))
        
    else:
        # Handle case where google_user is None
        return render_template("integrations.html", message="Error during syncing.")

    return render_template("login.html", message=message)

#################################################################################### ZOOM configurations #########################################################

app.secret_key = os.getenv('SECRET_KEY')

@app.route('/zoom/')
def zoom_login():
    logging.info('zoom logging in')
    # Directly start the OAuth process without registering the client again
    return zoom_oauth.zoom.authorize_redirect(url_for('initiate_oauth', _external=True, _scheme='https'))


@app.route('/initiate_oauth')
def initiate_oauth():
    return zoom_oauth.zoom.authorize_redirect(url_for('zoom_oauth_callback', _external=True,_scheme='https'))

@app.route('/oauth/callback')
def zoom_oauth_callback():
    try:
        token = zoom_oauth.zoom.authorize_access_token()
        session['zoom_access_token'] = token['access_token']
        session['zoom_refresh_token'] = token.get('refresh_token')  # Store the refresh token
        session['is_zoom_oauth']=True
        expires_in = token.get('expires_in', 3600)  # Default to 1 hour if not provided
        expiration_time = datetime.now() + timedelta(seconds=expires_in)
        resp = zoom_oauth.zoom.get('https://api.zoom.us/v2/users/me', token=token)
        profile = resp.json()

        # Check if user exists in your database
        user = User.query.filter_by(email=profile['email']).first()

        if user:
            logging.info('user already exists in our application')
            user.zoom_access_token = token['access_token']
            refresh_token = token.get('refresh_token')
            if refresh_token:
                user.zoom_refresh_token = refresh_token
            
            expires_in = token.get('expires_in')
            if expires_in:
                user.zoom_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
            user.is_zoom_synced = True

            db.session.commit()

        else:
            # Create a new user record if not existing
            full_name = profile.get('display_name', 'Unknown Name').split()
            first_name = full_name[0] if full_name else 'Unknown'
            last_name = full_name[-1] if len(full_name) > 1 else 'Unknown'
            # Provide default values for lname and password
            user = User(
                email=profile['email'], 
                fname=first_name, 
                lname=last_name, 
                password=None,
                email_confirmed=True
            )
            db.session.add(user)

            user.zoom_access_token = token['access_token']
            user.zoom_refresh_token = token['refresh_token']
            user.zoom_token_expires_at = expiration_time
            user.is_zoom_synced = True


            db.session.commit()

        # Log in the user
        login_user(user)
        flash(Markup('Sync your calendar with Google for seamless schedule updates. <a href="{}">Click here</a>'.format(url_for('google_login'))), "success")


        # Redirect to the home page or dashboard after successful login
        return redirect(url_for('home'))
    except Exception as e:
        logging.info("OAuth error:", e)
        return "OAuth process failed", 500

@app.route('/deauth', methods=['POST'])
def deauthorization():
    # Verify Zoom's verification token
    incoming_token = request.headers.get('Authorization')
    if not incoming_token or incoming_token != os.getenv('ZOOM_VERIFICATION_TOKEN'):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Process the deauthorization request
    deauth_data = request.json
    return jsonify({'message': 'App deauthorized and removed successfully'}), 200

@app.route('/app-landing')
def app_landing():
    zoom_client_id = os.getenv('ZOOM_CLIENT_ID')
    redirect_uri = os.getenv('REDIRECT_URI')  # This should match the redirect URI registered with Zoom
    scope = 'meeting:write meeting:read'  # Adjust the scope according to your app's requirements
    zoom_auth_url = f'https://zoom.us/oauth/authorize?response_type=code&client_id={zoom_client_id}&redirect_uri={redirect_uri}&scope={scope}'
    
    return render_template('landing_page.html', zoom_auth_url=zoom_auth_url)

###########################################################  POLICY ROUTES ############################################################################

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html')


@app.route('/tou')
def terms_of_use():
    return render_template('tou.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/documentation')
def docss():
    return render_template('documentation.html')

@app.route('/integrations')
def integrations():
    return render_template('integrations.html')

################################################# CONFIGURATION FOR BOT ######################################################

@app.route('/enter_passcode', methods=['GET'])
@login_required
def show_enter_passcode():
    form = MeetingForm()
    return render_template('enter_passcode.html', form=form)


@app.route('/enter_passcode', methods=['POST'])
@login_required
def enter_passcode():
    try:
        meeting_id = request.form.get('meeting_id')
        passcode = request.form.get('passcode')
        if not meeting_id or not passcode:
            return jsonify({'success': False, 'message': 'Missing meeting ID or passcode'}), 400

        user_id = str(current_user.id)
        email = current_user.email
        is_zoom_oauth = session.get('is_zoom_oauth', False)
        token = session.get('zoom_access_token') if is_zoom_oauth else None
        auth_token = prepare_auth_token(current_user)
        
        response = requests.get(
            f'https://api.zoom.us/v2/meetings/{meeting_id}/jointoken/local_recording',
            headers={'Authorization': auth_token}
        )
        join_token = None
        if response.status_code == 200:
            join_token = response.json().get('token')
        else:
            logging.info(f"Failed to obtain local recording join token. Status code: {response.status_code}")

        headers = {
            'Authorization': auth_token,
            'Content-Type': 'application/json'
        }
        url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
        meeting_verified = False
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                meeting_details = response.json()
                actual_passcode = meeting_details.get('password')
                meeting_verified = actual_passcode == passcode
        except requests.RequestException as e:
            logging.info("API request failed", e)

        # if not meeting_verified:
            # return jsonify({'success': False, 'message': 'Incorrect passcode. Please try again.'}), 400

        lahore_timezone = pytz.timezone('Asia/Karachi')
        date = datetime.now(lahore_timezone)
        signature = generate_jwt()
        config_file_path = generate_config_file(meeting_id, passcode, user_id, signature, join_token)
        image_tag = f"user_{user_id}_image"
        dockerfile_dir = os.getenv('DOCKER_FILE_DIR')
        demo_dir_path = os.getenv('DEMO_DIR')
        destination_file_path = os.path.join(demo_dir_path, os.path.basename(config_file_path))
        try:
            shutil.copyfile(config_file_path, destination_file_path)
        except Exception as e:
            logging.info(f"Failed to copy file: {e}")

        existing_meeting = Meeting.query.filter_by(MID=meeting_id, user_id=user_id).order_by(Meeting.MDate.desc()).first()
        scheduled_meeting = ScheduledMeeting.query.filter_by(meeting_id=meeting_id, user_id=user_id).order_by(ScheduledMeeting.start_time.desc()).first()

        if existing_meeting and scheduled_meeting:
            meeting_datetime = min(existing_meeting.MDate, scheduled_meeting.start_time)
        elif existing_meeting:
            meeting_datetime = existing_meeting.MDate
        elif scheduled_meeting:
            meeting_datetime = scheduled_meeting.start_time
        else:
            new_meeting = Meeting(
                user_id=user_id,
                MID=meeting_id,
                MTopic='External Meeting',
                MDate=date,
                Passcode=passcode,
                source='external'
            )
            db.session.add(new_meeting)
            db.session.commit()
            meeting_datetime = new_meeting.MDate

        formatted_time = meeting_datetime.strftime("%Y%m%d_%H%M%S")
        image_tag = build_docker_image(image_tag, config_file_path, dockerfile_dir, demo_dir_path)
        run_docker_container(image_tag, user_id, meeting_id, destination_file_path, formatted_time, email)

        return jsonify({'success': True, 'message': 'AI NOTE GENIUS has been notified. Will join your meeting in a few minutes'}), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': e}), 404


@app.route('/update-speaker-label', methods=['POST'])
def update_speaker_label():
    data = request.get_json()
    try:
        meeting_id = data['meeting_id']
        speaker_index = int(data['speaker_index'])
        new_label = data['new_label']

        transcription = Transcription.query.filter_by(meeting_id=meeting_id).first()
        if not transcription:
            return jsonify({'message': 'Transcription not found'}), 404

        soup = BeautifulSoup(transcription.diarization, 'html.parser')
        rows = soup.find_all('tr')[1:]  # Exclude header row
        if not (0 <= speaker_index < len(rows)):
            return jsonify({'message': 'Speaker index out of range'}), 400

        current_labels = set([row.find_all('td')[2].text.strip() for row in rows])
        if new_label in current_labels:
            return jsonify({'error': 'Label already in use by another speaker'}), 409
        
        old_label = rows[speaker_index].find_all('td')[2].text.strip()
        # Normalize old label to handle different cases and formats in text
        normalized_old_label = " ".join(re.split(r"[_\s]", old_label)).title()
        # Update diarization HTML
        for row in rows:
            speaker_cell = row.find_all('td')[2]
            if speaker_cell.text.strip() == old_label:
                speaker_cell.string.replace_with(new_label)

        transcription.diarization = str(soup)

        # Create regex pattern to match old label in a case-insensitive manner
        pattern = re.compile(r'\b' + re.escape(normalized_old_label) + r'\b', re.IGNORECASE)

        # Update summary and action items using the regex pattern
        transcription.summary = pattern.sub(new_label, transcription.summary)
        transcription.action = pattern.sub(new_label, transcription.action)

        db.session.commit()
        return jsonify({'message': f'All instances of label {old_label} updated successfully.'}), 200

    except KeyError as e:
        return jsonify({'error': str(e)}), 400
