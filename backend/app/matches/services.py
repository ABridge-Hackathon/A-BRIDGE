# app/auth/services.py
import hashlib
import os
import random
from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from app.sms_verifications.models import SmsVerification
from app.users.models import User

# solapi 추가
from solapi import SolapiMessageService
from solapi.model import RequestMessage

OTP_EXPIRE_SECONDS = 300
OTP_MAX_ATTEMPTS = 3


def _hash_code(code: str) -> str:
    salt = os.environ.get("OTP_SALT", "dev-salt")
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def _solapi_client() -> SolapiMessageService:
    api_key = os.environ.get("SOLAPI_API_KEY", "")
    api_secret = os.environ.get("SOLAPI_API_SECRET", "")
    if not api_key or not api_secret:
        raise RuntimeError("SOLAPI_API_KEY / SOLAPI_API_SECRET not set")
    return SolapiMessageService(api_key=api_key, api_secret=api_secret)


def issue_otp(phone_number: str) -> None:
    code = f"{random.randint(0, 999999):06d}"
    code_hash = _hash_code(code)
    expires_at = timezone.now() + timedelta(seconds=OTP_EXPIRE_SECONDS)

    # 1) OTP 저장
    SmsVerification.objects.create(
        phone_number=phone_number,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    # 2) SMS 발송
    from_number = os.environ.get("SOLAPI_FROM_NUMBER", "")
    if not from_number:
        raise RuntimeError("SOLAPI_FROM_NUMBER not set")

    text = (
        f"[ASCII] 인증번호는 {code} 입니다. {OTP_EXPIRE_SECONDS}초 이내 입력 해주세요"
    )

    client = _solapi_client()
    message = RequestMessage(
        from_=from_number,  # 01012345678 (하이픈X)
        to=phone_number,  # 01012345678 (하이픈X)
        text=text,
    )

    try:
        client.send(message)
    except Exception as e:
        # 해커톤이면 여기서 실패 로그만 찍고,
        # 실제로는 "재시도"나 "OTP row 삭제" 등을 선택하면 됨
        raise RuntimeError(f"SOLAPI_SEND_FAILED: {str(e)}")


def request_match(user):
    my_loc = UserLocation.objects.filter(user=user).first()

    candidates = (
        MatchSession.objects.filter(status="WAITING")
        .exclude(user_a=user)
        .select_for_update(skip_locked=True)
        .order_by("started_at")[:20]
    )

    best = None
    for c in candidates:
        peer_loc = UserLocation.objects.filter(user=c.user_a).first()
        if my_loc and peer_loc:
            d = haversine_km(
                my_loc.latitude, my_loc.longitude, peer_loc.latitude, peer_loc.longitude
            )
        else:
            d = 9999  # 위치 없으면 맨 뒤
        if best is None or d < best[0]:
            best = (d, c)

    if not best:
        return create_waiting_session(user)
