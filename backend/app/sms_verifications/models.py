# app/sms_verifications/models.py
from django.db import models


class SmsVerification(models.Model):
    phone_number = models.CharField(max_length=20)
    code_hash = models.CharField(max_length=255)  # 원문 저장 금지
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["expires_at"]),
        ]
