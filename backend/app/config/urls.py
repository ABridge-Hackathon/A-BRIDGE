# app/config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


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
    path("api/me/", include("app.me.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
