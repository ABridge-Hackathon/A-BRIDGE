# app/auth/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from app.users.models import User
from .services import issue_otp, verify_otp_and_issue_jwt, issue_jwt_for_user


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
        phone = request.data.get("phone_number")
        name = request.data.get("name")
        gender = request.data.get("gender")
        birth_year = request.data.get("birth_year")
        address = request.data.get("address")
        profile_image_url = request.data.get("profile_image_url", "")

        if not all([phone, name, gender, birth_year, address]):
            return fail("VALIDATION_ERROR", "missing required fields")

        if User.objects.filter(phone_number=phone).exists():
            return fail("PHONE_ALREADY_USED", "phone_number already exists", 409)

        user = User.objects.create(
            phone_number=phone,
            name=name,
            gender=gender,
            birth_year=int(birth_year),
            address=address,
            profile_image_url=profile_image_url,
            is_phone_verified=True,  #  가입=인증완료 처리
        )

        token = issue_jwt_for_user(user)  #  가입 직후 토큰 발급
        return ok({"userId": user.id, "accessToken": token, "tokenType": "Bearer"})

    authentication_classes = []
    permission_classes = []

    """
    가입: OCR 결과(이름/성별/출생년도/주소) + phone_number + profile_image_url
    (해커톤: OCR 업로드는 RN에서 처리하고, 결과 텍스트만 받는 걸로 시작)
    """

    def post(self, request):
        phone = request.data.get("phone_number")
        name = request.data.get("name")
        gender = request.data.get("gender")
        birth_year = request.data.get("birth_year")
        address = request.data.get("address")
        profile_image_url = request.data.get("profile_image_url", "")

        if not all([phone, name, gender, birth_year, address]):
            return fail("VALIDATION_ERROR", "missing required fields")

        if User.objects.filter(phone_number=phone).exists():
            return fail("PHONE_ALREADY_USED", "phone_number already exists", 409)

        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            gender=gender,
            birth_year=int(birth_year),
            address=address,
            profile_image_url=profile_image_url,
            is_phone_verified=False,
        )
        return ok({"userId": user.id})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # JWT는 서버 세션이 아니라서 "서버 로그아웃"이 실질적으로 없음.
        # 해커톤: 클라에서 토큰 삭제하면 로그아웃 완료.
        return ok({"loggedOut": True})


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user: User = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        return ok({"withdrawn": True})
