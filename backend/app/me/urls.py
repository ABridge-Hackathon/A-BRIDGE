# app/me/urls.py
from django.urls import path
from .views import PresencePingView

urlpatterns = [
    path("presence", PresencePingView.as_view()),  # POST /api/me/presence
    path("presence/", PresencePingView.as_view()),  # POST /api/me/presence
]
