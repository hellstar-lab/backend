"""
Input Validators
Validation functions for API inputs
"""

import re
from fastapi import HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def validate_city_name(city: str) -> str:
    """
    Validate and sanitize city name.
    
    Args:
        city: City name to validate
    
    Returns:
        Sanitized city name
    
    Raises:
        HTTPException: 400 if invalid
    """
    if not city or len(city.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="City name must be at least 2 characters"
        )
    
    if len(city) > 100:
        raise HTTPException(
            status_code=400,
            detail="City name too long (max 100 characters)"
        )
    
    # Allow letters, spaces, hyphens, apostrophes, and periods
    if not re.match(r"^[a-zA-Z\s\-'.]+$", city):
        raise HTTPException(
            status_code=400,
            detail="City name contains invalid characters"
        )
    
    return city.strip()


def validate_coordinates(lat: float, lon: float) -> tuple[float, float]:
    """
    Validate latitude and longitude.
    
    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
    
    Returns:
        Validated (lat, lon) tuple
    
    Raises:
        HTTPException: 400 if invalid
    """
    if not (-90 <= lat <= 90):
        raise HTTPException(
            status_code=400,
            detail="Latitude must be between -90 and 90"
        )
    
    if not (-180 <= lon <= 180):
        raise HTTPException(
            status_code=400,
            detail="Longitude must be between -180 and 180"
        )
    
    return (lat, lon)


def validate_units(units: str) -> str:
    """
    Validate temperature units.
    
    Args:
        units: "metric" or "imperial"
    
    Returns:
        Validated units string
    
    Raises:
        HTTPException: 400 if invalid
    """
    if units not in ["metric", "imperial"]:
        raise HTTPException(
            status_code=400,
            detail="Units must be 'metric' or 'imperial'"
        )
    
    return units


def validate_days(days: int, min_days: int = 1, max_days: int = 16) -> int:
    """
    Validate forecast days.
    
    Args:
        days: Number of days
        min_days: Minimum allowed (default 1)
        max_days: Maximum allowed (default 16)
    
    Returns:
        Validated days
    
    Raises:
        HTTPException: 400 if invalid
    """
    if not (min_days <= days <= max_days):
        raise HTTPException(
            status_code=400,
            detail=f"Days must be between {min_days} and {max_days}"
        )
    
    return days


def validate_alert_type(alert_type: str) -> str:
    """
    Validate alert type.
    
    Args:
        alert_type: Alert type string
    
    Returns:
        Validated alert type
    
    Raises:
        HTTPException: 400 if invalid
    """
    valid_types = ["temperature", "humidity", "wind_speed", "precipitation"]
    
    if alert_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Alert type must be one of: {', '.join(valid_types)}"
        )
    
    return alert_type


def validate_comparison(comparison: str) -> str:
    """
    Validate comparison operator.
    
    Args:
        comparison: Comparison operator
    
    Returns:
        Validated comparison
    
    Raises:
        HTTPException: 400 if invalid
    """
    valid_comparisons = ["greater_than", "less_than", "equals"]
    
    if comparison not in valid_comparisons:
        raise HTTPException(
            status_code=400,
            detail=f"Comparison must be one of: {', '.join(valid_comparisons)}"
        )
    
    return comparison


def validate_notification_methods(methods: list[str]) -> list[str]:
    """
    Validate notification methods.
    
    Args:
        methods: List of notification methods
    
    Returns:
        Validated methods list
    
    Raises:
        HTTPException: 400 if invalid
    """
    valid_methods = ["email", "sms", "push"]
    
    if not methods:
        raise HTTPException(
            status_code=400,
            detail="At least one notification method required"
        )
    
    for method in methods:
        if method not in valid_methods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid notification method: {method}"
            )
    
    return methods


def validate_email(email: str) -> str:
    """
    Validate email address.
    
    Args:
        email: Email address
    
    Returns:
        Validated email
    
    Raises:
        HTTPException: 400 if invalid
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email address"
        )
    
    return email.lower()


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input string.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    
    Raises:
        HTTPException: 400 if too long
    """
    if len(text) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Text too long (max {max_length} characters)"
        )
    
    # Remove any potential script tags or HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()
