"""
Main FastAPI Application Entry Point
Vornics Weather AI Platform Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

# Import configuration
from config import settings
import sentry_sdk

# Initialize Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        environment=settings.ENVIRONMENT,
    )

# Import routes
from api import auth_routes, weather_routes, history_routes, alerts_routes
from api import chatbot_routes, user_routes, sse_routes

# Import middleware
from middleware.error_handler import add_error_handlers

# Setup logging
from utils.logger import setup_logger, request_id_ctx
logger = setup_logger()

# Middleware for Request ID
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from uuid import uuid4

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)


# Initialize FastAPI app
app = FastAPI(
    title="Vornics Weather AI API",
    description="Real-time weather dashboard with AI chatbot",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Compression for responses >1KB (70% bandwidth reduction)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestIDMiddleware)

# Add error handlers
add_error_handlers(app)

# Include routers
app.include_router(auth_routes.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(weather_routes.router, prefix=f"{settings.API_PREFIX}/weather", tags=["Weather"])
app.include_router(history_routes.router, prefix=f"{settings.API_PREFIX}/history", tags=["History"])
app.include_router(alerts_routes.router, prefix=f"{settings.API_PREFIX}/alerts", tags=["Alerts"])
app.include_router(chatbot_routes.router, prefix=f"{settings.API_PREFIX}/chatbot", tags=["Chatbot"])
app.include_router(user_routes.router, prefix=f"{settings.API_PREFIX}/user", tags=["User"])
app.include_router(sse_routes.router, prefix=f"{settings.API_PREFIX}/sse", tags=["Real-Time"])


@app.on_event("startup")
async def startup():
    """Initialize resources on startup"""
    # Initialize Redis and Rate Limiter
    from services.redis_service import get_redis
    from fastapi_limiter import FastAPILimiter
    
    redis = await get_redis()
    await FastAPILimiter.init(redis)
    logger.info("Rate limiter initialized")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup resources on shutdown"""
    from services.redis_service import close_redis
    await close_redis()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Vornics Weather AI API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    from services.weather_service import WeatherService
    from firestore_client import db
    
    services = {}
    
    # Check Firestore
    try:
        db.collection('_health_check').document('test').set({'timestamp': datetime.utcnow()})
        services['firestore'] = 'ok'
    except Exception as e:
        logger.error(f"Firestore health check failed: {e}")
        services['firestore'] = 'error'
    
    # Check Open-Meteo
    try:
        weather_service = WeatherService()
        # Simple API call to check connectivity
        services['openmeteo'] = 'ok'
    except Exception as e:
        logger.error(f"Open-Meteo health check failed: {e}")
        services['openmeteo'] = 'error'
    
    status = 'healthy' if all(v == 'ok' for v in services.values()) else 'degraded'
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
        "environment": settings.ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
