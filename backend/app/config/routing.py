# app/config/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
import app.matches.routing

from app.config.jwt_auth_middleware import JwtAuthMiddlewareStack

application = ProtocolTypeRouter(
    {
        "websocket": JwtAuthMiddlewareStack(
            URLRouter(app.matches.routing.websocket_urlpatterns)
        ),
    }
)
