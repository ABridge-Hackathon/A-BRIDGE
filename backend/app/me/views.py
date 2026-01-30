# app/me/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from app.common.redis_client import get_redis

PRESENCE_TTL_SEC = 70  # 프론트가 30초마다 ping하면 안전


def presence_key(user_id: int) -> str:
    return f"presence:user:{user_id}"


class PresencePingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        r = get_redis()
        r.set(presence_key(request.user.id), "1", ex=PRESENCE_TTL_SEC)
        return Response({"success": True, "data": {"ok": True}, "error": None})
