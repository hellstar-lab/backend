
"""
Weather API Routes
Endpoints for current weather, forecasts, and favorites
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from services.weather_service import WeatherService
from services.cache_service import CacheService
from services.auth_service import get_current_user, get_optional_user
from utils.geocoding import geocode_city
from utils.validators import validate_city_name
from firestore_client import db
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

weather_service = WeatherService()
cache_service = CacheService()


@router.get("/current/{city}")
async def get_current_weather(
    city: str,
    units: str = Query("metric", regex="^(metric|imperial)$"),
    force: bool = False,
    user: Optional[dict] = Depends(get_optional_user)
):
    """Get current weather for a city"""
    try:
        city = validate_city_name(city)
        uid = user['uid'] if user else 'anonymous'
        logger.info(f"Weather request: {city} by user {uid} (force={force})")
        
        # Geocode city
        geocode_data = await geocode_city(city)
        lat, lon = geocode_data['lat'], geocode_data['lon']
        
        # Check cache
        cache_key = f"weather_{lat}_{lon}_{units}"
        cached_data = None
        
        if not force:
            cached_data = await cache_service.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache HIT: {city}")
            # Ensure location is correct even if cache has "Unknown"
            cached_data['location'] = geocode_data['city']
            return JSONResponse(content={
                "source": "cache",
                "data": cached_data,
                "timestamp": datetime.utcnow().timestamp()
            })
        else:
            logger.info(f"Cache MISS: {city}")
            # Fetch from API
            weather_data = await weather_service.get_current_weather(lat, lon, units)
            
            # Inject correct city name
            weather_data['location'] = geocode_data['city']
            
            # Cache result
            await cache_service.set(cache_key, weather_data, ttl_seconds=300)
            
            # Record query history only if authenticated
            if user:
                try:
                    query_ref = db.collection('query_history').document()
                    query_ref.set({
                        'id': query_ref.id,
                        'userId': user['uid'],
                        'city': geocode_data['city'],
                        'country': geocode_data['country'],
                        'countryCode': geocode_data.get('countryCode', ''),
                        'latitude': lat,
                        'longitude': lon,
                        'weatherData': weather_data,
                        'queryType': 'current',
                        'queriedAt': datetime.utcnow(),
                        'expiresAt': datetime.utcnow() + timedelta(days=7)
                    })
                except Exception as e:
                    logger.error(f"Failed to save query history: {e}")
            
            return JSONResponse(content={
                "source": "api",
                "data": weather_data,
                "timestamp": datetime.utcnow().timestamp()
            })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast/{city}")
async def get_forecast(
    city: str,
    days: int = Query(7, ge=1, le=16),
    units: str = Query("metric", regex="^(metric|imperial)$"),
    user: Optional[dict] = Depends(get_optional_user)
):
    """Get weather forecast"""
    try:
        city = validate_city_name(city)
        geocode_data = await geocode_city(city)
        
        forecast_data = await weather_service.get_forecast(
            geocode_data['lat'],
            geocode_data['lon'],
            days=days,
            units=units
        )
        
        return JSONResponse(
            content={"city": geocode_data['city'], "forecast": forecast_data},
            headers={"Cache-Control": "public, max-age=600"}
        )
    
    except Exception as e:
        logger.error(f"Error in get_forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{city}")
async def get_historical_weather(
    city: str,
    days: int = Query(30, ge=1, le=90),
    units: str = Query("metric", regex="^(metric|imperial)$"),
    user: Optional[dict] = Depends(get_optional_user)
):
    """Get historical weather data"""
    try:
        city = validate_city_name(city)
        geocode_data = await geocode_city(city)
        
        history_data = await weather_service.get_historical_weather(
            geocode_data['lat'],
            geocode_data['lon'],
            days=days,
            units=units
        )
        
        return {
            "city": geocode_data['city'],
            "history": history_data
        }
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites")
async def get_favorite_cities(user: dict = Depends(get_current_user)):
    """Get user's favorite cities"""
    try:
        favorites_ref = db.collection('users').document(user['uid']).collection('favorite_cities')
        docs = favorites_ref.order_by('addedAt', direction='DESCENDING').stream()
        
        favorites = []
        for doc in docs:
            data = doc.to_dict()
            favorites.append({
                'id': doc.id,
                'city': data.get('city'),
                'country': data.get('country'),
                'addedAt': data.get('addedAt').isoformat() if data.get('addedAt') else None
            })
        
        return favorites
    
    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favorites")
async def add_favorite_city(
    city: str,
    user: dict = Depends(get_current_user)
):
    """Add city to favorites"""
    try:
        # Check max favorites (10)
        favorites_ref = db.collection('users').document(user['uid']).collection('favorite_cities')
        existing = list(favorites_ref.stream())
        
        if len(existing) >= 10:
            raise HTTPException(status_code=403, detail="Maximum 10 favorite cities allowed")
        
        # Geocode city
        geocode_data = await geocode_city(city)
        
        # Add to favorites
        fav_ref = favorites_ref.document()
        fav_ref.set({
            'id': fav_ref.id,
            'city': geocode_data['city'],
            'country': geocode_data['country'],
            'latitude': geocode_data['lat'],
            'longitude': geocode_data['lon'],
            'addedAt': datetime.utcnow()
        })
        
        return JSONResponse(content={"message": "City added to favorites"}, status_code=201)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/favorites/{favorite_id}")
async def remove_favorite_city(
    favorite_id: str,
    user: dict = Depends(get_current_user)
):
    """Remove city from favorites"""
    try:
        fav_ref = db.collection('users').document(user['uid']).collection('favorite_cities').document(favorite_id)
        fav_ref.delete()
        
        return {"message": "City removed from favorites"}
    
    except Exception as e:
        logger.error(f"Error removing favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/poll/{city}")
async def poll_weather(
    city: str,
    last_updated: Optional[str] = Header(None, alias="If-Modified-Since"),
    user: dict = Depends(get_current_user)
):
    """
    Smart polling endpoint for weather updates.
    Returns 304 if data hasn't changed since 'If-Modified-Since'.
    """
    try:
        city = validate_city_name(city)
        
        # Geocode to get cache key
        geocode_data = await geocode_city(city)
        lat, lon = geocode_data['lat'], geocode_data['lon']
        
        # Check cache
        cache_key = f"weather_{lat}_{lon}_metric" # Default to metric for polling check
        cached_data = await cache_service.get(cache_key)
        
        # If we have cached data
        if cached_data:
            # Check timestamp
            cached_at = cached_data.get('timestamp') # ISO string
            
            if last_updated and cached_at:
                # Compare timestamps
                try:
                    client_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    server_time = datetime.fromisoformat(cached_at.replace('Z', '+00:00'))
                    
                    # If server data is not newer than client data
                    if server_time <= client_time:
                        return JSONResponse(status_code=304, content=None)
                except ValueError:
                    # If parsing fails, ignore and return data
                    pass
            
            return cached_data
            
        else:
            # No cache, fetch new data
            weather_data = await weather_service.get_current_weather(lat, lon, "metric")
            await cache_service.set(cache_key, weather_data, ttl_seconds=300)
            return weather_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error polling weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))
