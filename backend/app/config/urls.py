# app/config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("app.authentication.urls")),
    path("api/users/", include("app.users.urls")),
    path("api/me/", include("app.user_locations.urls")),  # /me/location 같은 거
    path("api/friends/", include("app.friends.urls")),
    path("api/match/", include("app.matches.urls")),
    path(
        "api/", include("app.transcripts.urls")
    ),  # /match/sessions/... 같은 경우 여기서 잡아도 됨
]
