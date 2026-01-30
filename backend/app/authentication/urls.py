from django.urls import path
from .views import OtpRequestView, OtpVerifyView, RegisterView, WithdrawView

urlpatterns = [
    path("otp/request/", OtpRequestView.as_view()),
    path("otp/verify/", OtpVerifyView.as_view()),
    path("register/", RegisterView.as_view()),
    # path("logout/", LogoutView.as_view()),
    path("withdraw/", WithdrawView.as_view()),
]
