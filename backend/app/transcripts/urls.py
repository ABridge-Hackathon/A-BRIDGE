# app/transcripts/urls.py
from django.urls import path
from .views import TranscriptCreateView

urlpatterns = [
    path(
        "match/sessions/<str:session_id>/transcripts/",
        TranscriptCreateView.as_view(),
    ),
]
