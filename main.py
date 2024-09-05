import os
from flask import Flask, render_template, redirect, url_for, request
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
import pandas as pd
import requests

# Constants
OPEN_WEATHER_API_KEY = "5fed3257f497dc3c8282e41bf354430b"
ACCOUNT_SID = "ACd455f42c5bf06c805b5075033b1da34a"
AUTH_TOKEN = "1c3ecbe8b623d1ebaa31a67af561542a"
MY_LAT = 45.943439
MY_LONG = 10.278610

app = Flask(__name__)


# Data retrieval functions
def get_cities_data():
    df = pd.read_csv('cities_airports.csv', usecols=['City'])
    return df['City'].tolist()


#coordinates API function
def get_coordinates():
    cities_list = get_cities_data()
    city_coordinates = {}
    for city in cities_list:
        city_params = {
            "q": city,
            "appid": OPEN_WEATHER_API_KEY,
            "limit": 1
        }
        response = requests.get("http://api.openweathermap.org/geo/1.0/direct", params=city_params)
        response.raise_for_status()
        data = response.json()

        if data:
            city_coordinates[city] = {
                "lat": data[0]["lat"],
                "lon": data[0]["lon"]
            }
        else:
            print(f"No coordinates found for {city}")

    return city_coordinates


def get_weather():
    weather_params = {
        "lat": MY_LAT,
        "lon": MY_LONG,
        "appid": OPEN_WEATHER_API_KEY,
        "cnt": 16,
    }
    response = requests.get("https://api.openweathermap.org/data/2.5/forecast", params=weather_params)
    response.raise_for_status()
    return response.json()

# Routes
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# Main execution
if __name__ == '__main__':
    print(get_coordinates())
    app.run(host='0.0.0.0', port=5001, debug=True)