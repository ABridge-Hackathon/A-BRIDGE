# app/matches/views.py
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import MatchSession
from app.matches.services import request_match, save_session_state, delete_session_state


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


class MatchRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user  # JWT로 식별

        result = request_match(user)
        session = result["session"]

        # Redis에 세션 상태 저장 (WAITING/MATCHED/CANCELED 등)
        save_session_state(session, status=session.status)

        return ok(
            {
                "sessionId": str(session.session_id),
                "status": session.status,
                "matched": result.get("matched", False),
                "peerUserId": result.get("peer_user_id"),
                "distanceKm": result.get("distance_km"),
            }
        )


class MatchEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id") or request.data.get("sessionId")
        if not session_id:
            return fail("VALIDATION_ERROR", "session_id is required")

        session = MatchSession.objects.filter(session_id=session_id).first()
        if not session:
            return fail("SESSION_NOT_FOUND", "session not found", 404)

        # 세션 당사자만 종료 가능
        if (
            session.user_a_id != request.user.id
            and session.user_b_id != request.user.id
        ):
            return fail("FORBIDDEN", "not your session", 403)

        if session.status in ("ENDED", "CANCELED"):
            return ok({"sessionId": str(session.session_id), "status": session.status})

        session.status = "ENDED"
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at"])

        # Redis에도 종료 반영 (둘 중 하나 선택)
        save_session_state(session, status="ENDED")
        # 해커톤이면 종료 시 바로 삭제하고 싶으면 아래로 바꾸기:
        # delete_session_state(str(session.session_id))

        return ok({"sessionId": str(session.session_id), "status": session.status})
