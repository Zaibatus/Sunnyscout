import os
import pandas as pd
import requests
from flask import Flask, render_template, redirect, url_for, request
import openmeteo_requests
import requests_cache
from retry_requests import retry

# Constants
OPEN_WEATHER_API_KEY = "5fed3257f497dc3c8282e41bf354430b"
ACCOUNT_SID = "ACd455f42c5bf06c805b5075033b1da34a"
AUTH_TOKEN = "1c3ecbe8b623d1ebaa31a67af561542a"

app = Flask(__name__)

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


# Data processing functions
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


def get_cities_data():
    df = pd.read_csv('cities_airports.csv', usecols=['City', 'Latitude', 'Longitude'])
    return df.to_dict('records')


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

    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        ),
        "sunshine_duration": daily_sunshine_duration / 3600
    }

    return pd.DataFrame(data=daily_data)


# Flask routes
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/results")
def result():
    cities = get_cities_data()
    city_sunshine = []

    for city in cities:
        if pd.isna(city['Latitude']) or pd.isna(city['Longitude']):
            # Instead of printing, we could log this information
            app.logger.warning(f"Missing coordinates for {city['City']}. Skipping forecast.")
            continue

        forecast = get_sunshine_forecast(city['City'], city['Latitude'], city['Longitude'])
        if forecast is not None:
            avg_sunshine = forecast['sunshine_duration'].mean()
            total_sunshine = forecast['sunshine_duration'].sum()

            if avg_sunshine >= 11:
                city_sunshine.append({
                    'city': city['City'],
                    'avg_sunshine': avg_sunshine,
                    'total_sunshine': total_sunshine
                })

    # Sort cities by total sunshine and get top 5
    top_5_cities = sorted(city_sunshine, key=lambda x: x['total_sunshine'], reverse=True)[:5]

    # Prepare data for the template
    result_data = []
    for rank, city_data in enumerate(top_5_cities, 1):
        result_data.append({
            'rank': rank,
            'city': city_data['city'],
            'avg_sunshine': f"{city_data['avg_sunshine']:.2f}",
            'total_sunshine': f"{city_data['total_sunshine']:.2f}"
        })

    return render_template("results.html", results=result_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)