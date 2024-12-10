#  AI NOTE GENIUS

## Description
AI Note Genius is an innovative project designed to enhance note-taking during Zoom meetings through the power of artificial intelligence. Leveraging Flask for the backend, OpenAI for advanced AI capabilities, pyannote.audio for audio analysis and the C++ Linux SDK for Zoom integration, this application provides real-time transcription and summarization of meetings, making information retrieval and documentation more efficient.

## Features
Real-Time Transcription: Converts spoken language during Zoom meetings into text.
Meeting Summarization: Utilizes OpenAI LLM to generate concise summaries of meetings.
Audio Analysis: Detects speaker changes and annotates audio with speaker labels.
Easy Integration: Seamlessly integrates with Zoom meetings on your account.

## Installation
### Prerequisites
- Linux Operating System / Windows
- Python 3.8 or higher
- Zoom account and Zoom App Credentials

## Setup

- Clone the Repository : **https://github.com/ashlarglobal/AI_Note_Taker_v1.git**

### Download the required packages in requirements.txt

- **pip install -r requirements.txt**

## Environment Variables

- Set up the environment variables according to env.example.

## Docker Setup

### Create a Docker Hub Account:

- Visit Docker Hub and sign up for an account.
- Verify your email and log in.
- Push Base Image in meetingsdk-linux-raw-recording-sample to Docker Hub:

## HuggingFace Setup
- Obtain huggingface token for pyanote diarization library. Library being used is : **https://huggingface.co/pyannote/speaker-diarization-3.1**
- Token can be obtained from : **https://huggingface.co/settings/tokens**. Set it as read.

## OpenAI Setup
- Obtain OpenAI key to use GPT models for notes generation. Key can be generated from here : **http://platform.openai.com/settings/organization/billing/overview**

## Database Setup
- Create local test database by running the init_db.py file. 
- **python3 init_db.py**

## Run the Flask Application

**python app.py**

## Usage
- After starting the Flask server, sign in via Zoom, sync up with your Google Calendar. Create Meetings, the meeting bot will join and record the meeting. The recording will be processed and available to you with notes.

## Contribution Guidelines

### Create Your Feature Branch:
- Always use a branch dedicated to your feature. This helps you to keep your changes organized and separate from the main project.
- **git checkout -b feature/AmazingFeature**
### Commit Your Changes:
- Write meaningful commit messages. This helps others to understand the history of the project and your contribution.
- **git commit -m 'Add some AmazingFeature'**
### Push to the Branch:
- **git push origin feature/AmazingFeature**
## Open a Pull Request (PR):
- Go to repository on GitHub and you’ll see a Compare & pull request button. Click on it, review your changes, and submit your pull request. Provide as much information as possible in the PR's description: explain the changes you made and their purpose, any specific details others might need to understand, etc.

## Review & Merge 
- Once your pull request is reviewed and approved by the maintainers, it can be merged into the main project.

## Note
-  Create a **log.log** file in root of project to obtain real time logging.
