# app/matches/routing.py
from django.urls import re_path
from .consumers import SignalingConsumer

websocket_urlpatterns = [
    re_path(r"^ws/signaling/(?P<session_id>[^/]+)/?$", SignalingConsumer.as_asgi()),
]
