# app/auth/views.py
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.users.models import User
from .services import issue_otp, issue_jwt_for_user, _normalize_phone, verify_otp_only
from .onboarding import (
    issue_onboarding_token,
    read_onboarding_token,
    write_onboarding_token,
    delete_onboarding_token,
)


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


def _dbg(request, label: str):
    """
    form-data 400 원인 잡는 용:
    - content-type boundary 포함 여부
    - request.data / request.FILES 파싱 여부
    - Authorization 헤더 유무
    """
    try:
        print(f"\n[DBG] {label}")
        print("  method:", request.method)
        print("  path:", getattr(request, "path", ""))
        print("  content-type:", request.content_type)
        print("  auth:", request.headers.get("Authorization"))
        print("  data keys:", list(getattr(request, "data", {}).keys()))
        print("  files keys:", list(getattr(request, "FILES", {}).keys()))
        # 프론트가 어떤 키로 보내는지 확인용(너무 크면 안 찍힘)
        if hasattr(request, "data"):
            # 값까지는 길어서 keys만으로 충분. 필요하면 아래 주석 해제
            # print("  data:", dict(request.data))
            pass
    except Exception as e:
        print("[DBG] failed:", e)


class OtpRequestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        _dbg(request, "OtpRequestView")

        phone = request.data.get("phoneNumber") or request.data.get("phone_number")
        if not phone:
            return fail("VALIDATION_ERROR", "phoneNumber is required")

        issue_otp(phone)
        from .services import OTP_EXPIRE_SECONDS  # 5분(300초) 유지

        return ok({"expiresInSec": OTP_EXPIRE_SECONDS})


class OtpVerifyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        _dbg(request, "OtpVerifyView")

        phone = request.data.get("phoneNumber") or request.data.get("phone_number")
        code = request.data.get("code")
        onboarding_token = request.data.get(
            "onboardingToken"
        )  # 회원가입 플로우에서만 존재

        if not phone or not code:
            return fail("VALIDATION_ERROR", "phoneNumber and code are required")

        phone_norm = _normalize_phone(phone)

        # 1) OTP 검증 (유저 존재 여부와 무관)
        try:
            verify_otp_only(phone_norm, code)
        except ValueError as e:
            code_map = str(e)
            return fail(code_map, code_map)

        # 2) 기존 유저면 로그인(바로 JWT 발급)
        user = User.objects.filter(phone_number=phone_norm, is_active=True).first()
        if user:
            if not user.is_phone_verified:
                user.is_phone_verified = True
                user.save(update_fields=["is_phone_verified"])

            token = issue_jwt_for_user(user)
            return ok(
                {"accessToken": token, "tokenType": "Bearer", "isRegistered": True}
            )

        # 3) 유저 없으면: onboardingToken 있으면 회원가입 생성 후 로그인
        if onboarding_token:
            ob = read_onboarding_token(onboarding_token)
            if not ob:
                return fail(
                    "INVALID_ONBOARDING_TOKEN",
                    "invalid or expired onboardingToken",
                    401,
                )

            name = ob.get("name") or "홍길동"
            gender = ob.get("gender") or "M"
            birth_date = ob.get("birthDate") or "2003-09-15"
            address = ob.get("address") or "수원시 팔달구"
            profile_url = ob.get("profileImageUrl") or ""

            try:
                parsed_birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            except Exception:
                return fail("VALIDATION_ERROR", "birthDate must be YYYY-MM-DD")

            birth_year = parsed_birth_date.year

            # 혹시 사이에 같은 번호로 가입된 경우 방어
            existing = User.objects.filter(
                phone_number=phone_norm, is_active=True
            ).first()
            if existing:
                token = issue_jwt_for_user(existing)
                delete_onboarding_token(onboarding_token)
                return ok(
                    {"accessToken": token, "tokenType": "Bearer", "isRegistered": True}
                )

            user = User.objects.create_user(
                phone_number=phone_norm,
                name=name,
                gender=gender,
                birth_year=birth_year,
                birth_date=parsed_birth_date,
                address=address,
                profile_image_url=profile_url,
                is_phone_verified=True,
            )

            delete_onboarding_token(onboarding_token)

            token = issue_jwt_for_user(user)
            return ok(
                {"accessToken": token, "tokenType": "Bearer", "isRegistered": True}
            )

        # 4) 유저 없고 onboardingToken도 없음 -> 회원가입 필요
        return ok({"accessToken": None, "tokenType": "Bearer", "isRegistered": False})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        _dbg(request, "RegisterView")

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

        phone_norm = _normalize_phone(phone)

        if User.objects.filter(phone_number=phone_norm).exists():
            return fail("PHONE_ALREADY_USED", "phone_number already exists", 409)

        parsed_birth_date = None
        if birth_date:
            try:
                parsed_birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            except Exception:
                return fail("VALIDATION_ERROR", "birthDate must be YYYY-MM-DD")

        user = User.objects.create_user(
            phone_number=phone_norm,
            name=name,
            gender=gender,
            birth_year=int(birth_year),
            birth_date=parsed_birth_date,
            address=address,
            profile_image_url=profile_image_url,
            is_phone_verified=True,
        )

        token = issue_jwt_for_user(user)
        return ok({"userId": user.id, "accessToken": token, "tokenType": "Bearer"})


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _dbg(request, "WithdrawView")

        user: User = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        return ok(None)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        _dbg(request, "LoginView")

        user_id = request.data.get("userId") or request.data.get("user_id")
        if not user_id:
            return fail("VALIDATION_ERROR", "userId is required")

        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            return fail("USER_NOT_FOUND", "user not found", 404)

        token = issue_jwt_for_user(user)
        return ok({"accessToken": token})


