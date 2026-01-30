# app/friends/urls.py
from django.urls import path
from .views import FriendListView, FriendAddView

urlpatterns = [
    path("", FriendListView.as_view()),  # GET /api/friends
    path("add", FriendAddView.as_view()),  # POST /api/friends/add
]
