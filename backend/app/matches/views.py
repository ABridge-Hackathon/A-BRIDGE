# app/matches/views.py
from typing import Optional

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import MatchSession
from app.matches.services import request_match
from app.matches.redis_store import save_session_state

from app.user_locations.geocode import reverse_geocode_region


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


def _calc_age(user) -> Optional[int]:
    now_year = timezone.now().year
    if getattr(user, "birth_date", None):
        return now_year - user.birth_date.year
    if getattr(user, "birth_year", None):
        try:
            return now_year - int(user.birth_year)
        except Exception:
            return None
    return None


def _short_region(region: str) -> str:
    if not region:
        return ""
    parts = str(region).strip().split()
    return parts[-1] if parts else ""


class MatchRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        session = request_match(user)

        save_session_state(session, status=session.status)

        # 문서대로: sessionId만 반환
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

        return Response({"ended": True})


class CallSummaryView(APIView):
    """
    POST /api/match/call-summary
    body: { "sessionId": "uuid" }
    res: 상대 프로필
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("sessionId") or request.data.get("session_id")
        if not session_id:
            return fail("VALIDATION_ERROR", "sessionId is required")

        session = (
            MatchSession.objects.select_related(
                "user_a", "user_b", "user_a__location", "user_b__location"
            )
            .filter(session_id=session_id)
            .first()
        )
        if not session:
            return fail("SESSION_NOT_FOUND", "session not found", 404)

        if (
            session.user_a_id != request.user.id
            and session.user_b_id != request.user.id
        ):
            return fail("FORBIDDEN", "not your session", 403)

        peer = (
            session.user_b if session.user_a_id == request.user.id else session.user_a
        )
        if not peer:
            return fail("PEER_NOT_FOUND", "peer not found", 404)

        region_full = ""
        loc = getattr(peer, "location", None)
        lat = getattr(loc, "latitude", None) if loc else None
        lng = getattr(loc, "longitude", None) if loc else None

        if lat is not None and lng is not None:
            try:
                region_full = reverse_geocode_region(float(lat), float(lng))
            except Exception:
                region_full = ""

        if not region_full:
            region_full = getattr(peer, "address", "") or ""

        peer_payload = {
            "userId": peer.id,
            "name": peer.name,
            "age": _calc_age(peer),
            "gender": getattr(peer, "gender", "") or "",
            "regionDong": _short_region(region_full),
            "profileImageUrl": getattr(peer, "profile_image_url", "") or "",
        }

        return ok({"peer": peer_payload})
