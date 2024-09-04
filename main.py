from flask import Flask, render_template, redirect, url_for, request
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
import os
import requests

'''
Make sure the required packages are installed. Type: pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)

OPEN_WEATHER_API_KEY = "5fed3257f497dc3c8282e41bf354430b"
account_sid = "ACd455f42c5bf06c805b5075033b1da34a"
auth_token = "1c3ecbe8b623d1ebaa31a67af561542a"
MY_LAT = 45.943439
MY_LONG = 10.278610

cities_list = ["Milan", "Madrid", "Berlin", "Barcelona", "London", "Rome", "Geneva"]


def get_coordinates(city):
    city_params = {
        "q": city,
        "appid": OPEN_WEATHER_API_KEY,
    }

    response = requests.get(url="http://api.openweathermap.org/geo/1.0/direct", params=city_params)
    response.raise_for_status()
    city_data = response.json()
    return city_data


#Get weather forecasting via API call
def get_weather():
    weather_params = {
        "lat": MY_LAT,
        "lon": MY_LONG,
        "appid": OPEN_WEATHER_API_KEY,
        "cnt": 16,
    }

    response = requests.get(url="https://api.openweathermap.org/data/2.5/forecast", params=weather_params)
    response.raise_for_status()
    weather_data = response.json()
    return weather_data


for city in cities_list:
    city_details = get_coordinates(city)
    city_lat = city_details[0]['lat']
    city_long = city_details[0]['lon']
    print(f"{city}: lat:{city_lat} lon:{city_long}")



@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
