"""
Weather Service
Open-Meteo API integration with data transformation
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


from utils.transformations import (
    transform_current_weather,
    transform_forecast,
    transform_hourly_forecast,
    get_weather_condition
)


from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential

class WeatherService:
    """Service for fetching and transforming weather data from Open-Meteo API"""
    
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1"
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1"
        self.air_quality_url = "https://air-quality-api.open-meteo.com/v1"
        self.client = httpx.AsyncClient(timeout=10.0)

    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_current_weather(
        self,
        lat: float,
        lon: float,
        units: str = "metric"
    ) -> Dict[str, Any]:
        """
        Get current weather for coordinates.
        """
        try:
            # 1. Fetch Weather Data (Forecast API)
            weather_params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,is_day,visibility",
                "daily": "sunrise,sunset,uv_index_max",
                "timezone": "auto",
                "temperature_unit": "fahrenheit" if units == "imperial" else "celsius",
                "wind_speed_unit": "mph" if units == "imperial" else "kmh"
            }
            
            # 2. Fetch Air Quality Data
            aqi_params = {
                "latitude": lat,
                "longitude": lon,
                "current": "us_aqi,european_aqi"
            }

            # Execute requests in parallel
            weather_response, aqi_response = await asyncio.gather(
                self.client.get(f"{self.base_url}/forecast", params=weather_params),
                self.client.get(f"{self.air_quality_url}/air-quality", params=aqi_params)
            )

            weather_response.raise_for_status()
            # AQI might fail but we shouldn't fail the whole request? 
            # For now, let's treat it as critical or handle error gracefully. 
            # I'll let it raise for now to debug if it fails.
            aqi_response.raise_for_status() 
            
            weather_data = weather_response.json()
            aqi_data = aqi_response.json()
            
            # Transform using imported function
            return transform_current_weather(
                weather_data,
                "Unknown",  # City name will be added by caller
                {"lat": lat, "lon": lon},
                aqi_data=aqi_data
            )
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching weather: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_current_weather: {e}")
            raise
    
    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_forecast(
        self,
        lat: float,
        lon: float,
        days: int = 7,
        units: str = "metric"
    ) -> List[Dict[str, Any]]:
        """
        Get daily forecast for coordinates.
        """
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
                "timezone": "auto",
                "forecast_days": days,
                "temperature_unit": "fahrenheit" if units == "imperial" else "celsius",
                "wind_speed_unit": "mph" if units == "imperial" else "kmh"
            }
            
            response = await self.client.get(f"{self.base_url}/forecast", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Transform using imported function
            forecast_data = transform_forecast(data, days=days)
            
            return forecast_data
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching forecast: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_forecast: {e}")
            raise
    
    async def get_hourly_forecast(
        self,
        lat: float,
        lon: float,
        hours: int = 24,
        units: str = "metric"
    ) -> List[Dict[str, Any]]:
        """
        Get hourly forecast for coordinates.
        """
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,weather_code,precipitation,precipitation_probability,wind_speed_10m,relative_humidity_2m",
                "timezone": "auto",
                "forecast_days": (hours // 24) + 1,
                "temperature_unit": "fahrenheit" if units == "imperial" else "celsius",
                "wind_speed_unit": "mph" if units == "imperial" else "kmh"
            }
            
            response = await self.client.get(f"{self.base_url}/forecast", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Transform using imported function
            hourly_data = transform_hourly_forecast(data, hours=hours)
            
            return hourly_data
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching hourly forecast: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_hourly_forecast: {e}")
            raise

    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_historical_weather(
        self,
        lat: float,
        lon: float,
        days: int = 30,
        units: str = "metric"
    ) -> List[Dict[str, Any]]:
        """Get historical weather data"""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_direction_10m_dominant",
                "timezone": "auto",
                "temperature_unit": "fahrenheit" if units == "imperial" else "celsius",
                "wind_speed_unit": "mph" if units == "imperial" else "kmh"
            }
            
            # Use archive API
            url = "https://archive-api.open-meteo.com/v1/archive"
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._transform_historical(data)
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return []

    def _transform_historical(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        daily = data.get('daily', {})
        if not daily:
            return []
            
        history = []
        time_list = daily.get('time', [])
        
        for i in range(len(time_list)):
            history.append({
                "date": time_list[i],
                "temperature": daily.get('temperature_2m_max', [])[i],
                "minTemp": daily.get('temperature_2m_min', [])[i],
                "precipitation": daily.get('precipitation_sum', [])[i],
                "windSpeed": daily.get('wind_speed_10m_max', [])[i],
                "windDirection": daily.get('wind_direction_10m_dominant', [])[i]
            })
        return history
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
