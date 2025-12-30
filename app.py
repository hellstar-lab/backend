"""
Main FastAPI Application Entry Point
Vornics Weather AI Platform Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
# NOTE: Chatbot routes are commented out because ChatterBot is disabled in requirements.txt
from api import auth_routes, weather_routes, history_routes, alerts_routes
# from api import chatbot_routes  # <--- CAUSE OF CRASH: ChatterBot not installed
from api import user_routes, sse_routes

# Import middleware
from middleware.error_handler import add_error_handlers
from utils.logger import setup_logger, request_id_ctx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from uuid import uuid4

logger = setup_logger()

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

from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestIDMiddleware)

add_error_handlers(app)

# Include routers
app.include_router(auth_routes.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(weather_routes.router, prefix=f"{settings.API_PREFIX}/weather", tags=["Weather"])
app.include_router(history_routes.router, prefix=f"{settings.API_PREFIX}/history", tags=["History"])
app.include_router(alerts_routes.router, prefix=f"{settings.API_PREFIX}/alerts", tags=["Alerts"])
# app.include_router(chatbot_routes.router, prefix=f"{settings.API_PREFIX}/chatbot", tags=["Chatbot"]) # DISABLED
app.include_router(user_routes.router, prefix=f"{settings.API_PREFIX}/user", tags=["User"])
app.include_router(sse_routes.router, prefix=f"{settings.API_PREFIX}/sse", tags=["Real-Time"])

@app.on_event("startup")
async def startup():
    """Initialize resources on startup"""
    # Initialize Redis and Rate Limiter
    try:
        from services.redis_service import get_redis
        from fastapi_limiter import FastAPILimiter
        
        redis = await get_redis()
        # Ensure we have a valid redis object before init
        if redis:
            await FastAPILimiter.init(redis)
            logger.info("Rate limiter initialized")
        else:
            logger.warning("Redis client is None, skipping Rate Limiter init")
            
    except Exception as e:
        logger.error(f"Failed to initialize Redis/Rate Limiter: {e}")
        logger.warning("Application starting without Rate Limiting")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup resources on shutdown"""
    try:
        from services.redis_service import close_redis
        await close_redis()
    except Exception:
        pass

@app.get("/")
async def root():
    return {
        "name": "Vornics Weather AI API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    # Keep it simple for now to prevent timeouts
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "workers": 1
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG 
    )
