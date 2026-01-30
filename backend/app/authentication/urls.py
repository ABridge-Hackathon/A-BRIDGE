from django.urls import path
from .views import (
    OtpRequestView,
    OtpVerifyView,
    RegisterView,
    WithdrawView,
    LoginView,
    IdCardOcrView,
    ProfileImageUploadView,
    DevJwtIssueView,
)

urlpatterns = [
    path("idcard/ocr/", IdCardOcrView.as_view()),
    path("profile-image/", ProfileImageUploadView.as_view()),
    path("otp/request/", OtpRequestView.as_view()),
    path("otp/verify/", OtpVerifyView.as_view()),
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    # path("logout/", LogoutView.as_view()),
    path("withdraw/", WithdrawView.as_view()),
    path("idcard/ocr", IdCardOcrView.as_view()),
    path("profile-image", ProfileImageUploadView.as_view()),
    path("otp/request", OtpRequestView.as_view()),
    path("otp/verify", OtpVerifyView.as_view()),
    path("register", RegisterView.as_view()),
    path("login", LoginView.as_view()),
    # path("logout", LogoutView.as_view()),
    path("withdraw", WithdrawView.as_view()),
    # 개발용 JWT
    path("jwt/dev/", DevJwtIssueView.as_view()),
    # (슬래시 없는 버전 유지 시)
    path("jwt/dev", DevJwtIssueView.as_view()),
]
