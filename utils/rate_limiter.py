"""
Rate Limiter Utility
Decorator for API rate limiting
"""

from fastapi import HTTPException, Request
from typing import Optional
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter for demonstration
# In production, use Redis or Firestore
class RateLimiter:
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        
        if len(self.requests[key]) >= limit:
            return False
        
        self.requests[key].append(now)
        return True

limiter = RateLimiter()

def rate_limit(limit: int = 100, window: int = 60):
    """
    Rate limit decorator.
    
    Args:
        limit: Max requests
        window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Use IP or user ID as key
            key = request.client.host
            
            if not limiter.is_allowed(key, limit, window):
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
