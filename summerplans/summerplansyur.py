import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv_vault import load_dotenv

# kleurjes en bold voor text in mail
class color:
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    NOTBOLD = '\033[0m'
    start = "\033[1m"
    end = "\033[0;0m"

# Load env file variable
load_dotenv()

# Retrieve token
token = os.getenv("WEATHER_TOKEN")

# Define Google API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# List of ski areas with their latitude and longitude
ski_areas = {
    "Ankara, Turkey": (39.9334, 32.8597),
    "Athens, Greece": (37.9838, 23.7275),
    "Valletta, Malta": (35.8989, 14.5146),
    "Sardinia, Italy": (40.1209, 9.0129),
    "Sicily, Italy": (37.5990, 14.0154),
    "Nicosia, Cyprus": (35.1856, 33.3823),
    "Mallorca, Spain": (39.6953, 3.0176),
    "Lagos, Portugal": (37.1028, -8.6741),
    "Mauritius": (-20.3484, 57.5522),
    "Bucharest, Romania": (44.4268, 26.1025)
}

average_temp = 0
average_rain = 0




def getWeatherForecast(api_key, latitude, longitude):
    # Function to fetch weather forecast from OpenWeatherMap API
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()

    # Calculate the average temperature and rainfall for the first 5 days
    total_temp = 0
    total_rain = 0
    for day in data["list"][:5]:
        total_temp += day["main"]["temp"]  # get temperature
        if 'rain' in day:
            total_rain += day["rain"].get('3h', 0)  # get rainfall data if available

    average_temp = total_temp / 5  # Calculate average temperature
    average_rain = total_rain / 5 if total_rain > 0 else 0  # Calculate average rainfall if no rain = 0

    return average_temp, average_rain


# Calculate score based on temperature and rainfall preference
def calculate_score(average_temp, chosentemp, average_rain, rain_preference, chosenrain_threshold):
    score = 0

    # Temperature scoring
    if abs(average_temp - chosentemp) <= 1:
        score = 6
    elif abs(average_temp - chosentemp) <= 2:
        score = 5
    elif abs(average_temp - chosentemp) <= 3:
        score = 4
    elif abs(average_temp - chosentemp) <= 5:
        score = 3
    elif abs(average_temp - chosentemp) <= 7:
        score = 2
    elif abs(average_temp - chosentemp) <= 10:
        score = 1

    # Rainfall scoring
    if chosenrain_threshold is not None:
        if average_rain <= chosenrain_threshold:
            score += 4

    return score


def main():
    # Fetch API key and google credentials
    openweathermap_api_key = token
    google_credentials_file = "credentials.json"

    # Ask for user preferences
    chosentemp = float(input("How hot do you want it to be in °C: "))

    # Ask for rainfall preference
    print("Rainfall Preference:")
    print("1: Less than 1mm")
    print("2: Less than 2mm")
    print("3: Doesn't matter")
    rain_preference = int(input("Choose your rainfall preference: "))

    # Define the corresponding rainfall thresholds
    if rain_preference == 1:
        chosenrain_threshold = 1
    elif rain_preference == 2:
        chosenrain_threshold = 2
    else:
        chosenrain_threshold = None

    # Fetching weather forecast for each ski area and calculating scores
    forecasts_text = ""
    ski_areas_with_scores = {}  # Dictionary to store ski areas with their scores
    for area, (latitude, longitude) in ski_areas.items():
        average_temp, average_rain = getWeatherForecast(openweathermap_api_key, latitude, longitude)
        score = calculate_score(average_temp, chosentemp, average_rain, rain_preference, chosenrain_threshold)
        ski_areas_with_scores[area] = {"score": score, "average_temp": average_temp, "average_rain": average_rain}

    # Sort ski areas based on their scores
    sorted_ski_areas = sorted(ski_areas_with_scores.items(), key=lambda x: x[1]["score"], reverse=True)


    # Generate forecasts text and rank the locations
    # rank the locations
    rank = 1
    for index, (area, data) in enumerate(sorted_ski_areas):
        # this is the location
        area_forecast_text = f"{rank}. {area} Forecast:\n"

        # This is the average temp
        area_forecast_text += f"      Average Temperature: {round(data['average_temp'] )}°C\n"


        # Include rain value conditions in the email content
        if data['average_rain'] == 0:
            area_forecast_text += "      No rain expected.\n"
        elif 0 < data['average_rain'] < 2:
            area_forecast_text += "      Light rain expected.\n"
        else:
            area_forecast_text += "      Heavy rain expected.\n"

        forecasts_text += area_forecast_text + "\n\n"

        # Increment the rank
        rank += 1

        # Break the loop if rank exceeds 10
        if rank > 10:
            break

    # Sending email and asking to input mail of reciever
    receiver_email = input("Give your E-mail: ")
    send_email(google_credentials_file, receiver_email, forecasts_text)



def send_email(credentials_file, receiver_email, message):
    # Function to send email using Gmail API
    creds = None
    # If email dont exist pass
    if not os.path.exists("token.json"):
        pass
    else:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # Try to refresh token and try again when creds not valid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        msg = MIMEMultipart()
        # filling the reciever and subject
        msg['to'] = receiver_email
        msg['subject'] = "Weather Forecast for Ski Areas"
        msg.attach(MIMEText(message, 'plain'))
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()

    # If there is a error show this
    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
