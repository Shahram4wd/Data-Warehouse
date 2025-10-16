"""
Global Concurrency Guard using Redis-based Semaphore

This module provides a semaphore implementation that limits concurrent tasks
across the entire cluster to prevent memory overload.
"""
import redis
import time
import logging
from contextlib import contextmanager
from typing import Optional
from decouple import config

logger = logging.getLogger(__name__)


def _get_django_settings():
    """Lazy import Django settings to avoid app loading issues"""
    try:
        from django.conf import settings
        return settings
    except Exception as e:
        logger.warning(f"Could not import Django settings: {e}")
        return None


class RedisSemaphore:
    """Redis-based semaphore for controlling global concurrency"""
    
    def __init__(self, key: str, max_permits: int = 2, timeout: float = 300.0):
        """
        Initialize Redis semaphore
        
        Args:
            key: Redis key for the semaphore
            max_permits: Maximum number of concurrent permits
            timeout: Timeout in seconds for acquiring permit
        """
        self.key = key
        self.max_permits = max_permits
        self.timeout = timeout
        self.redis_client = self._get_redis_client()
        
    def _get_redis_client(self) -> redis.Redis:
        """Get Redis client from Django settings"""
        try:
            # Try to get Redis URL from settings
            settings = _get_django_settings()
            redis_url = getattr(settings, 'CELERY_BROKER_URL', None) if settings else None
            if not redis_url:
                redis_url = config('REDIS_URL', default='redis://localhost:6379/0')
            
            return redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def acquire(self, identifier: Optional[str] = None, timeout: Optional[float] = None) -> bool:
        """
        Acquire a permit from the semaphore
        
        Args:
            identifier: Unique identifier for this permit (defaults to timestamp)
            timeout: Override default timeout
            
        Returns:
            True if permit acquired, False if timeout
        """
        if timeout is None:
            timeout = self.timeout
            
        if identifier is None:
            identifier = f"{time.time()}_{id(self)}"
            
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                # Use Redis pipeline for atomic operations
                pipe = self.redis_client.pipeline(transaction=True)
                
                # Clean up expired permits (older than 1 hour)
                cutoff = time.time() - 3600
                pipe.zremrangebyscore(self.key, '-inf', cutoff)
                
                # Count current permits
                pipe.zcard(self.key)
                
                results = pipe.execute()
                current_count = results[1] if len(results) > 1 else 0
                
                if current_count < self.max_permits:
                    # Try to add our permit
                    added = self.redis_client.zadd(
                        self.key, 
                        {identifier: time.time()},
                        nx=True  # Only add if not exists
                    )
                    
                    if added:
                        # Set expiration for the key to prevent Redis bloat
                        self.redis_client.expire(self.key, 3600)  # 1 hour
                        logger.info(f"Acquired permit {identifier} ({current_count + 1}/{self.max_permits})")
                        return True
                
                # Wait a bit before retrying
                time.sleep(0.1)
                
            except redis.RedisError as e:
                logger.error(f"Redis error acquiring permit: {e}")
                time.sleep(1)
        
        logger.warning(f"Failed to acquire permit {identifier} within {timeout}s timeout")
        return False
    
    def release(self, identifier: str) -> bool:
        """
        Release a permit from the semaphore
        
        Args:
            identifier: The identifier used when acquiring
            
        Returns:
            True if permit was released, False if not found
        """
        try:
            removed = self.redis_client.zrem(self.key, identifier)
            if removed:
                current_count = self.redis_client.zcard(self.key)
                logger.info(f"Released permit {identifier} ({current_count}/{self.max_permits})")
                return True
            else:
                logger.warning(f"Permit {identifier} not found for release")
                return False
                
        except redis.RedisError as e:
            logger.error(f"Redis error releasing permit: {e}")
            return False
    
    def current_count(self) -> int:
        """Get current number of active permits"""
        try:
            # Clean up expired permits first
            cutoff = time.time() - 3600
            self.redis_client.zremrangebyscore(self.key, '-inf', cutoff)
            return self.redis_client.zcard(self.key)
        except redis.RedisError as e:
            logger.error(f"Redis error getting count: {e}")
            return 0
    
    @contextmanager
    def acquire_context(self, identifier: Optional[str] = None, timeout: Optional[float] = None):
        """
        Context manager for acquiring and automatically releasing permits
        
        Usage:
            with semaphore.acquire_context("my_task") as acquired:
                if acquired:
                    # Do work
                    pass
        """
        if identifier is None:
            identifier = f"{time.time()}_{id(self)}"
            
        acquired = self.acquire(identifier, timeout)
        try:
            yield acquired
        finally:
            if acquired:
                self.release(identifier)


# Global semaphore instance
_global_semaphore = None


def get_global_semaphore() -> RedisSemaphore:
    """Get the global concurrency semaphore"""
    global _global_semaphore
    
    if _global_semaphore is None:
        max_concurrent = config('CELERY_WORKER_CONCURRENCY', default=2, cast=int)
        _global_semaphore = RedisSemaphore(
            key="datahub:semaphore:global",
            max_permits=max_concurrent,
            timeout=300.0  # 5 minute timeout
        )
    
    return _global_semaphore


@contextmanager
def global_concurrency_guard(task_name: str, timeout: float = 300.0):
    """
    Context manager for global concurrency control
    
    Usage:
        with global_concurrency_guard("sync_hubspot"):
            # Task work here - will be limited to global concurrent limit
            pass
    """
    semaphore = get_global_semaphore()
    identifier = f"{task_name}_{time.time()}"
    
    with semaphore.acquire_context(identifier, timeout) as acquired:
        if not acquired:
            raise Exception(f"Could not acquire concurrency permit for {task_name} within {timeout}s")
        yield


def force_release_all():
    """Emergency function to release all permits (for debugging)"""
    semaphore = get_global_semaphore()
    try:
        semaphore.redis_client.delete(semaphore.key)
        logger.warning("Force released all concurrency permits")
    except Exception as e:
        logger.error(f"Error force releasing permits: {e}")