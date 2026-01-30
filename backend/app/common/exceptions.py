from rest_framework.views import exception_handler
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(exc, NotAuthenticated):
        response.data = {
            "success": False,
            "data": None,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Authorization header missing",
            },
        }
    elif isinstance(exc, PermissionDenied):
        response.data = {
            "success": False,
            "data": None,
            "error": {"code": "FORBIDDEN", "message": "Permission denied"},
        }
    elif isinstance(exc, (InvalidToken, TokenError)):
        # 만료/위조를 더 정확히 나누려면 exc.detail 내용으로 분기
        response.data = {
            "success": False,
            "data": None,
            "error": {"code": "INVALID_TOKEN", "message": "Invalid token"},
        }

    return response
