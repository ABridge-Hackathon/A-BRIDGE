# app/auth/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from typing import Optional, Dict, Any
from app.users.models import User
from .services import issue_otp, verify_otp_and_issue_jwt, issue_jwt_for_user

from datetime import datetime
from .services import _normalize_phone
import json
from app.common.redis_client import get_redis
import secrets

ONBOARDING_TTL_SEC = 60 * 30


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


class OtpRequestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        phone = request.data.get("phoneNumber") or request.data.get("phone_number")
        if not phone:
            return fail("VALIDATION_ERROR", "phoneNumber is required")

        issue_otp(phone)
        from .services import OTP_EXPIRE_SECONDS

        return ok({"expiresInSec": OTP_EXPIRE_SECONDS})


class OtpVerifyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        phone = request.data.get("phoneNumber") or request.data.get("phone_number")
        code = request.data.get("code")
        if not phone or not code:
            return fail("VALIDATION_ERROR", "phoneNumber and code are required")

        # ✅ 스펙: 가입 여부에 따라 isRegistered 내려줌 (미가입을 에러로 보지 않음)
        phone_norm = _normalize_phone(phone)

        try:
            token = verify_otp_and_issue_jwt(phone_norm, code)
            return ok(
                {
                    "accessToken": token,
                    "tokenType": "Bearer",
                    "isRegistered": True,
                }
            )
        except LookupError:
            # USER_NOT_REGISTERED를 에러로 던지지 않고 스펙대로 응답
            return ok(
                {
                    "accessToken": None,
                    "tokenType": "Bearer",
                    "isRegistered": False,
                }
            )
        except ValueError as e:
            code_map = str(e)
            return fail(code_map, code_map)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        phone = request.data.get("phoneNumber") or request.data.get("phone_number")
        name = request.data.get("name")
        gender = request.data.get("gender")
        birth_year = request.data.get("birthYear") or request.data.get("birth_year")
        birth_date = request.data.get("birthDate") or request.data.get("birth_date")
        address = request.data.get("address")
        profile_image_url = request.data.get("profileImageUrl") or request.data.get(
            "profile_image_url", ""
        )

        if not all([phone, name, gender, birth_year, address]):
            return fail("VALIDATION_ERROR", "missing required fields")

        phone = _normalize_phone(phone)

        if User.objects.filter(phone_number=phone).exists():
            return fail("PHONE_ALREADY_USED", "phone_number already exists", 409)

        # birthDate 파싱(옵션)
        parsed_birth_date = None
        if birth_date:
            try:
                parsed_birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            except Exception:
                return fail("VALIDATION_ERROR", "birthDate must be YYYY-MM-DD")

        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            gender=gender,
            birth_year=int(birth_year),
            birth_date=parsed_birth_date,
            address=address,
            profile_image_url=profile_image_url,
            is_phone_verified=True,  # 해커톤: 가입=인증완료로 처리
        )

        token = issue_jwt_for_user(user)
        return ok({"userId": user.id, "accessToken": token, "tokenType": "Bearer"})


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user: User = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        return ok(None)  # ✅ data: null


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        user_id = request.data.get("userId") or request.data.get("user_id")
        if not user_id:
            return fail("VALIDATION_ERROR", "userId is required")

        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            return fail("USER_NOT_FOUND", "user not found", 404)

        token = issue_jwt_for_user(user)
        return ok({"accessToken": token, "tokenType": "Bearer"})


def _ob_key(token: str) -> str:
    return f"onboarding:{token}"


def issue_onboarding_token(payload: dict) -> str:
    token = "ob_" + secrets.token_urlsafe(24)
    r = get_redis()
    r.set(
        _ob_key(token), json.dumps(payload, ensure_ascii=False), ex=ONBOARDING_TTL_SEC
    )
    return token


def read_onboarding_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or not token.startswith("ob_"):
        return None
    r = get_redis()
    raw = r.get(_ob_key(token))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


class IdCardOcrView(APIView):
    """
    더미:
    - 어떤 요청이 와도 200 OK
    - form-data로 사진만 와도 OK
    - onboardingToken은 그냥 임의 문자열로 내려줌(저장/검증 안 함)
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # 프론트가 값 보내면 그걸로, 아니면 기본 더미
        name = request.data.get("name") or "홍길동"
        gender = request.data.get("gender") or "M"
        birth_date = request.data.get("birthDate") or "2003-09-15"
        address = request.data.get("address") or "수원시 팔달구"

        # ✅ 저장/검증 없이 그냥 랜덤 토큰 내려줌
        onboarding_token = "ob_dummy_" + secrets.token_urlsafe(12)

        return ok(
            {
                "onboardingToken": onboarding_token,
                "name": name,
                "gender": gender,
                "birthDate": birth_date,
                "address": address,
            }
        )


class ProfileImageUploadView(APIView):
    """
    더미:
    - Authorization 없어도 OK
    - form-data에 image 없어도 OK
    - 무조건 200 OK + 더미 profileImageUrl 반환
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # 실제 업로드 안 함. 그냥 응답만.
        profile_url = "https://example.com/profile.jpg"
        return ok({"profileImageUrl": profile_url})
