# app/users/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UserMeSerializer


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return ok(serializer.data)
