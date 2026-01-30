# app/user_locations/views.py
from app.user_locations.geocode import reverse_geocode_region
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

        lat = float(lat)
        lng = float(lng)

        region = reverse_geocode_region(lat, lng)  # 중요

        loc, _ = UserLocation.objects.update_or_create(
            user=request.user,
            defaults={
                "latitude": lat,
                "longitude": lng,
                "region": region,
            },
        )

        return Response(
            {
                "success": True,
                "data": {
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "region": loc.region,
                },
                "error": None,
            }
        )
