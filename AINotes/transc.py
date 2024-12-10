import whisper
import subprocess
import torch
import os
import wave
import contextlib
import glob
from pyannote.audio import Pipeline
import time
import re
from pydub import AudioSegment 
import os
from dotenv import load_dotenv
import numpy as np
from textblob import TextBlob
from collections import Counter
import logging
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

load_dotenv()

log_file_path = os.getenv('LOG_FILE')
logging.basicConfig(filename=log_file_path, filemode='a', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
token=os.getenv('HUGGINGFACE_TOKEN')
pipeline = Pipeline.from_pretrained(
  "pyannote/speaker-diarization-3.1",
  use_auth_token=token)

model = whisper.load_model('large', device = device)

pipeline.to(device)

def pcm_to_wav_ffmpeg(pcm_file_path, wav_file_path=None, channels=1, sample_rate=32000):
    """
    Convert a PCM audio file to WAV format using FFmpeg.

    Parameters:
    - pcm_file_path (str): Path to the PCM audio file.
    - wav_file_path (str, optional): Path to the output WAV file. If not provided, the file name will be derived from the PCM file path.
    - channels (int, optional): Number of audio channels. Defaults to 1.
    - sample_rate (int, optional): Sample rate of the audio. Defaults to 32000.

    Returns:
    - Tuple[str, float]: Path to the converted WAV file, and its duration in seconds. If the conversion fails, None will be returned for both values.
    """
    if wav_file_path is None:
        wav_file_path = os.path.splitext(pcm_file_path)[0] + '.wav'

    command = [
        'ffmpeg',
        '-f', 's16le',
        '-ar', str(sample_rate),
        '-ac', str(channels),
        '-i', pcm_file_path,
        wav_file_path
    ]

    try:
        # Capture standard error output to diagnose issues
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logging.info(f"ffmpeg command failed: {e}\nError output:\n{e.stderr.decode()}")
        return None, None

    try:
        with contextlib.closing(wave.open(wav_file_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
    except wave.Error as e:
        return wav_file_path, None

    if duration is not None:
        os.remove(pcm_file_path)

    return wav_file_path, duration

folder_path = os.getenv('ZOOM_MEETING_FOLDER')
def get_audio_path_by_meeting_id(folder_path, meeting_id, date_time):
    """
    Searches for PCM audio files in a specified folder that match a given meeting ID and date-time, returning the path to the first matching file.

    Parameters:
    - folder_path (str): The path to the folder where audio files are stored.
    - meeting_id (str or int): The meeting ID used to identify the relevant audio files.
    - date_time (datetime): The datetime object used to match the file naming pattern.

    Returns:
    - str or None: The path to the first audio file that matches the meeting ID and date-time, if any are found.
    """
    search_pattern = os.path.join(folder_path, f'{meeting_id}_{date_time}.*')
    audio_files = glob.glob(search_pattern)
    audio_files = [file for file in audio_files if file.endswith('.pcm') or file.endswith('.wav')]
    if not audio_files:
        logging.info(f"No .pcm files found for meeting ID {meeting_id} at {date_time}.")
        return None
    return audio_files[0]

def convert_video_to_audio(video_file_path):
    """
    Converts a video file to an audio file in WAV format using FFmpeg, ensuring the output file does not overwrite existing files.

    Parameters:
    - video_file_path (str): The file path of the video to be converted.

    Returns:
    - tuple: A tuple containing the name of the converted audio file and its duration in seconds.

    Raises:
    - ValueError: If no video file path is provided.

    Note: Requires FFmpeg to be installed and accessible from the system's command line.
    """
    if video_file_path is None:
        raise ValueError("Error: no video input provided")

    output_folder = os.getenv('OUTPUT_FOLDER_PATH')
    os.makedirs(output_folder, exist_ok=True)


    base_name, file_extension = os.path.splitext(os.path.basename(video_file_path))
    audio_file_name = base_name + ".wav"
    final_audio_path = os.path.join(output_folder, audio_file_name)

    if os.path.exists(final_audio_path):
        unique_identifier = time.strftime("_%Y%m%d-%H%M%S")
        # Corrected the way unique_identifier is appended
        audio_file_name = base_name + unique_identifier + ".wav"
        final_audio_path = os.path.join(output_folder, audio_file_name)


    os.system(f'ffmpeg -i "{video_file_path}" -ar 16000 -ac 1 -c:a pcm_s16le "{final_audio_path}"')

    try:
        with contextlib.closing(wave.open(final_audio_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
    except wave.Error as e:
        logging.info(f"Error reading the converted audio file: {e}")
        duration = 0  

    return audio_file_name, duration

def is_audio_mostly_silent(audio_path, silence_threshold=-40, min_silence_len=500, silence_percentage_threshold=90):
    """
    Determines if an audio file is mostly silent.

    Parameters:
    - audio_path (str): Path to the audio file.
    - silence_threshold (int): The silence threshold in dB. Lower values mean more stringent silence detection.
    - min_silence_len (int): The minimum length of a silence to be considered in milliseconds.
    - silence_percentage_threshold (int): Percentage of audio that must be silent to consider the entire file as 'mostly silent'.

    Returns:
    - bool: True if the audio is mostly silent, False otherwise.
    """
    audio = AudioSegment.from_file(audio_path)
    total_duration_ms = len(audio)

    nonsilent_periods = detect_nonsilent(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_threshold
    )

    # Calculate total nonsilent duration
    total_nonsilent_duration = sum((end - start for start, end in nonsilent_periods))

    # Calculate the percentage of the audio that is nonsilent
    nonsilent_percentage = (total_nonsilent_duration / total_duration_ms) * 100

    # Check if the nonsilent part is less than the threshold to proceed
    is_mostly_silent = nonsilent_percentage < (100 - silence_percentage_threshold)
    return is_mostly_silent





def run_diarization(pipeline, audio_path, user_id,unique_filename):
    """
    Performs speaker diarization on an audio file using a pre-trained pipeline.

    Parameters:
    - pipeline (Pipeline): Pre-trained pipeline for speaker diarization.
    - audio_path (str): Path to the audio file for diarization.
    - user_id (int): Unique identifier for the user.
    - unique_filename (str): Unique filename for the diarization output.

    Returns:
    - str: Path to the diarization output file.
    """
    try:
        diarization = pipeline(audio_path)
        output_dir=os.getenv('DIARIZATION_DIR')
        output=os.path.join(output_dir, str(user_id))
        os.makedirs(output, exist_ok=True)
        filename = f"{unique_filename}_diarization.txt"
        diarization_file_path = os.path.join(output, filename)
        with open(diarization_file_path, "w") as text_file:
            text_file.write(str(diarization))
        return diarization_file_path 
    
    except Exception as e:
        logging.info(f"Error: {e}")
        # Optionally, return None or re-raise the exception to signal the error upstream
        return None

def parse_diarization_file(diarization_file):
    """
    Parses a diarization file and returns a dictionary containing speaker segments and their timestamps.

    Parameters:
    - diarization_file (str): The path to the diarization file.

    Returns:
    dict: A dictionary where keys are speaker labels and values are lists of dictionaries. Each dictionary
          contains 'tart_ms', 'end_ms', and 'egments' keys. 'tart_ms' and 'end_ms' represent the
          start and end timestamps of the speaker segment in milliseconds. 'egments' contains the
          original lines from the diarization file that belong to the speaker segment.
    """
    with open(diarization_file, "r") as file:
        lines = file.readlines()

    speakers = {}
    for line in lines:
        parts = line.strip().split()
        start_time, end_time = re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', line)[:2]
        start_ms = millisec(start_time)
        end_ms = millisec(end_time)
        speaker_label = parts[-1]
        if speaker_label not in speakers:
            speakers[speaker_label] = []

        # Check if the current segment is contiguous with the previous one
        if speakers[speaker_label] and speakers[speaker_label][-1]['end_ms'] + 1000 >= start_ms:  # allow 1-second gap
            # If contiguous, merge the time
            speakers[speaker_label][-1]['end_ms'] = max(speakers[speaker_label][-1]['end_ms'], end_ms)
        else:
            # Otherwise, start a new segment
            speakers[speaker_label].append({
                'start_ms': start_ms,
                'end_ms': end_ms,
                'segments': [line]
            })

    return speakers

def process_audio_file(audio_path, spacer_duration=2000):
    """
    Appends a silent audio segment to the beginning of an existing WAV file and overwrites the original file.

    Parameters:
    - audio_path (str): The file path of the original WAV audio file.
    - spacer_duration (int): Duration of the silent audio to prepend, in milliseconds.

    Returns:
    - str: The path to the overwritten audio file.
    """
    # Create a silent audio segment
    spacer = AudioSegment.silent(duration=spacer_duration)
    
    # Load the original audio
    audio = AudioSegment.from_wav(audio_path)
    
    # Append the silent segment to the beginning of the original audio
    modified_audio = spacer.append(audio, crossfade=0)
    
    # Overwrite the original file with the modified audio
    modified_audio.export(audio_path, format='wav')
    
    return audio_path


def millisec(timeStr):
  """
    Converts a time string in the format "hh:mm:ss.sss" to milliseconds.

    Parameters:
    timeStr (str): The time string to convert. It should be in the format "hh:mm:ss.sss".

    Returns:
    int: The time in milliseconds.

    Example:
    >>> millisec("01:23:45.678")
    50245678
    """
  spl = timeStr.split(":") 
  s = (int)((int(spl[0]) * 60 * 60 + int(spl[1]) * 60 + float(spl[2]) )* 1000) 
  return s 


def format_timestamp(milliseconds):
    """
    Converts milliseconds to a formatted timestamp string 'HH:MM:SS'.

    Parameters:
    - milliseconds (int): Time in milliseconds.

    Returns:
    - str: Formatted timestamp.
    """
    seconds = milliseconds // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"



def transcribe_segments(speakers, modified_audio_path, model,user_id):
    """
    Transcribes audio segments by speaker, appending formatted timestamps and returning structured results.

    Parameters:
    - speakers (dict): Dictionary of speakers and their corresponding audio segments.
    - modified_audio_path (str): Path to the audio file.
    - model: Transcription model (e.g., Whisper).

    Returns:
    - dict: Dictionary containing transcriptions and timestamps indexed by speaker.
    """
    audio = AudioSegment.from_wav(modified_audio_path)
    results = {}
    output_dir=os.getenv('DIARIZATION_DIR')
    output=os.path.join(output_dir, str(user_id))
    os.makedirs(output, exist_ok=True)
    for speaker, segments in speakers.items():
        for segment_info in segments:
            # Extract the audio segment
            segment_audio = audio[segment_info['start_ms']:segment_info['end_ms']]
            segment_path = os.path.join(output, f'{speaker}_{segment_info["start_ms"]}-{segment_info["end_ms"]}.wav')
            segment_audio.export(segment_path, format='wav')

            # Transcribe the audio segment
            transcription = model.transcribe(audio=segment_path, language="en")

            # Check if there are already entries for this speaker and add if not
            if speaker not in results:
                results[speaker] = []

            # Append the transcription with formatted timestamps
            results[speaker].append({
                'start': format_timestamp(segment_info['start_ms']),
                'end': format_timestamp(segment_info['end_ms']),
                'transcription': transcription['text']
            })

    return results

def process_transcription(S2T_Data, output_path):
    """
    Processes transcription data to format and write it to a specified output file.

    This function takes a DataFrame containing transcription data, ensures each row has a speaker label,
    formats each row into a "Speaker: Text" format, and writes the formatted text to an output file. It also
    cleans up extra spaces in the transcription. Finally, it reads back and returns the content of the output file.

    Parameters:
    - S2T_Data (DataFrame): The transcription data as a pandas DataFrame with 'Speaker' and 'Text' columns.
    - output_path (str): The file path where the processed transcription text should be saved.

    Returns:
    - str: The entire processed transcription text as a single string.

    Note: This function assumes the presence of the 'Text' column and optionally the 'Speaker' column in the input
    DataFrame. Rows without a 'Speaker' will be labeled as 'Unknown Speaker'.
    """
    # Ensure 'Speaker' column exists
    if 'Speaker' not in S2T_Data.columns:
        S2T_Data['Speaker'] = 'Unknown Speaker'

     # Remove excessive repetitions and filler words
    def clean_text(text):
        # Ensure the input is a string
        if not isinstance(text, str):
            text = str(text) if text is not None else ''
        # Normalize spacing and lowercasing
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)

        # Remove excessive fillers and normalize repetitive acknowledgements
        text = re.sub(r'\b(thank you|uh|um|ah|okay|right|yes)\b', '', text)
        text = re.sub(r'\b(yeah|so)\b', '', text)

        # Reduce character and word repetitions
        text = re.sub(r'(.)\1{2,}', r'\1', text)  # Simplify extended character repetitions
        text = re.sub(r'(\b\w+\b)( \1\b)+', r'\1', text)  # Remove consecutive repetitive words

        # Cluster and reduce overused phrases
        text = re.sub(r'(thank you\s*)+', ' thank you ', text)
        
        # Final trim and space normalization
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    # Creating a list to store the formatted lines
    formatted_lines = []

    # Iterate over the DataFrame rows
    for _, row in S2T_Data.iterrows():
        # Accessing each element safely using the .get method with a default value
        speaker = row.get('Speaker', 'Unknown Speaker')
        text = row.get('Text', '')
        text = clean_text(row.get('Text', ''))

        formatted_line = f"{speaker}: {text}"
        formatted_lines.append(formatted_line)

    # Removing extra spaces within the line and writing to the output file
    with open(output_path, 'w') as f:
        for line in formatted_lines:
            modified_line = re.sub('\s+', ' ', line.strip())
            f.write(modified_line + '\n')

    # Reading the processed file
    with open(output_path, 'r') as f:
        modified_text = f.read()

    return modified_text


def analyze_sentiments(transcripts):
    sentiment_counts = Counter({'positive': 0, 'negative': 0, 'neutral': 0})
    sentiment_results = []  # Initialize a new list to hold the sentiment analysis results
    for transcript in transcripts:
        text = transcript['text']  
        if not text.strip():
            continue  # Skip empty text
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity
        if sentiment > 0:
            sentiment_counts['positive'] += 1
            sentiment_result = 'positive'
        elif sentiment < 0:
            sentiment_counts['negative'] += 1
            sentiment_result = 'negative'
        else:
            sentiment_counts['neutral'] += 1
            sentiment_result = 'neutral'
        # Append the sentiment result to the new list
        sentiment_results.append({'start': transcript['start'], 'end': transcript['end'], 'speaker': transcript['speaker'], 'text': transcript['text'], 'sentiment': sentiment_result})

    total_transcripts = len(transcripts)
    if total_transcripts > 0:
        positive_percentage = (sentiment_counts['positive'] / total_transcripts) * 100
        negative_percentage = (sentiment_counts['negative'] / total_transcripts) * 100
        neutral_percentage = (sentiment_counts['neutral'] / total_transcripts) * 100
    else:
        logging.info('no text could be obtained')
        positive_percentage, negative_percentage, neutral_percentage = 0, 0, 0

    return sentiment_results, sentiment_counts, positive_percentage, negative_percentage, neutral_percentage


