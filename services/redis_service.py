import os
import redis.asyncio as redis
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None

async def init_redis():
    """Initialize Redis connection with fallback to FakeRedis."""
    global _redis_client
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    try:
        # Try connecting to real Redis with short timeout
        _redis_client = redis.from_url(
            redis_url, 
            encoding="utf-8", 
            decode_responses=True, 
            socket_timeout=1.0,
            socket_connect_timeout=1.0
        )
        await _redis_client.ping()
        logger.info(f"Connected to Redis at {redis_url}")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        logger.info("Falling back to FakeRedis (In-Memory)")
        
        try:
            from fakeredis import aioredis
            _redis_client = aioredis.FakeRedis(decode_responses=True)
            logger.info("Initialized FakeRedis successfully")
        except ImportError:
            logger.error("fakeredis not installed. Cannot initialize Redis fallback.")
            raise

async def get_redis() -> redis.Redis:
    """Get the Redis client instance."""
    if _redis_client is None:
        await init_redis()
    return _redis_client

async def close_redis():
    """Close Redis connection."""
    if _redis_client:
        await _redis_client.close()
