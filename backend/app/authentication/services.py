# app/auth/services.py
import hashlib
import os
import random
import re
from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from solapi import SolapiMessageService
from solapi.model import RequestMessage

from app.sms_verifications.models import SmsVerification
from app.users.models import User

OTP_EXPIRE_SECONDS = 60
OTP_MAX_ATTEMPTS = 3


def _hash_code(code: str) -> str:
    salt = os.environ.get("OTP_SALT", "dev-salt")
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def _normalize_phone(phone: str) -> str:
    # 010-1234-5678 / 010 1234 5678 -> 01012345678
    return re.sub(r"[^0-9]", "", str(phone or ""))


def _solapi_client() -> SolapiMessageService:
    api_key = os.environ.get("SOLAPI_API_KEY", "")
    api_secret = os.environ.get("SOLAPI_API_SECRET", "")
    if not api_key or not api_secret:
        raise RuntimeError("SOLAPI_API_KEY / SOLAPI_API_SECRET not set")
    return SolapiMessageService(api_key=api_key, api_secret=api_secret)


def issue_otp(phone_number: str) -> None:
    to_number = _normalize_phone(phone_number)
    if not to_number:
        raise ValueError("INVALID_PHONE_NUMBER")

    code = f"{random.randint(0, 99999):05d}"  # ✅ 5자리
    code_hash = _hash_code(code)
    expires_at = timezone.now() + timedelta(seconds=OTP_EXPIRE_SECONDS)

    # 1) OTP 저장
    SmsVerification.objects.create(
        phone_number=to_number,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    # 2) SMS 발송
    from_number = _normalize_phone(os.environ.get("SOLAPI_FROM_NUMBER", ""))
    if not from_number:
        raise RuntimeError("SOLAPI_FROM_NUMBER not set")

    text = f"[함보까] 인증번호는 {code} 입니다. {OTP_EXPIRE_SECONDS}초 이내 입력하세요."

    client = _solapi_client()
    message = RequestMessage(
        from_=from_number,
        to=to_number,
        text=text,
    )

    try:
        # SOLAPI Python SDK 예제 방식
        res = client.send(message)
        print("[SOLAPI] send result:", res)
    except Exception as e:
        # 해커톤: 일단 로그만 보고 넘어감
        raise RuntimeError(f"SOLAPI_SEND_FAILED: {e}")


def verify_otp_and_issue_jwt(phone_number: str, code: str) -> str:
    phone = _normalize_phone(phone_number)
    now = timezone.now()

    v = (
        SmsVerification.objects.filter(
            phone_number=phone,
            verified_at__isnull=True,
            expires_at__gt=now,
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

    # 인증 성공
    v.verified_at = now
    v.save(update_fields=["verified_at"])

    user = User.objects.filter(phone_number=phone, is_active=True).first()
    if not user:
        raise LookupError("USER_NOT_REGISTERED")

    user.is_phone_verified = True
    user.save(update_fields=["is_phone_verified"])

    token = AccessToken.for_user(user)
    return str(token)


def issue_jwt_for_user(user: User) -> str:
    token = AccessToken.for_user(user)
    return str(token)
