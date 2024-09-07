import os
import pandas as pd
import requests
from flask import Flask, render_template, redirect, url_for, request, jsonify
import openmeteo_requests  # should we add this to the requirements.txt?
import requests_cache  # should we add this to the requirements.txt?
from retry_requests import retry  # should we add this to the requirements.txt?
from math import radians, sin, cos, sqrt, atan2
from requests.exceptions import RequestException
import time
from flight_search import FlightSearch
import json

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


def update_iata_codes():
    flight_search = FlightSearch()
    df = pd.read_csv('cities_airports.csv')

    iata_codes = []
    for city in df['City']:
        iata_code = flight_search.get_destination_code(city)
        iata_codes.append(iata_code)
        time.sleep(1)  # Add a delay to avoid rate limiting

    df['IATA_Code'] = iata_codes
    df.to_csv('cities_airports.csv', index=False)
    print("IATA codes have been added to the CSV file.")


def get_cities_data():
    df = pd.read_csv('cities_airports.csv', usecols=['City', 'Latitude', 'Longitude', 'IATA_Code', 'Country', 'Island', 'Capital', 'EU', 'Schengen'])
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

    try:
        app.logger.debug(f"Requesting forecast for {city} with params: {params}")
        response = openmeteo.weather_api(url, params=params)
        app.logger.debug(f"Received response for {city}")

        if not response:
            app.logger.error(f"Empty response for {city}")
            return None

        daily = response[0].Daily()
        daily_sunshine_duration = daily.Variables(0).ValuesAsNumpy()

        app.logger.debug(f"Sunshine duration for {city}: {daily_sunshine_duration}")

        daily_data = {
            "date": pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left"
            ).tz_convert('UTC'),
            "sunshine_duration": daily_sunshine_duration / 3600
        }

        app.logger.debug(f"Successful forecast retrieval for {city}")
        return pd.DataFrame(data=daily_data)
    except Exception as e:
        app.logger.error(f"Error getting forecast for {city}: {str(e)}")
        return None


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return round(distance, 2)


@app.route('/get_cities')
def get_cities():
    df = pd.read_csv('europe_cities.csv')
    cities = df['city'].tolist()
    return jsonify(cities)


