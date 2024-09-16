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
from datetime import datetime

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
    df = pd.read_csv('cities_airports.csv',
                     usecols=['City', 'Latitude', 'Longitude', 'IATA_Code', 'Country', 'Island', 'Capital', 'EU',
                              'Schengen', 'Population', 'Cost_Scale', 'Euro'])
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
    population_ranges = json.loads(request.args.get('population_ranges', '[]'))
    cost_ranges = json.loads(request.args.get('cost_ranges', '[]'))

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

    current_city = europe_cities_df[europe_cities_df['city'].str.lower() == current_location.lower()].iloc[0] if not \
        europe_cities_df[europe_cities_df['city'].str.lower() == current_location.lower()].empty else None

    if current_city is not None:
        current_lat, current_lon = current_city['lat'], current_city['lng']

        # Check if the current location is in the airports database
        current_airport = airports_df[airports_df['City'].str.lower() == current_location.lower()]

        if current_airport.empty:
            # Find the closest airport
            closest_city, closest_airport_code = find_closest_airport(current_lat, current_lon, airports_df)
            current_location_code = closest_airport_code
            print(
                f"No airport found for {current_location}. Using closest airport: {closest_city} ({closest_airport_code})")
        else:
            current_location_code = current_airport.iloc[0]['IATA_Code']
    else:
        current_lat, current_lon = None, None
        current_location_code = None

    # Parse preferences
    preferences = json.loads(request.args.get('preferences', '{}'))

    # Filter cities based on preferences
    filtered_cities = filter_cities_by_preferences(cities, preferences, current_lat, current_lon, distance_preference, population_ranges, cost_ranges)

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
                    'total_sunshine': total_sunshine,
                    'latitude': city['Latitude'],
                    'longitude': city['Longitude']
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

    # Load city descriptions and additional information from CSV file
    city_info = {}
    try:
        info_df = pd.read_csv('cities_airports.csv')
        city_info = info_df.set_index('City')[['City_Description', 'City_To_Dos', 'Food_to_try']].to_dict('index')
    except FileNotFoundError:
        app.logger.warning("Cities information file not found. Additional info will not be included.")
    except pd.errors.EmptyDataError:
        app.logger.warning("Cities information file is empty. Additional info will not be included.")
    except KeyError as e:
        app.logger.warning(f"Column {e} not found in the CSV. Some additional info may not be included.")

    # Load flag emojis
    flag_emojis = {}
    try:
        flag_df = pd.read_csv('flag_emoji.csv')
        flag_emojis = dict(zip(flag_df['Country'], flag_df['Flag']))
    except FileNotFoundError:
        app.logger.warning("Flag emoji file not found. Flags will not be displayed.")
    except pd.errors.EmptyDataError:
        app.logger.warning("Flag emoji file is empty. Flags will not be displayed.")

    # Prepare data for the template
    result_data = []
    for city in top_5_cities:
        city_name = city['city']
        country = city['country']
        flag_emoji = flag_emojis.get(country, '')
        
        # Find the IATA code for the city
        city_airport = airports_df[airports_df['City'].str.lower() == city_name.lower()]
        iata_code = city_airport['IATA_Code'].iloc[0] if not city_airport.empty else ''

        result_data.append({
            'city': city_name,
            'country': country,
            'flag_emoji': flag_emoji,
            'avg_sunshine': round(city['avg_sunshine'], 2),
            'total_sunshine': round(city['total_sunshine'], 2),
            'distance': round(city['distance']) if isinstance(city['distance'], (int, float)) else city['distance'],
            'latitude': city['latitude'],
            'longitude': city['longitude'],
            'description': city_info.get(city_name, {}).get('City_Description', ''),
            'to_dos': city_info.get(city_name, {}).get('City_To_Dos', ''),
            'food_to_try': city_info.get(city_name, {}).get('Food_to_try', ''),
            'iata_code': iata_code,
            'kayak_link': f"https://www.kayak.com/flights/{current_location_code}-{iata_code}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}" if iata_code else '#',
            'booking_link': f"https://www.booking.com/searchresults.html?ss={city_name}&checkin={start_date}&checkout={end_date}"
        })

    show_distance = current_lat is not None and current_lon is not None

    current_lat = current_city['lat'] if current_city is not None else None
    current_lon = current_city['lng'] if current_city is not None else None

    return render_template("results.html", results=result_data, start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'), current_location=current_location,
                           show_distance=show_distance, current_lat=current_lat, current_lon=current_lon)


def filter_cities_by_preferences(cities, preferences, current_lat, current_lon, distance_preference, population_ranges, cost_ranges):
    filtered_cities = cities.copy()

    preference_mapping = {
        'island': 'Island',
        'capital': 'Capital',
        'eu': 'EU',
        'schengen': 'Schengen',
        'eurozone': 'Euro'
    }

    for pref, value in preferences.items():
        if pref in preference_mapping:
            key = preference_mapping[pref]
            if value == 'must':
                filtered_cities = [city for city in filtered_cities if city.get(key) == 'yes']
            elif value == 'dont':
                filtered_cities = [city for city in filtered_cities if city.get(key) != 'yes']

    if current_lat is not None and current_lon is not None and distance_preference:
        max_dist = int(distance_preference)
        if max_dist < 5000:  # Only filter if it's not "Any distance"
            filtered_cities = [
                city for city in filtered_cities
                if haversine_distance(current_lat, current_lon, city['Latitude'], city['Longitude']) <= max_dist
            ]

    # Filter by population ranges
    if population_ranges and len(population_ranges) < 4:  # If not all ranges are selected
        filtered_cities = [
            city for city in filtered_cities
            if any(is_in_population_range(city['Population'], range_name) for range_name in population_ranges)
        ]

    # Filter by cost ranges
    if cost_ranges and len(cost_ranges) < 4:  # If not all ranges are selected
        filtered_cities = [
            city for city in filtered_cities
            if city['Cost_Scale'] in cost_ranges
        ]

    return filtered_cities

def is_in_population_range(population, range_name):
    population = int(population.replace(',', ''))
    ranges = {
        'small': (0, 200000),
        'medium': (200001, 500000),
        'metropolitan': (500001, 1500000),
        'large-metropolitan': (1500001, float('inf'))
    }
    min_pop, max_pop = ranges[range_name]
    return min_pop <= population <= max_pop

def find_closest_airport(lat, lon, airports_df):
    airports_df['distance'] = airports_df.apply(
        lambda row: haversine_distance(lat, lon, row['Latitude'], row['Longitude']), axis=1)
    closest_airport = airports_df.loc[airports_df['distance'].idxmin()]
    return closest_airport['City'], closest_airport['IATA_Code']


@app.template_filter('format_date')
def format_date(date_string):
    date = datetime.strptime(date_string, '%Y-%m-%d')
    return date.strftime('%A, %B %d')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)