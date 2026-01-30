# app/user_locations/urls.py
from django.urls import path
from .views import MyLocationView

urlpatterns = [
    path("location", MyLocationView.as_view()),  # /api/me/location
]
