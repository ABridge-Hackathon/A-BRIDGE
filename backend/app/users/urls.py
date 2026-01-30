# app/users/urls.py
from django.urls import path
from .views import MeView

urlpatterns = [
    path("me/", MeView.as_view()),  # GET /api/users/me/
    path("me", MeView.as_view()),  # GET /api/users/me/
]
