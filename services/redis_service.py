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
            # Try new fakeredis (v2+)
            from fakeredis import FakeRedis
            _redis_client = FakeRedis(decode_responses=True)
            logger.info("Initialized FakeRedis (v2+) successfully")
        except ImportError:
            try:
                # Try old fakeredis with aioredis
                from fakeredis import aioredis
                _redis_client = aioredis.FakeRedis(decode_responses=True)
                logger.info("Initialized FakeRedis (legacy) successfully")
            except ImportError:
                # Last resort: Mock object to prevent crash
                logger.error("fakeredis not installed. Using limit-less mock.")
                class MockRedis:
                    async def ping(self): return True
                    async def get(self, *args, **kwargs): return None
                    async def set(self, *args, **kwargs): return True
                    async def close(self): pass
                    def pipeline(self): return self
                    async def execute(self): return []
                    async def __aenter__(self): return self
                    async def __aexit__(self, *args): pass
                
                _redis_client = MockRedis()

async def get_redis() -> redis.Redis:
    """Get the Redis client instance."""
    if _redis_client is None:
        await init_redis()
    return _redis_client

async def close_redis():
    """Close Redis connection."""
    if _redis_client:
        await _redis_client.close()
