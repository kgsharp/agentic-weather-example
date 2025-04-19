import json
import requests
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_coordinates(city):
    """Get latitude and longitude for a city using Open-Meteo's geocoding API"""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    response = requests.get(url)
    data = response.json()
    
    if not data.get('results'):
        raise Exception(f"Could not find coordinates for city: {city}")
    
    result = data['results'][0]
    return result['latitude'], result['longitude']

def get_weather(latitude, longitude):
    """Get weather data from Open-Meteo API"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
    response = requests.get(url)
    data = response.json()
    
    if 'error' in data:
        raise Exception(f"Weather API error: {data['error']}")
    
    # Convert temperature from Celsius to Fahrenheit
    data['current']['temperature_2m'] = data['current']['temperature_2m'] * 9/5 + 32
    
    return data['current']

def weather_code_to_description(code):
    """Convert Open-Meteo weather code to human-readable description"""
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(code, "Unknown weather condition")

def format_bedrock_response(response_state, response_body):
    response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "get-weather-from-lambda",
            "function": "get-weather-data",
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": response_body
                    }
                }
            }
        }
    }
    
    # Include responseState only for failures
    if response_state == "FAILURE":
        response["response"]["functionResponse"]["responseState"] = response_state
    
    return response

def lambda_handler(event, context):
    try:
        # Log the incoming event for debugging
        logger.info("Received event: %s", json.dumps(event))
        
        # Extract parameters from the event
        parameters = {param['name']: param['value'] for param in event.get('parameters', [])}
        location = parameters.get('location')
        intent = parameters.get('intent')
        
        if not location or intent != 'get_weather':
            response = format_bedrock_response(
                "FAILURE",
                "Invalid request parameters"
            )
            logger.info("Response: %s", json.dumps(response))
            return response
        
        # Get coordinates for the city
        latitude, longitude = get_coordinates(location)
        
        # Get weather data
        weather_data = get_weather(latitude, longitude)
        
        # Format the response as plain text
        response_text = (
            f"Weather for {location}:\n"
            f"Temperature: {weather_data['temperature_2m']}°F\n"
            f"Conditions: {weather_code_to_description(weather_data['weather_code'])}\n"
            f"Humidity: {weather_data['relative_humidity_2m']}%\n"
            f"Wind Speed: {weather_data['wind_speed_10m']} mph"
        )
        
        response = format_bedrock_response(
            None,  # No responseState for success
            response_text
        )
        logger.info("Response: %s", json.dumps(response))
        return response
        
    except Exception as e:
        response = format_bedrock_response(
            "FAILURE",
            str(e)
        )
        logger.info("Response: %s", json.dumps(response))
        return response 