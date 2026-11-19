import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import requests
import smtplib
import threading
import json
import re
import os

from email.message import EmailMessage
from urllib.parse import quote_plus
from dotenv import load_dotenv

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
WEATHER_API_KEY = OPENWEATHER_API_KEY
EMAIL_PASSWORD = EMAIL_APP_PASSWORD

engine = pyttsx3.init()
engine.setProperty("rate", 175)
engine.setProperty("volume", 1.0)

speech_lock = threading.Lock()
recognizer =sr.Recognizer()
reminder_timers =[]

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        print("Configuration error:", error)
        return {"custom_commands": {}, "knowledge_base": {} }
config = load_config()

def speak(text):
    print("Assistant:", text)
    with speech_lock:
        engine.say(text)
        engine.runAndWait()


def listen():
    try:
        with sr.Microphone() as source:
            print("\nListening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5 )
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=12)
        command = recognizer.recognize_google(audio, language="en-IN")
        print("You:", command)
        return command.lower().strip()

    except sr.WaitTimeoutError:
        speak("I did not hear anything.")
        return ""

    except sr.UnknownValueError:
        speak("Sorry, please repeat your command.")
        return ""

    except sr.RequestError:
        speak("Speech recognition service is unavailable.")
        return ""

    except OSError as error:
        print("Microphone error:", error)
        speak("Please check your microphone.")
        return ""

def detect_intent(command):
    text = command.lower().strip()
    if re.search(r"\b(stop|exit|quit|goodbye)\b", text):
        return "exit"

    if re.search(r"\b(send|compose)\b.*\bemail\b", text):
        return "email"
    
    if re.search(r"\b(remind|reminder)\b", text):
        return "reminder"

    if re.search(r"\b(weather|temperature|forecast)\b", text):
        return "weather"

    if re.search(r"\b(time|clock)\b", text):
        return "time"

    if re.search(r"\b(date|today|day)\b", text):
        return "date"

    if re.search(r"\b(search|google|look up)\b", text):
        return "search"

    if re.search(r"\b(hello|hi|hey)\b", text):
        return "greeting"

    if text.startswith(("who ", "what ", "when ", "where ", "why ", "how ")):
        return "knowledge"

    return "unknown"


def greeting():
    speak("Hello! How can I help you today?")

def tell_time():
    current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
    speak("The current time is " + current_time)

def tell_date():
    current_date = datetime.datetime.now().strftime("%d %B %Y")
    speak("Today's date is " + current_date)

def google_search(command):
    patterns = [
        r"search(?:\s+google)?(?:\s+for)?\s+(.+)",
        r"google\s+(.+)",
        r"look up\s+(.+)"
    ]
    topic = ""

    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            topic = match.group(1).strip()
            break

    if not topic:
        speak("Please tell me what you want to search.")
        return

    speak("Searching Google for " + topic)
    url = ("https://www.google.com/search?q=" + quote_plus(topic))
    webbrowser.open(url)


def get_weather(command):
    if not WEATHER_API_KEY:
        speak("Weather API key is missing. Please configure your environment.")
        return

    match = re.search(r"\b(?:in|for|at)\s+(.+)$", command, re.IGNORECASE)

    if not match:
        speak("Please tell me the city name.")
        return

    city = match.group(1).strip()
    city = re.sub( r"\s+(please|right now)$", "", city, flags=re.IGNORECASE)
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = { "q": city, "appid": WEATHER_API_KEY, "units": "metric"}

    try:
        response = requests.get(url, params=params,timeout=10)
        response.raise_for_status()
        data = response.json()

        temperature = data["main"]["temp"]
        description = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]

        speak(
            f"The weather in {city} is {description}. "
            f"Temperature is {temperature} degrees Celsius. "
            f"Humidity is {humidity} percent."
        )

    except requests.exceptions.HTTPError as error:
        if response.status_code == 401:
            speak("Your weather API key is invalid or not active.")
        elif response.status_code == 404:
            speak("I could not find that city.")
        else:
            speak("Weather service returned an error.")
        print("Weather error:", error)

    except requests.exceptions.RequestException as error:
        print("Weather connection error:", error)
        speak("Unable to connect to the weather service.")    


