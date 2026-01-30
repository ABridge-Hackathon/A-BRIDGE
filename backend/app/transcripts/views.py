# app/transcripts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Transcript


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


class TranscriptCreateView(APIView):
    authentication_classes = []  # 해커톤 임시: 인증 없이
    permission_classes = []

    """
    POST /api/match/sessions/<session_id>/transcripts
    body:
      {
        "text": "....",
        "safe": true   (optional)
      }
    """

    def post(self, request, session_id: str):
        text = request.data.get("text")
        safe = request.data.get("safe", True)

        if not text:
            return fail("VALIDATION_ERROR", "text is required")

        t = Transcript.objects.create(
            session_id=session_id,
            text=text,
            safe=bool(safe),
        )

        return ok(
            {
                "transcriptId": t.id,
                "sessionId": str(t.session_id),
                "createdAt": t.created_at.isoformat(),
            }
        )
