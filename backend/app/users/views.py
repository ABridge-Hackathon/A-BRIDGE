from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UserMeSerializer


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        forced_phone = getattr(settings, "DEMO_FORCE_USER_PHONE", None)

        if forced_phone:
            User = get_user_model()
            demo_user = User.objects.filter(
                phone_number=forced_phone, is_active=True
            ).first()
            if demo_user:
                serializer = UserMeSerializer(demo_user)
                return ok(serializer.data)

        serializer = UserMeSerializer(request.user)
        return ok(serializer.data)
