import os
from flask import Flask, render_template, redirect, url_for, request
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry
import requests

# Constants
OPEN_WEATHER_API_KEY = "5fed3257f497dc3c8282e41bf354430b"
ACCOUNT_SID = "ACd455f42c5bf06c805b5075033b1da34a"
AUTH_TOKEN = "1c3ecbe8b623d1ebaa31a67af561542a"
MY_LAT = 45.943439
MY_LONG = 10.278610

app = Flask(__name__)


#Update coordinates in CVS file
def update_coordinates():
    df = pd.read_csv('cities_airports.csv', usecols=['City'])
    cities_list = df['City'].tolist()

    city_coordinates = {}

    for city in cities_list:
        city_params = {
            "q": city,
            "appid": OPEN_WEATHER_API_KEY,
            "limit": 1
        }
        try:
            response = requests.get("http://api.openweathermap.org/geo/1.0/direct", params=city_params)
            response.raise_for_status()
            data = response.json()

            # If data is available, extract latitude and longitude
            if data:
                city_coordinates[city] = {
                    "lat": data[0]["lat"],
                    "lon": data[0]["lon"]
                }
            else:
                print(f"No coordinates found for {city}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {city}: {e}")

    df['Latitude'] = df['City'].map(lambda x: city_coordinates.get(x, {}).get('lat'))
    df['Longitude'] = df['City'].map(lambda x: city_coordinates.get(x, {}).get('lon'))

    df.to_csv('cities_airports.csv', index=False)


def get_sunshine_forecast(city, lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "sunshine_duration",
        "timezone": "GMT",
        "forecast_days": 16
    }

    response = openmeteo.weather_api(url, params=params)[0]

    daily = response.Daily()
    daily_sunshine_duration = daily.Variables(0).ValuesAsNumpy()

    daily_data = {"date": pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left"
    ), "sunshine_duration": daily_sunshine_duration / 3600}

    return pd.DataFrame(data=daily_data)



# Routes
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# Main execution
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)