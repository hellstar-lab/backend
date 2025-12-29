"""
Multi-Layer Caching Service
Layer 1: In-Memory LRU (fastest, 1-minute TTL)
Layer 2: Redis (fast, 5-minute TTL)
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from functools import lru_cache

# Initialize logger
logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.enabled = True
        # In-memory store for Layer 1
        self._memory_cache: Dict[str, str] = {}
        self._memory_cache_expiry: Dict[str, datetime] = {}
        
    def _get_from_memory(self, key: str) -> Optional[str]:
        """Layer 1: In-memory cache check"""
        if key in self._memory_cache:
            expiry = self._memory_cache_expiry.get(key)
            if expiry and datetime.utcnow() < expiry:
                return self._memory_cache[key]
            else:
                # Lazy delete expired
                del self._memory_cache[key]
                del self._memory_cache_expiry[key]
        return None
    
    def _set_to_memory(self, key: str, value: str, ttl_seconds: int = 60):
        """Layer 1: Store in memory with short TTL"""
        self._memory_cache[key] = value
        self._memory_cache_expiry[key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data.
        Flow: Memory -> Redis -> None
        """
        if not self.enabled:
            return None
            
        try:
            # 1. Check Memory (L1)
            cached_str = self._get_from_memory(key)
            if cached_str:
                logger.debug(f"L1 Cache HIT: {key}")
                return json.loads(cached_str)
            
            # 2. Check Redis (L2)
            from services.redis_service import get_redis
            redis = await get_redis()
            cached_data = await redis.get(key)
            
            if cached_data:
                logger.info(f"L2 Redis HIT: {key}")
                # Backfill L1
                self._set_to_memory(key, cached_data, ttl_seconds=60)
                return json.loads(cached_data)
            
            logger.debug(f"Cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 300):
        """
        Set data in cache.
        Flow: Set Memory -> Set Redis
        """
        if not self.enabled:
            return
            
        try:
            json_str = json.dumps(value)
            
            # 1. Set Memory (L1) - Max 60s or provided TTL
            l1_ttl = min(60, ttl_seconds)
            self._set_to_memory(key, json_str, ttl_seconds=l1_ttl)
            
            # 2. Set Redis (L2)
            from services.redis_service import get_redis
            redis = await get_redis()
            await redis.setex(key, ttl_seconds, json_str)
            
            logger.info(f"Cache SET: {key} (L1: {l1_ttl}s, L2: {ttl_seconds}s)")
            
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
    
    async def delete(self, key: str):
        """Delete from all layers"""
        try:
            # Clear L1
            if key in self._memory_cache:
                del self._memory_cache[key]
                if key in self._memory_cache_expiry:
                    del self._memory_cache_expiry[key]
            
            # Clear L2
            from services.redis_service import get_redis
            redis = await get_redis()
            await redis.delete(key)
            
            logger.info(f"Cache DELETE: {key}")
            
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            
    def clear_memory(self):
        """Clear L1 cache only"""
        self._memory_cache.clear()
        self._memory_cache_expiry.clear()

# Global instance
cache_service = CacheService()
