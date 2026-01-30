# app/user_locations/views.py

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.user_locations.models import UserLocation


class MyLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lat = request.data.get("latitude")
        lng = request.data.get("longitude")

        if lat is None or lng is None:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "latitude/longitude required",
                    },
                },
                status=400,
            )

        loc, _ = UserLocation.objects.update_or_create(
            user=request.user,
            defaults={"latitude": float(lat), "longitude": float(lng)},
        )

        return Response(
            {
                "success": True,
                "data": {"latitude": loc.latitude, "longitude": loc.longitude},
                "error": None,
            }
        )

    def get(self, request):
        loc = getattr(request.user, "location", None)
        if not loc:
            return Response({"success": True, "data": None, "error": None})
        return Response(
            {
                "success": True,
                "data": {"latitude": loc.latitude, "longitude": loc.longitude},
                "error": None,
            }
        )
