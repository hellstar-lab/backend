"""
Data Models
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class UnitSystem(str, Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"

class AlertType(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
    PRECIPITATION = "precipitation"

class ComparisonOperator(str, Enum):
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"

class NotificationMethod(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"

class MessageType(str, Enum):
    USER = "user"
    BOT = "bot"


# ============================================================================
# Weather Models
# ============================================================================

class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

class WeatherCondition(BaseModel):
    text: str
    code: int
    icon: str

class CurrentWeather(BaseModel):
    temperature: float
    feelsLike: float
    humidity: int
    windSpeed: float
    windDirection: int
    pressure: float
    uvIndex: float
    visibility: float
    condition: str
    weatherCode: int
    isDay: bool
    timestamp: datetime

class DailyForecast(BaseModel):
    date: str
    maxTemp: float
    minTemp: float
    precipitationChance: int
    condition: str
    weatherCode: int
    sunrise: str
    sunset: str
    uvIndex: float

class HourlyForecast(BaseModel):
    time: str
    temperature: float
    condition: str
    precipitationChance: int

class WeatherResponse(BaseModel):
    location: str
    current: CurrentWeather
    daily: List[DailyForecast]
    hourly: List[HourlyForecast]
    units: UnitSystem


# ============================================================================
# User Models
# ============================================================================

class UserSettings(BaseModel):
    defaultLocation: str = "New York"
    temperatureUnits: UnitSystem = UnitSystem.METRIC
    emailNotifications: bool = True
    pushNotifications: bool = False
    smsNotifications: bool = False
    weeklyReports: bool = True
    theme: str = "dark"
    timeFormat24h: bool = False
    autoRefresh: bool = True

class UserSubscription(BaseModel):
    plan: str
    status: str
    startDate: datetime
    endDate: Optional[datetime] = None

class UserProfile(BaseModel):
    userId: str
    email: EmailStr
    name: Optional[str] = None
    photoURL: Optional[str] = None
    emailVerified: bool
    createdAt: datetime
    lastLoginAt: datetime
    settings: UserSettings
    subscription: UserSubscription


# ============================================================================
# Alert Models
# ============================================================================

class AlertBase(BaseModel):
    name: str
    type: AlertType
    thresholdValue: float
    comparison: ComparisonOperator
    location: str
    notificationMethods: List[NotificationMethod]
    severity: str = "warning"

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    name: Optional[str] = None
    thresholdValue: Optional[float] = None
    notificationMethods: Optional[List[NotificationMethod]] = None
    active: Optional[bool] = None

class AlertResponse(AlertBase):
    id: str
    userId: str
    active: bool
    createdAt: datetime
    lastTriggered: Optional[datetime] = None
    triggerCount: int


# ============================================================================
# Chatbot Models
# ============================================================================

class ChatMessage(BaseModel):
    id: str
    sessionId: str
    messageType: MessageType
    content: str
    weatherData: Optional[Dict[str, Any]] = None
    createdAt: datetime

class ChatSession(BaseModel):
    sessionId: str
    lastMessage: str
    lastMessageAt: datetime


# ============================================================================
# History Models
# ============================================================================

class QueryHistoryItem(BaseModel):
    id: str
    city: str
    country: str
    queriedAt: datetime
    condition: str
    temperature: float
    humidity: int
    windSpeed: float
