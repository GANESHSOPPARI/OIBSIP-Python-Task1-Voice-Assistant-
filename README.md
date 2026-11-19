# Python Voice Assistant

## Description

An Python voice assistant that recognizes
English voice commands, identifies user intents,
and performs useful automation tasks.


## Features

1. Voice recognition
2. Natural language intent recognition
3. Text-to-speech responses
4. Email automation
5. Timed reminders
6. Live weather information
7. General knowledge using a local knowledge base
8. Custom commands using JSON
9. Google search
10. Date and time information

## Technologies

- Python
- SpeechRecognition
- pyttsx3
- PyAudio
- Requests
- Python-dotenv
- SMTP
- JSON
- Regular Expressions
- Threading


## Installation

1. Create a virtual environment.
2. Activate the environment.
3. Install dependencies.

Install packages:

```bash
pip install -r requirements.txt
```

## Run the Application

```bash
python main.py
```


## Privacy and Security

- Microphone audio is captured when the assistant listens.
- Google speech recognition processes audio online.
- Weather requests share the requested city with OpenWeatherMap.
- Email credentials are stored in environment variables.
- Email sending requires voice confirmation.
- Reminder messages are held in application memory.
- The application does not intentionally save audio recordings.
- Custom commands are loaded from config.json.
- Do not upload .env or private credentials to GitHub.