# app/adminpanel/urls.py
from django.urls import path
from .views import DashboardView, SeniorDetailView, CallDetailView

urlpatterns = [
    path("", DashboardView.as_view(), name="adminpanel-dashboard"),
    path(
        "seniors/<int:senior_id>/",
        SeniorDetailView.as_view(),
        name="adminpanel-senior-detail",
    ),
    path(
        "calls/<uuid:call_id>/", CallDetailView.as_view(), name="adminpanel-call-detail"
    ),
]
