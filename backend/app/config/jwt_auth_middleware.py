# app/config/jwt_auth_middleware.py
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def get_user_from_token(token: str):
    """
    SimpleJWT 토큰 검증 후 유저 반환.
    실패 시 AnonymousUser 반환.
    """
    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(token)
        user = jwt_auth.get_user(validated)
        return user
    except Exception:
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    ws://.../?token=xxx 로 들어오는 JWT를 검증해서 scope['user']에 세팅
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        qs = parse_qs(query_string)
        token_list = qs.get("token", [])
        token = token_list[0] if token_list else None

        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
