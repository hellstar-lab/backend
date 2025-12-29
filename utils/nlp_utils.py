"""
NLP Utilities
Intent recognition and entity extraction for chatbot
"""

import re
from typing import Optional

WEATHER_KEYWORDS = [
    "weather", "temperature", "forecast", "rain", "sunny", 
    "cloudy", "snow", "wind", "hot", "cold", "humidity"
]

CITY_PATTERNS = [
    r"in\s+([A-Z][a-zA-Z\s]+)",           # "weather in London"
    r"at\s+([A-Z][a-zA-Z\s]+)",           # "temperature at Paris"
    r"for\s+([A-Z][a-zA-Z\s]+)",          # "forecast for Tokyo"
    r"^([A-Z][a-zA-Z\s]+)\s+weather",     # "London weather"
    r"weather\s+in\s+([A-Z][a-zA-Z\s]+)", # "weather in New York"
]

def extract_city_from_message(message: str) -> Optional[str]:
    """
    Extract city name from message using regex patterns.
    
    Args:
        message: User input message
        
    Returns:
        Extracted city name or None
    """
    # Try regex patterns first
    for pattern in CITY_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            # Remove common trailing words that might get captured
            city = re.sub(r'\s+(weather|forecast|temperature|today|tomorrow)$', '', city, flags=re.IGNORECASE)
            return city.strip()
    
    # Fallback: look for capitalized words in short messages
    # This helps capture just "London" or "New York" if user types only that
    words = message.split()
    if len(words) < 5:
        for i, word in enumerate(words):
            # Check for capitalized words (excluding common keywords if they happened to be capitalized)
            if word[0].isupper() and len(word) > 2 and word.lower() not in WEATHER_KEYWORDS:
                # Check if next word is also capitalized (e.g., "New York")
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    return f"{word} {words[i + 1]}"
                return word
    
    return None

def is_weather_query(message: str) -> bool:
    """
    Check if message is related to weather.
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in WEATHER_KEYWORDS)