class IdCardOcrView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        _dbg(request, "IdCardOcrView")

        # 프론트가 보내는 키: id_image
        img = request.FILES.get("id_image")
        if not img:
            return fail("VALIDATION_ERROR", "id_image is required")

        # 더미(또는 OCR 결과) + onboardingToken
        name = "김순자"
        gender = "F"
        birth_date = "1953-09-15"
        address = "수원시 팔달구"

        payload = {
            "name": name,
            "gender": gender,
            "birthDate": birth_date,
            "address": address,
            "profileImageUrl": "",
        }
        onboarding_token = issue_onboarding_token(payload)

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
    authentication_classes = []
    permission_classes = []

    # POST /api/auth/profile-image (form-data: image)
    def post(self, request):
        _dbg(request, "ProfileImageUploadView")

        # 1) onboardingToken: Authorization Bearer or form-data field
        auth = request.headers.get("Authorization", "")
        token = None
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
        if not token:
            token = request.data.get("onboardingToken")

        payload = read_onboarding_token(token)
        if not payload:
            return fail(
                "INVALID_ONBOARDING_TOKEN", "invalid or expired onboardingToken", 401
            )

        img = (
            request.FILES.get("image")
            or request.FILES.get("id_image")
            or request.FILES.get("file")
        )
        if not img:
            return fail("VALIDATION_ERROR", "image is required")

        # 2) 로컬 저장: onboarding_profiles/<token>.<ext>
        filename = img.name or "profile.jpg"
        ext = ".jpg"
        if "." in filename:
            maybe = "." + filename.split(".")[-1].lower()
            if maybe in [".jpg", ".jpeg", ".png", ".webp"]:
                ext = maybe

        path = f"onboarding_profiles/{token}{ext}"
        saved_path = default_storage.save(path, ContentFile(img.read()))

        media_url = getattr(settings, "MEDIA_URL", "/media/")
        if not media_url.endswith("/"):
            media_url += "/"
        profile_url = media_url + saved_path

        # 3) onboarding payload 업데이트
        payload["profileImageUrl"] = profile_url
        write_onboarding_token(token, payload)

        return ok({"profileImageUrl": profile_url})


class DevJwtIssueView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        _dbg(request, "DevJwtIssueView")

        # ⚠️ 해커톤/개발용 고정 유저
        user, _ = User.objects.get_or_create(
            phone_number="00000000000",
            defaults={
                "name": "DEV_USER",
                "gender": "M",
                "birth_year": 1970,
                "address": "DEV",
                "is_phone_verified": True,
            },
        )

        token = issue_jwt_for_user(user)

        return ok(
            {
                "accessToken": token,
                "tokenType": "Bearer",
                "isRegistered": True,
            }
        )
