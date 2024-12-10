import docker
from dotenv import load_dotenv
import logging
import os
import tarfile
import io
from AINotes import app
from AINotes.transc import get_audio_path_by_meeting_id, convert_video_to_audio,pcm_to_wav_ffmpeg,run_diarization,parse_diarization_file,process_audio_file,transcribe_segments,pipeline,model,process_transcription,folder_path,analyze_sentiments,is_audio_mostly_silent
from datetime import datetime
from flask_mail import Message
from .. import mail
from flask import  url_for
from AINotes import db,app
from AINotes.models import Transcription,Meeting,ScheduledMeeting
from AINotes.openai import get_chatbot_response
import pandas as pd


load_dotenv()

log_file_path = os.getenv('LOG_FILE')
logging.basicConfig(filename=log_file_path, filemode='a', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def build_docker_image(image_tag, config_file_path, dockerfile_dir, demo_dir_path):
    logging.info('build started')
    logging.info(datetime.now())
    client = None
    try:
        client = docker.from_env()
    except Exception as e:
        logging.info(f"Failed to initialize Docker client: {e}")
        return None

    user_dockerfile_path = os.path.join(dockerfile_dir, 'UserDockerFile')
    if not os.path.exists(user_dockerfile_path):
        logging.info(f"User Dockerfile does not exist: {user_dockerfile_path}")
        return None
    if not os.path.exists(demo_dir_path):
        logging.info(f"Demo directory does not exist:, {demo_dir_path}")
        return None

    build_context = io.BytesIO()
    with tarfile.open(fileobj=build_context, mode='w') as tar:
        with open(user_dockerfile_path, 'r') as file:
            dockerfile_content = file.read()
            dockerfile_info = tarfile.TarInfo('Dockerfile')
            dockerfile_bytes = dockerfile_content.encode('utf-8')
            dockerfile_info.size = len(dockerfile_bytes)
            tar.addfile(dockerfile_info, io.BytesIO(dockerfile_bytes))
        with open(config_file_path, 'rb') as config_file:
            config_data = config_file.read()
            config_info = tarfile.TarInfo(name='config.txt')
            config_info.size = len(config_data)
            tar.addfile(config_info, io.BytesIO(config_data))
        for root, dirs, files in os.walk(demo_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=demo_dir_path)
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    file_info = tarfile.TarInfo(name=os.path.join('demo', arcname))
                    file_info.size = len(file_data)
                    tar.addfile(file_info, io.BytesIO(file_data))
    build_context.seek(0)
    logging.info('build context succeeded')
    try:
        logging.info('Building image with user-specific Dockerfile...')
        image, build_logs = client.images.build(
            fileobj=build_context,
            custom_context=True,
            encoding='utf-8',
            tag=image_tag,
            rm=True
        )
        # for chunk in build_logs:
        #     if 'stream' in chunk:
        #         print(chunk['stream'].strip())
        # print(f"Docker image {image_tag} built successfully.")
        return image_tag
    except docker.errors.BuildError as e:
        return None
    except Exception as e:
        logging.info("An error occurred during the build:", e)
        return None
    finally:
        logging.info('Build process completed.')
        build_context.close()

def remove_user_images(user_id):
    import docker
    client = docker.from_env()
    all_images = client.images.list()
 
    user_images = [img for img in all_images if any(str(user_id) in tag for tag in img.tags)]
#    
    for img in user_images:
        try:
            client.images.remove(img.id, force=True)
        except docker.errors.ImageNotFound:
            logging.info(f"Image {img.tags} not found.")
        except docker.errors.APIError as e:
            logging.info(f"Error removing image {img.tags}: {e}")

    # Prune dangling images
    try:
        pruned = client.images.prune(filters={'dangling': True})
    except Exception as e:
        logging.info(f"Error during cleanup of dangling images: {e}")

def run_docker_container(image_tag, user_id, meeting_id, destination_file_path,date,email):
    with app.app_context():
        logging.info('running container')
        logging.info(datetime.now())
        client = docker.from_env()
        config_dir = os.getenv('CONFIG_FILE')  # Directory containing all user-specific config files
        user_config_dir = os.path.join(config_dir, user_id)  # Directory specific to each user
        user_config_file_path = os.path.join(user_config_dir, f"config.txt")  # Path to the user's config file on the host
        recordings_host_dir = os.getenv('RECORDING_DIR')

        volumes = {
            user_config_file_path: {'bind': '/app/demo/config.txt', 'mode': 'ro'},
            recordings_host_dir: {'bind': '/app/recordings', 'mode': 'rw'}  # Allow read-write access to recordings directory
        }
        container = client.containers.run(
            image_tag,
            detach=True,
            volumes=volumes,
            auto_remove=True
        )
        # for log in container.logs(stream=True):
        #     print(log.decode('utf-8').strip())
            # logging.info(log.decode('utf-8').strip())
        try:
            container.wait()  # Wait for the container to exit
            logging.info('bot going to leave')
            logging.info(datetime.now())
           
            recording_dir = os.getenv('RECORDING_DIR')
            original_meeting_file_path = os.path.join(recording_dir, f"{meeting_id}.pcm")
            if os.path.exists(original_meeting_file_path):
                logging.info(f"Recording found for meeting ID {meeting_id}. Going to rename now")
            new_meeting_file_path = os.path.join(recording_dir, f"{meeting_id}_{date}.pcm")
            try:
                os.rename(original_meeting_file_path, new_meeting_file_path)
            except OSError as e:
                logging.info(f"Error renaming file: {e}")
            if os.path.exists(new_meeting_file_path):
                current_size = os.path.getsize(new_meeting_file_path)
                logging.info(f"Recording found for meeting ID {new_meeting_file_path}.File size is {current_size}")
                transcribe_backend(meeting_id, user_id,date,email)
                # transcribe_backend.delay(meeting_id, user_id, date,email)
            else:
                logging.info(f"No recording found for meeting ID {new_meeting_file_path}.")

            remove_user_images(user_id)

            return container.id
        except Exception as e:
            logging.info(f'Error waiting for container to finish: {e}')


def transcribe_backend(meeting_id,user_id,meeting_datetime,email):
    logging.info('in try backend')
    try:
        with app.app_context():
            meeting_datetime_db = datetime.strptime(meeting_datetime, '%Y%m%d_%H%M%S')
            transcription = Transcription(
                    user_id=user_id, 
                    meeting_id=meeting_id, 
                    meeting_date=meeting_datetime_db ,
                    status='pending'
                )
            db.session.add(transcription)
            # Update the status to 'in_progress'
            transcription.status = 'in_progress'

            db.session.commit()
            # Get the audio path
            video_path = get_audio_path_by_meeting_id(folder_path, meeting_id,meeting_datetime)
            # Convert video to WAV format
            audio_file, duration = pcm_to_wav_ffmpeg(video_path)
            if audio_file is None:
                logging.info('Error converting meeting audio to WAV format.', 'error')
            if duration < 120:
                logging.info(f'Audio duration is less than 120 seconds: {duration} seconds.')
                transcription.status = 'incomplete'
                db.session.commit()
                return  # Stop processing and exit the function
            
            if is_audio_mostly_silent(audio_file, silence_threshold=-40, min_silence_len=500, silence_percentage_threshold=90):
                logging.info(f'Audio is mostly silent')
                transcription.status = 'incomplete'
                db.session.commit()
                return

            # Check for PATH_FILE environment variable
            path_file = os.getenv('PATH_FILE')
            if path_file is None:
                logging.info('Configuration error: PATH_FILE environment variable is not set.', 'error')
            audio_file = os.path.join(path_file, audio_file)
            
            # Run diarization and transcription
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
            save_path = f"output/transcript_result_{meeting_id}.csv"
            txt_save_path = f"output/transcript_result_{meeting_id}.txt"
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
            
            # transcription_html = df.to_html(index=False, classes="table table-striped table-bordered")
            transcription.summary = summarized_meeting
            transcription.action = '\n'.join(action_items_list)
            transcription.diarization = transcription_html
            transcription.audio = audio_file
            transcription.keywords = keywords
            transcription.positive_percentage = positive_percentage
            transcription.negative_percentage = negative_percentage
            transcription.neutral_percentage = neutral_percentage
            transcription.status = 'completed'  # Set status to 'completed'
            db.session.commit()
            
            send_transcription_email(email,meeting_id,meeting_datetime)
            logging.info('backend transcription process completed successfully')
    except Exception as e:
        logging.error('error in function is: %s', str(e))
        transcription = Transcription.query.filter_by(meeting_id=meeting_id).first()
        transcription.status = 'pending'
        db.session.commit()

def send_transcription_email(email, meeting_id, meeting_datetime): 
    try:
        if isinstance(meeting_datetime, str):
            try:
                # Try to convert the string to a datetime object if it matches the format %Y%m%d_%H%M%S
                meeting_datetime = datetime.strptime(meeting_datetime, '%Y%m%d_%H%M%S')
            except ValueError:
                # If the format is not matched, handle accordingly or log the error
                logging.error(f"Incorrect datetime format: {meeting_datetime}")
                return
        with app.app_context():
            meeting_date_str = meeting_datetime.strftime('%Y%m%d_%H%M%S')
            link = url_for('share_meeting_data', meeting_id=meeting_id, meeting_date=meeting_date_str, _external=True)
            message = Message("Transcription Success", sender="info@ashlarglobal.biz", recipients=[email])
            message.body = (
    f"Dear User,\n\n"
    f"We are pleased to inform you that your meeting with ID {meeting_id} has been successfully processed.\n\n"
    f"To view the details, please visit the following link: {link}\n\n"
    f"If you have any questions or need further assistance, please feel free to contact our support team at management@ashlarglobal.com.\n\n"
    f"Best regards,\n"
    f"The AI NOTE GENIUS Team"
)
            mail.send(message)
    except Exception as e:
        logging.error(f"Error sending email: {e}")