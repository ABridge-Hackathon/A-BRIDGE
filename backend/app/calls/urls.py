# app/calls/urls.py
from django.urls import path
from .views import FriendCallStartView

urlpatterns = [
    path("friend/start", FriendCallStartView.as_view()),
    path("friend/start/", FriendCallStartView.as_view()),
]
