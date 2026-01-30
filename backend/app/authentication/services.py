# app/auth/services.py
import hashlib
import os
import random
from datetime import timedelta


from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from app.sms_verifications.models import SmsVerification
from app.users.models import User


OTP_EXPIRE_SECONDS = 60
OTP_MAX_ATTEMPTS = 3


def _hash_code(code: str) -> str:
    # salt까지 섞어서 저장 (간단 버전)
    salt = os.environ.get("OTP_SALT", "dev-salt")
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def issue_otp(phone_number: str) -> None:
    code = f"{random.randint(0, 999999):06d}"
    code_hash = _hash_code(code)
    expires_at = timezone.now() + timedelta(seconds=OTP_EXPIRE_SECONDS)

    SmsVerification.objects.create(
        phone_number=phone_number,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    # TODO: 실제 SMS 전송으로 교체
    print(
        f"[DEV SMS] phone={phone_number} otp={code} (expires in {OTP_EXPIRE_SECONDS}s)"
    )


def verify_otp_and_issue_jwt(phone_number: str, code: str) -> str:
    now = timezone.now()

    v = (
        SmsVerification.objects.filter(
            phone_number=phone_number, verified_at__isnull=True, expires_at__gt=now
        )
        .order_by("-created_at")
        .first()
    )
    if not v:
        raise ValueError("OTP_NOT_FOUND_OR_EXPIRED")

    if v.attempt_count >= OTP_MAX_ATTEMPTS:
        raise ValueError("OTP_TOO_MANY_ATTEMPTS")

    if v.code_hash != _hash_code(code):
        v.attempt_count += 1
        v.save(update_fields=["attempt_count"])
        raise ValueError("OTP_INVALID_CODE")

    v.verified_at = now
    v.save(update_fields=["verified_at"])

    # 로그인: 유저가 이미 있으면 바로 JWT 발급, 없으면 "회원가입 필요" 상태로 보냄
    user = User.objects.filter(phone_number=phone_number, is_active=True).first()
    if not user:
        raise LookupError("USER_NOT_REGISTERED")

    user.is_phone_verified = True
    user.save(update_fields=["is_phone_verified"])

    token = AccessToken.for_user(user)
    return str(token)


def issue_jwt_for_user(user: User) -> str:
    token = AccessToken.for_user(user)
    return str(token)