# Flask routes
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/results")
def result():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    current_location = request.args.get('current_location')
    preferences = json.loads(request.args.get('preferences', '{}'))
    distance_preference = request.args.get('distance', '')

    if not all([start_date, end_date, current_location]):
        return redirect(url_for('home'))

    start_date = pd.to_datetime(start_date).tz_localize('UTC')
    end_date = pd.to_datetime(end_date).tz_localize('UTC')

    # Adjust date range to be within the next 16 days
    today = pd.Timestamp.now().tz_localize('UTC').floor('D')
    forecast_end = today + pd.Timedelta(days=15)
    start_date = max(start_date, today)
    end_date = min(end_date, forecast_end)
    date_range = pd.date_range(start=start_date, end=end_date, tz='UTC')

    cities = get_cities_data()
    
    # Get current location coordinates
    europe_cities_df = pd.read_csv('europe_cities.csv')
    airports_df = pd.read_csv('cities_airports.csv')

    current_city = europe_cities_df[europe_cities_df['city'].str.lower() == current_location.lower()].iloc[0] if not europe_cities_df[europe_cities_df['city'].str.lower() == current_location.lower()].empty else None

    if current_city is not None:
        current_lat, current_lon = current_city['lat'], current_city['lng']
        
        # Check if the current location is in the airports database
        current_airport = airports_df[airports_df['City'].str.lower() == current_location.lower()]
        
        if current_airport.empty:
            # Find the closest airport
            closest_city, closest_airport_code = find_closest_airport(current_lat, current_lon, airports_df)
            current_location_code = closest_airport_code
            print(f"No airport found for {current_location}. Using closest airport: {closest_city} ({closest_airport_code})")
        else:
            current_location_code = current_airport.iloc[0]['IATA_Code']
    else:
        current_lat, current_lon = None, None
        current_location_code = None

    # Filter cities based on preferences
    filtered_cities = filter_cities_by_preferences(cities, preferences, current_lat, current_lon, distance_preference)
    
    city_sunshine = []

    for city in filtered_cities:
        if pd.isna(city['Latitude']) or pd.isna(city['Longitude']):
            app.logger.warning(f"Missing coordinates for {city['City']}. Skipping forecast.")
            continue
        
        app.logger.debug(f"Fetching forecast for {city['City']}")
        forecast = get_sunshine_forecast(city['City'], city['Latitude'], city['Longitude'])
        if forecast is not None:
            app.logger.debug(f"Forecast data for {city['City']}: {forecast.to_dict()}")
            forecast_in_range = forecast[forecast['date'].isin(date_range)]
            if not forecast_in_range.empty:
                avg_sunshine = forecast_in_range['sunshine_duration'].mean()
                total_sunshine = forecast_in_range['sunshine_duration'].sum()

                city_data = {
                    'city': city['City'],
                    'country': city['Country'],
                    'avg_sunshine': avg_sunshine,
                    'total_sunshine': total_sunshine
                }

                if current_lat is not None and current_lon is not None:
                    distance = haversine_distance(current_lat, current_lon, city['Latitude'], city['Longitude'])
                    city_data['distance'] = distance
                else:
                    city_data['distance'] = 'N/A'

                city_sunshine.append(city_data)
                app.logger.debug(
                    f"Added {city['City']} to results with avg_sunshine: {avg_sunshine}, total_sunshine: {total_sunshine}, distance: {city_data['distance']}")
            else:
                app.logger.debug(
                    f"No data in range for {city['City']}. Date range: {date_range}, Forecast dates: {forecast['date'].tolist()}")
        else:
            app.logger.debug(f"No forecast data for {city['City']}")

    # Sort cities by total sunshine and get top 5
    top_5_cities = sorted(city_sunshine, key=lambda x: x['total_sunshine'], reverse=True)[:5]

    # Prepare data for the template
    result_data = []
    for rank, city_data in enumerate(top_5_cities, 1):
        flight_search = FlightSearch()
        destination_code = flight_search.get_destination_code(city_data['city'].split(',')[0])

        if current_location_code and destination_code != "N/A" and destination_code != "Not Found":
            kayak_link = f"https://www.kayak.com/flights/{current_location_code}-{destination_code}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        else:
            kayak_link = None

        result = {
            'rank': rank,
            'city': f"{city_data['city']}, {city_data['country']}",
            'avg_sunshine': f"{city_data['avg_sunshine']:.2f}",
            'total_sunshine': f"{city_data['total_sunshine']:.2f}",
            'distance': f"{city_data['distance']}",
            'kayak_link': kayak_link
        }
        result_data.append(result)

    show_distance = current_lat is not None and current_lon is not None

    return render_template("results.html", results=result_data, start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'), current_location=current_location,
                           show_distance=show_distance)


def filter_cities_by_preferences(cities, preferences, current_lat, current_lon, distance_preference):
    filtered_cities = cities.copy()
    
    preference_mapping = {
        'island': 'Island',
        'capital': 'Capital',
        'eu': 'EU',
        'schengen': 'Schengen'
    }
    
    for pref, value in preferences.items():
        if pref in preference_mapping:
            key = preference_mapping[pref]
            if value == 'must':
                filtered_cities = [city for city in filtered_cities if city.get(key) == 'yes']
            elif value == 'dont':
                filtered_cities = [city for city in filtered_cities if city.get(key) != 'yes']
    
    if current_lat is not None and current_lon is not None and distance_preference:
        min_dist, max_dist = map(int, distance_preference.split('-')) if '-' in distance_preference else (2001, float('inf'))
        filtered_cities = [
            city for city in filtered_cities
            if min_dist <= haversine_distance(current_lat, current_lon, city['Latitude'], city['Longitude']) < max_dist
        ]
    
    return filtered_cities


def find_closest_airport(lat, lon, airports_df):
    airports_df['distance'] = airports_df.apply(lambda row: haversine_distance(lat, lon, row['Latitude'], row['Longitude']), axis=1)
    closest_airport = airports_df.loc[airports_df['distance'].idxmin()]
    return closest_airport['City'], closest_airport['IATA_Code']


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)