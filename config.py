"""
Configuration Management
Environment variables and application settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union, Any, Optional
from pydantic import field_validator
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key"
    API_VERSION: str = "v1"
    API_PREFIX: str = "/api"
    PORT: int = 8000
    
    # CORS
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8501"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Firebase
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_PRIVATE_KEY_ID: str = os.getenv("FIREBASE_PRIVATE_KEY_ID", "")
    FIREBASE_PRIVATE_KEY: str = os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")
    FIREBASE_CLIENT_EMAIL: str = os.getenv("FIREBASE_CLIENT_EMAIL", "")
    FIREBASE_CLIENT_ID: str = os.getenv("FIREBASE_CLIENT_ID", "")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # SendGrid
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "noreply@vornics.com")
    
    # Twilio (optional)
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = 300
    STALE_CACHE_MAX_AGE_SECONDS: int = 3600
    
    # SMTP Configuration for OTP Emails
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Vornics Weather AI"
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100"))
    RATE_LIMIT_REQUESTS_PER_HOUR: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_HOUR", "5000"))
    RATE_LIMIT_REQUESTS_PER_DAY: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_DAY", "10000"))
    
    # Open-Meteo API
    OPENMETEO_BASE_URL: str = os.getenv("OPENMETEO_BASE_URL", "https://api.open-meteo.com/v1")
    OPENMETEO_GEOCODING_URL: str = os.getenv("OPENMETEO_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1")


# Create settings instance
settings = Settings()
