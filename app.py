"""
Main FastAPI Application Entry Point (Step 3 - Phase 1: Infrastructure)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

# Import configuration
from config import settings
# import sentry_sdk

# Initialize Sentry (Disabled for Phase 1)
# if settings.SENTRY_DSN:
#     sentry_sdk.init(
#         dsn=settings.SENTRY_DSN,
#         traces_sample_rate=1.0,
#         environment=settings.ENVIRONMENT,
#     )

# Import routes (DISABLED)
# from api import auth_routes
# from api import weather_routes, history_routes, alerts_routes
# from api import chatbot_routes  
# from api import user_routes
# from api import sse_routes

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
    description="Incremental Test Phase 1",
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

# Include routers (DISABLED)
# app.include_router(auth_routes.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
# app.include_router(weather_routes.router, prefix=f"{settings.API_PREFIX}/weather", tags=["Weather"])
# app.include_router(user_routes.router, prefix=f"{settings.API_PREFIX}/user", tags=["User"])

@app.get("/")
async def root():
    return {
        "status": "ok",
        "phase": "1_infrastructure",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "phase": "1_infrastructure"}
