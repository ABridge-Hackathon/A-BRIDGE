# users/models.py
from django.db import models


class User(models.Model):
    GENDER_CHOICES = (("M", "Male"), ("F", "Female"))

    phone_number = models.CharField(max_length=20, unique=True)  # 로그인 키
    is_phone_verified = models.BooleanField(default=False)

    name = models.CharField(
        max_length=50, blank=True
    )  # OCR로 채움(가입 전엔 비어있을 수 있음)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    birth_year = models.IntegerField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)

    profile_image_url = models.TextField(blank=True)
    is_welfare_worker = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)  # 탈퇴/비활성
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.phone_number}"
