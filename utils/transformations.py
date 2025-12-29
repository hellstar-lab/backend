"""
Data Transformation Utilities
Functions to transform API responses to frontend data models
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


def get_weather_condition(code: int) -> str:
    """
    Map WMO weather code to descriptive text.
    Based on Open-Meteo WMO codes.
    """
    # WMO Weather interpretation codes (WW)
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
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
    return codes.get(code, "Unknown")


def transform_current_weather(
    data: Dict[str, Any],
    city_name: str,
    coordinates: Dict[str, float],
    aqi_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Transform Open-Meteo current weather response.
    """
    current = data.get('current', {})
    daily = data.get('daily', {})
    
    # Get today's daily data (first element)
    today_daily = {k: v[0] if v else None for k, v in daily.items()}
    
    # Process AQI - Send raw US AQI value (frontend expects 0-500 scale)
    air_quality = 1  # Default fallback
    if aqi_data:
        current_aqi = aqi_data.get('current', {})
        us_aqi = current_aqi.get('us_aqi')
        if us_aqi is not None:
            air_quality = us_aqi  # Send raw value, frontend will map it

    # Process Visibility (meters to km) with fog correction
    visibility = current.get('visibility')
    weather_code = current.get('weather_code')
    
    if visibility is not None:
        visibility = visibility / 1000.0  # Convert to km
        
        # Apply fog correction - Open-Meteo's visibility doesn't account well for fog
        # WMO codes: 45 = Fog, 48 = Depositing rime fog
        if weather_code in [45, 48]:
            # During fog, visibility is typically much lower
            # Cap at 2km for fog conditions (more realistic)
            visibility = min(visibility, 2.0)
            # If humidity is very high (>95%), reduce further
            humidity = current.get('relative_humidity_2m', 0)
            if humidity > 95:
                visibility = min(visibility, 1.0)
    else:
        visibility = 10.0  # Fallback

    return {
        "location": city_name,
        "temperature": current.get('temperature_2m'),
        "feelsLike": current.get('apparent_temperature'),
        "condition": get_weather_condition(current.get('weather_code')),
        "humidity": current.get('relative_humidity_2m'),
        "windSpeed": current.get('wind_speed_10m'),
        "windDirection": current.get('wind_direction_10m'),
        "pressure": current.get('pressure_msl'),
        "uvIndex": 0 if not current.get('is_day', 1) else today_daily.get('uv_index_max'),
        "visibility": visibility,
        "airQuality": air_quality,
        "sunrise": today_daily.get('sunrise'),
        "sunset": today_daily.get('sunset'),
        "coordinates": coordinates,
        "weatherCode": current.get('weather_code'),
        "isDay": bool(current.get('is_day', 1)),
        "timestamp": datetime.utcnow().isoformat()
    }


def transform_forecast(
    data: Dict[str, Any],
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Transform Open-Meteo daily forecast response.
    """
    daily = data.get('daily', {})
    if not daily:
        return []
    
    forecast = []
    time_list = daily.get('time', [])
    
    for i in range(min(len(time_list), days)):
        forecast.append({
            "date": time_list[i],
            "maxTemp": daily.get('temperature_2m_max', [])[i],
            "minTemp": daily.get('temperature_2m_min', [])[i],
            "precipitationChance": daily.get('precipitation_probability_max', [])[i],
            "condition": get_weather_condition(daily.get('weather_code', [])[i]),
            "weatherCode": daily.get('weather_code', [])[i],
            "sunrise": daily.get('sunrise', [])[i],
            "sunset": daily.get('sunset', [])[i],
            "uvIndex": daily.get('uv_index_max', [])[i]
        })
        
    return forecast


def transform_hourly_forecast(
    data: Dict[str, Any],
    hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Transform Open-Meteo hourly forecast response.
    """
    hourly = data.get('hourly', {})
    if not hourly:
        return []
    
    forecast = []
    time_list = hourly.get('time', [])
    
    for i in range(min(len(time_list), hours)):
        forecast.append({
            "time": time_list[i],
            "temperature": hourly.get('temperature_2m', [])[i],
            "condition": get_weather_condition(hourly.get('weather_code', [])[i]),
            "precipitationChance": hourly.get('precipitation_probability', [])[i],
            "humidity": hourly.get('relative_humidity_2m', [])[i],
            "windSpeed": hourly.get('wind_speed_10m', [])[i]
        })
        
    return forecast
