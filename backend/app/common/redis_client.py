# app/common/redis_client.py
import redis
from django.conf import settings


_redis = None


def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,  # bytes 말고 str로 받게
        )
    return _redis