import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv_vault import load_dotenv

# Load env file variable
load_dotenv()

# Retrieve token
token = os.getenv("WEATHER_TOKEN")

# Define Google API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# List of ski areas
ski_areas = [
    "Les Trois Vallées",
    "Sölden",
    "Chamonix-Mont Blanc",
    "Val di Fassa",
    "Salzburger Sportwelt",
    "Alpenarena Flims-Laax-Falera",
    "Kitzsteinhorn Kaprun",
    "Ski Arlberg",
    "Espace Killy",
    "Spindleruv Mlyn"
]


def getWeatherForecast(api_key, city):
    # Function to fetch weather forecast from OpenWeatherMap API
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()
    return data["list"][:5]  # only first 5 days


def formatWeatherForecast(weather_forecast):
    # Function to format weather forecast data
    forecasts = []
    for forecast in weather_forecast:
        date = forecast["dt_txt"].split()[0]
        temperature = forecast["main"]["temp"]
        description = forecast["weather"][0]["description"]
        wind_speed = forecast["wind"]["speed"]
        precipitation = forecast["rain"]["3h"] if "rain" in forecast else 0

        # Append formatted forecast to forecasts list
        forecasts.append(f"Date: {date}\nTemperature: {temperature}°C\nDescription: {description}\nWind Speed: {wind_speed} m/s\nPrecipitation: {precipitation} mm")

    return "\n\n".join(forecasts)


def main():
    # Main function
    openweathermap_api_key = token
    google_credentials_file = "credentials.json"

    # Fetching weather forecast for each ski area
    forecasts_text = ""
    for area in ski_areas:
        weather_forecast = getWeatherForecast(openweathermap_api_key, area)
        area_forecast_text = f"{area} Forecast:\n\n{formatWeatherForecast(weather_forecast)}\n\n"
        forecasts_text += area_forecast_text

    # Sending email
    receiver_email = input("Give your E-mail: ")
    send_email(google_credentials_file, receiver_email, forecasts_text)


def send_email(credentials_file, receiver_email, message):
    # Function to send email using Gmail API
    creds = None
    if not os.path.exists("token.json"):
        pass
    else:
        # Load Google credentials from token file
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(requests.Request())
        else:
            # Authenticate user and generate credentials
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Write credentials to token file
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # Build Gmail service
        service = build("gmail", "v1", credentials=creds)

        # Create a plain text message
        msg = MIMEMultipart()
        msg['to'] = receiver_email
        msg['subject'] = "Weather Forecast for Ski Areas"

        # Attach the plain text message
        msg.attach(MIMEText(message, 'plain'))

        # Encode the message as base64
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        # Send the email
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
