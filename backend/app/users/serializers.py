# app/users/serializers.py
from rest_framework import serializers
from .models import User


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "is_phone_verified",
            "name",
            "gender",
            "birth_year",
            "address",
            "profile_image_url",
            "is_welfare_worker",
            "is_active",
            "created_at",
        ]
