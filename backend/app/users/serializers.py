# app/users/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import User


class UserMeSerializer(serializers.ModelSerializer):
    userId = serializers.IntegerField(source="id", read_only=True)
    phoneNumber = serializers.CharField(source="phone_number", read_only=True)
    profileImageUrl = serializers.CharField(source="profile_image_url", read_only=True)
    isWelfareWorker = serializers.BooleanField(
        source="is_welfare_worker", read_only=True
    )

    birthDate = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "userId",
            "name",
            "gender",
            "birthDate",
            "age",
            "region",
            "phoneNumber",
            "profileImageUrl",
            "isWelfareWorker",
        ]

    def get_birthDate(self, obj: User):
        return obj.birth_date.isoformat() if obj.birth_date else None

    def get_age(self, obj: User):
        # birth_date 있으면 그걸로, 없으면 birth_year로 대충 계산
        now_year = timezone.now().year
        if obj.birth_date:
            # 한국식 나이/만나이 정책 정하기 전이면 “대략”은 연도로만
            return now_year - obj.birth_date.year
        if obj.birth_year:
            return now_year - obj.birth_year
        return None

    def get_region(self, obj: User):
        loc = getattr(obj, "location", None)
        if loc and getattr(loc, "region", ""):
            return loc.region
        # fallback: 주소에서 대충 보여주기
        return obj.address
