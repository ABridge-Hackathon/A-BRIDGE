# app/matches/urls.py
from django.urls import path
from .views import MatchRequestView, MatchEndView,CallSummaryView

urlpatterns = [
    path("request", MatchRequestView.as_view()),
    path("request/", MatchRequestView.as_view()),
    path("end", MatchEndView.as_view()),
    path("end/", MatchEndView.as_view()),
    path("call-summary", CallSummaryView.as_view()),
    path("call-summary/", CallSummaryView.as_view()),
]
