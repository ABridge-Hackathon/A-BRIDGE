# app/matches/views.py
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import MatchSession
from app.matches.services import request_match
from app.matches.redis_store import save_session_state


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


class MatchRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        session = request_match(user)

        save_session_state(session, status=session.status)

        # 문서대로: sessionId만 반환 (envelope 없이)
        return Response({"sessionId": str(session.session_id)})


class MatchEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("sessionId") or request.data.get("session_id")
        if not session_id:
            return fail("VALIDATION_ERROR", "sessionId is required")

        session = MatchSession.objects.filter(session_id=session_id).first()
        if not session:
            return fail("SESSION_NOT_FOUND", "session not found", 404)

        # 세션 당사자만 종료 가능
        if (
            session.user_a_id != request.user.id
            and session.user_b_id != request.user.id
        ):
            return fail("FORBIDDEN", "not your session", 403)

        if session.status not in ("ENDED", "CANCELED"):
            session.status = "ENDED"
            session.ended_at = timezone.now()
            session.save(update_fields=["status", "ended_at"])
            save_session_state(session, status="ENDED")

        # 문서대로: ended만 반환 (envelope 없이)
        return Response({"ended": True})
