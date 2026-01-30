# app/matches/redis_store.py
import json
import redis
from django.conf import settings

r = redis.Redis(
    host=getattr(settings, "REDIS_HOST", "127.0.0.1"),
    port=int(getattr(settings, "REDIS_PORT", 6379)),
    db=int(getattr(settings, "REDIS_DB", 0)),
    decode_responses=True,
)

def session_key(session_id: str) -> str:
    return f"match:session:{session_id}"

def save_session_state(session, *, status: str, ttl_sec: int = 3600):
    payload = {
        "sessionId": str(session.session_id),
        "status": status,
        "userAId": session.user_a_id,
        "userBId": session.user_b_id,
    }
    r.set(session_key(str(session.session_id)), json.dumps(payload), ex=ttl_sec)

def delete_session_state(session_id: str):
    r.delete(session_key(str(session_id)))
