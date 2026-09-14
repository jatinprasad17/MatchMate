import os

import redis


def get_redis_client():
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    password = os.getenv("REDIS_PASSWORD")

    return redis.Redis(
        host=host,
        port=port,
        db=db,
        password=password,
        decode_responses=True,
    )


def get_cache(key: str):
    return get_redis_client().get(key)


def set_cache(key: str, value: str, ttl_seconds: int | None = None):
    client = get_redis_client()
    if ttl_seconds is None:
        return client.set(key, value)
    return client.set(key, value, ex=ttl_seconds)
