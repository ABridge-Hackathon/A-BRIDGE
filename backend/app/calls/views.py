# app/calls/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from app.users.models import User
from app.friends.models import Friend
from app.matches.models import MatchSession
from app.matches.redis_store import save_session_state


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


class FriendCallStartView(APIView):
    """
    POST /api/calls/friend/start
    body: { "targetUserId": 42 }
    res: { sessionId }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        target_user_id = request.data.get("targetUserId")
        if not target_user_id:
            return fail("VALIDATION_ERROR", "targetUserId is required")

        if str(target_user_id) == str(request.user.id):
            return fail("VALIDATION_ERROR", "cannot call yourself")

        target = User.objects.filter(id=target_user_id, is_active=True).first()
        if not target:
            return fail("USER_NOT_FOUND", "target user not found", 404)

        #  친구인지 검증(친구목록에서 눌러서 전화니까)
        is_friend = Friend.objects.filter(
            user=request.user, friend_user=target
        ).exists()
        if not is_friend:
            return fail("NOT_FRIEND", "target is not your friend", 403)

        #  이미 둘 사이에 진행중 세션 있으면 재사용(해커톤 안전장치)
        existing = (
            MatchSession.objects.filter(user_a=request.user, user_b=target)
            .exclude(status__in=["ENDED", "CANCELED"])
            .order_by("-started_at")
            .first()
        )
        if existing:
            save_session_state(existing, status=existing.status)
            return ok({"sessionId": str(existing.session_id), "reused": True})

        #  새 세션 생성: friend-call은 바로 MATCHED(or CALLING)
        session = MatchSession.objects.create(
            user_a=request.user,
            user_b=target,
            status="MATCHED",  # 또는 "CALLING"으로 통일해도 됨
            started_at=timezone.now(),  # auto_now_add라 없어도 되지만 명시 OK
        )

        save_session_state(session, status=session.status)
        return ok({"sessionId": str(session.session_id), "reused": False})
