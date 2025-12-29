"""
Geocoding Utilities
City name to coordinates conversion with caching
"""

import httpx
from typing import Dict, Any
from datetime import datetime, timedelta
import hashlib
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def geocode_city(city_name: str, db=None) -> Dict[str, Any]:
    """
    Geocode city name to coordinates using Open-Meteo API.
    Results are cached in Firestore for 24 hours.
    
    Args:
        city_name: Name of the city
        db: Firestore client (optional, for caching)
    
    Returns:
        {
            "lat": float,
            "lon": float,
            "city": str,
            "country": str,
            "countryCode": str,
            "timezone": str
        }
    
    Raises:
        HTTPException: 404 if city not found
    """
    # Check cache first if db provided
    if db:
        cache_key = hashlib.md5(city_name.lower().encode()).hexdigest()
        cache_ref = db.collection('geocode_cache').document(cache_key)
        
        try:
            cached_doc = cache_ref.get()
            if cached_doc.exists:
                cached_data = cached_doc.to_dict()
                cached_at = cached_data.get('cachedAt')
                
                if cached_at:
                    age = datetime.utcnow() - cached_at
                    if age < timedelta(hours=24):
                        logger.info(f"Geocode cache HIT: {city_name}")
                        return cached_data.get('data')
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
    
    # Cache miss - call API
    logger.info(f"Geocode cache MISS: {city_name}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "name": city_name,
                    "count": 1,
                    "language": "en",
                    "format": "json"
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        if not data.get('results'):
            raise HTTPException(
                status_code=404,
                detail=f"City '{city_name}' not found"
            )
        
        result = data['results'][0]
        
        geocode_data = {
            "lat": result['latitude'],
            "lon": result['longitude'],
            "city": result['name'],
            "country": result.get('country', ''),
            "countryCode": result.get('country_code', '').upper(),
            "timezone": result.get('timezone', 'UTC')
        }
        
        # Cache result if db provided
        if db:
            try:
                cache_ref.set({
                    'data': geocode_data,
                    'cachedAt': datetime.utcnow(),
                    'expiresAt': datetime.utcnow() + timedelta(hours=24),
                    'cityName': city_name
                })
                logger.info(f"Geocoded and cached: {city_name}")
            except Exception as e:
                logger.warning(f"Failed to cache geocode result: {e}")
        
        return geocode_data
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error geocoding {city_name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Geocoding service temporarily unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error geocoding {city_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Geocoding failed"
        )


async def reverse_geocode(lat: float, lon: float) -> Dict[str, Any]:
    """
    Reverse geocode coordinates to city name.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        City information
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "count": 1
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        if not data.get('results'):
            return {
                "city": "Unknown",
                "country": "Unknown",
                "countryCode": "XX"
            }
        
        result = data['results'][0]
        
        return {
            "city": result['name'],
            "country": result.get('country', ''),
            "countryCode": result.get('country_code', '').upper()
        }
    
    except Exception as e:
        logger.error(f"Error reverse geocoding: {e}")
        return {
            "city": "Unknown",
            "country": "Unknown",
            "countryCode": "XX"
        }
