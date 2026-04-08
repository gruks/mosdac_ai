"""Async Redis client with connection pool."""

from typing import Optional

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from src.gateway.config import settings


# Module-level connection pool (lazy initialization)
_connection_pool: Optional[ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get or create an async Redis client with connection pooling.

    The connection pool is created on first call and reused for subsequent calls.
    This ensures efficient connection management.

    Returns:
        An async Redis client instance.
    """
    global _connection_pool, _redis_client

    if _connection_pool is None:
        # Create connection pool with settings from config
        _connection_pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=False,
        )

    if _redis_client is None:
        # Create Redis client with the connection pool
        _redis_client = redis.Redis(connection_pool=_connection_pool)

    return _redis_client


async def check_redis_health() -> bool:
    """Check if Redis is available and responding.

    Returns:
        True if Redis is healthy, False otherwise.
    """
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except Exception:
        return False


async def close_redis_pool() -> None:
    """Close the Redis connection pool.

    Should be called on application shutdown.
    """
    global _connection_pool, _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None

    if _connection_pool is not None:
        await _connection_pool.disconnect()
        _connection_pool = None
