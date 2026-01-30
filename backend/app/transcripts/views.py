# app/transcripts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Transcript


class TranscriptCreateView(APIView):
    authentication_classes = []  # 더미: 인증 없이
    permission_classes = []

    """
    POST /api/match/sessions/<session_id>/transcripts
    body:
      {
        "items": [
          { "text": "..."},
          { "text": "..."}
        ]
      }
    """

    def post(self, request, session_id: str):
        items = request.data.get("items")
        if not isinstance(items, list):
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "items must be a list",
                    },
                },
                status=400,
            )

        rows = []
        for it in items:
            text = (it or {}).get("text")
            if not text:
                continue
            rows.append(Transcript(session_id=session_id, text=text, safe=True))

        if not rows:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": "VALIDATION_ERROR", "message": "no valid items"},
                },
                status=400,
            )

        Transcript.objects.bulk_create(rows)

        # 문서대로: inserted만 반환 (envelope 없이)
        return Response({"inserted": len(rows)})
