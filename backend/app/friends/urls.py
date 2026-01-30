# app/friends/urls.py
from django.urls import path
from .views import FriendListView

urlpatterns = [
    path("", FriendListView.as_view()),  # GET/POST /api/friends/
]
