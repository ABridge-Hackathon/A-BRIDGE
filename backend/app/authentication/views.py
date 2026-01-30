# app/auth/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from app.users.models import User
from .services import issue_otp, verify_otp_and_issue_jwt, issue_jwt_for_user

from datetime import datetime
from .services import _normalize_phone


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


class OtpRequestView(APIView):
    authentication_classes = []  # 인증 없이
    permission_classes = []

    def post(self, request):
        phone = request.data.get("phone_number")
        if not phone:
            return fail("VALIDATION_ERROR", "phone_number is required")

        issue_otp(phone)
        return ok({"sent": True})


class OtpVerifyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        phone = request.data.get("phone_number")
        code = request.data.get("code")
        if not phone or not code:
            return fail("VALIDATION_ERROR", "phone_number and code are required")

        try:
            token = verify_otp_and_issue_jwt(phone, code)
            return ok({"accessToken": token, "tokenType": "Bearer"})
        except LookupError:
            # 유저가 아직 없으면 회원가입 하라고 내려줌
            return fail("USER_NOT_REGISTERED", "register is required", 404)
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
        return ok({"withdrawn": True})
