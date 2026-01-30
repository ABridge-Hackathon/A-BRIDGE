# app/config/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
import app.matches.routing
import os
from app.config.jwt_auth_middleware import JwtAuthMiddlewareStack
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.config.settings")
application = ProtocolTypeRouter(
    {
        "websocket": JwtAuthMiddlewareStack(
            URLRouter(app.matches.routing.websocket_urlpatterns)
        ),
    }
)
