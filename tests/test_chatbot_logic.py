"""
Chatbot Logic Tests
Unit tests for NLP utilities and intent recognition
"""

import pytest
from utils.nlp_utils import extract_city_from_message, is_weather_query

def test_weather_intent_recognition():
    """Test detection of weather-related queries"""
    assert is_weather_query("What is the weather today?") == True
    assert is_weather_query("Temperature in London") == True
    assert is_weather_query("Is it going to rain?") == True
    assert is_weather_query("Forecast for next week") == True
    assert is_weather_query("Hello there") == False
    assert is_weather_query("What is your name?") == False

def test_city_extraction():
    """Test city extraction from various message formats"""
    # Standard patterns
    assert extract_city_from_message("Weather in London") == "London"
    assert extract_city_from_message("Temperature at Paris") == "Paris"
    assert extract_city_from_message("Forecast for Tokyo") == "Tokyo"
    
    # Multi-word cities
    assert extract_city_from_message("Weather in New York") == "New York"
    assert extract_city_from_message("San Francisco weather") == "San Francisco"
    
    # Capitalized words fallback
    assert extract_city_from_message("Chicago") == "Chicago"
    assert extract_city_from_message("Los Angeles") == "Los Angeles"
    
    # Negative cases
    assert extract_city_from_message("Hello world") == None
    assert extract_city_from_message("weather today") == None

def test_city_extraction_cleanup():
    """Test cleanup of extracted city names"""
    assert extract_city_from_message("Weather in London weather") == "London"
    assert extract_city_from_message("Forecast for Paris tomorrow") == "Paris"
    assert extract_city_from_message("Temperature in Rome today") == "Rome"