def send_email(command):
    pattern = ( r"send email to\s+(\S+@\S+)" r"\s+subject\s+(.+?)" r"\s+message\s+(.+)$")
    match = re.search(pattern, command, re.IGNORECASE)

    if not match:
        speak( "Please say: send email to recipient "
            "subject your subject message your message."
        )
        return

    recipient = match.group(1)
    subject = match.group(2).strip()
    body = match.group(3).strip()

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        speak("Email credentials are not configured.")
        return

    speak(f"You are about to send an email to {recipient}. "
        f"Subject: {subject}. "
        "Please say yes to confirm or no to cancel.")

    confirmation = listen()
    if not re.search(r"\b(yes|confirm)\b", confirmation):
        speak("Email cancelled.")
        return

    message = EmailMessage()
    message["From"] = EMAIL_ADDRESS
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(message)
        speak("Your email has been sent successfully.")

    except Exception as error:
        print("Email error:", error)
        speak("Sorry, I could not send the email.")

def reminder_alert(message):
    speak("Reminder! " + message)


def set_reminder(command):
    match = re.search(
        r"remind me in\s+(\d+)\s+"
        r"(seconds?|minutes?|hours?)\s+to\s+(.+)",
        command,
        re.IGNORECASE
    )

    if not match:
        speak("Please say, remind me in 30 minutes " "going out.")
        return

    amount = int(match.group(1))
    unit = match.group(2).lower()
    task = match.group(3).strip()

    if amount <= 0:
        speak("Please provide a positive reminder duration.")
        return

    if amount > 10000:
        speak("That reminder duration is too large.")
        return

    if unit.startswith("second"):
        seconds = amount

    elif unit.startswith("minute"):
        seconds = amount * 60

    else:
        seconds = amount * 3600
    timer = threading.Timer(seconds, reminder_alert, args=[task])
    timer.daemon = True
    timer.start()
    reminder_timers.append(timer)
    speak(f"Reminder set for {amount} {unit} " f"to {task}.")


def answer_question(command):
    knowledge = config.get("knowledge_base", {})
    normalized = command.lower().strip(" ?.")
    answer = knowledge.get(normalized)

    if answer:
        speak(answer)
        return

    for question, response in knowledge.items():
        keywords = question.split()
        if all(word in normalized for word in keywords):
            speak(response)
            return

    speak("I don't have an answer in my local knowledge base. "
        "Please add this question to config.json.")

    
def run_custom_command(command):
    commands = config.get("custom_commands", {})
    for phrase, details in commands.items():
        if phrase.lower() in command:
            action = details.get("action")
            if action == "open_url":
                url = details.get("url", "")
                if url.startswith(("https://", "http://")):
                    speak("Opening " + phrase)
                    webbrowser.open(url)

                else:
                    speak("This custom URL is not allowed.")
                return True

    return False


def process_command(command):
    if not command:
        return True

    intent = detect_intent(command)
    if intent == "exit":
        speak("Goodbye! Have a nice day.")
        return False

    elif intent == "greeting":
        greeting()

    elif intent == "time":
        tell_time()

    elif intent == "date":
        tell_date()

    elif intent == "search":
        google_search(command)

    elif intent == "weather":
        get_weather(command)

    elif intent == "email":
        send_email(command)

    elif intent == "reminder":
        set_reminder(command)

    elif intent == "knowledge":
        answer_question(command)

    elif run_custom_command(command):
        pass

    else:
        speak( "Sorry, I could not identify your command." "Please try again.")
    return True


def main():
    speak("Welcome to your voice assistant.")
    speak( "I can help with weather, email, reminders, "
        "time, date, and general knowledge.")

    while True:
        command = listen()

        if command:
            result = process_command(command)
            if result is False:
                break

        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        speak("Assistant stopped. Goodbye!")
