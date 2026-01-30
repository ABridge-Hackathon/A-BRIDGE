# app/friends/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from app.friends.models import Friend
from app.users.models import User


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


class FriendListView(APIView):
    permission_classes = [IsAuthenticated]

    # GET /api/friends/
    def get(self, request):
        qs = (
            Friend.objects.filter(user=request.user)
            .select_related("friend_user")
            .order_by("-created_at")
        )

        items = []
        for f in qs:
            u = f.friend_user
            items.append(
                {
                    "friendUserId": u.id,
                    "name": u.name,
                    "birthYear": u.birth_year,
                    "address": u.address,
                    "profileImageUrl": u.profile_image_url,
                    "isWelfareWorker": u.is_welfare_worker,
                    # 온라인 여부는 Redis presence 붙일 때 추가
                    "isOnline": False,
                    "createdAt": f.created_at.isoformat(),
                }
            )

        return ok({"items": items, "count": len(items)})

    # POST /api/friends/
    # body: { "friend_user_id": 123 }
    def post(self, request):
        friend_user_id = request.data.get("friend_user_id")
        if not friend_user_id:
            return fail("VALIDATION_ERROR", "friend_user_id is required")

        if str(friend_user_id) == str(request.user.id):
            return fail("INVALID_FRIEND", "cannot add yourself")

        friend_user = User.objects.filter(id=friend_user_id, is_active=True).first()
        if not friend_user:
            return fail("USER_NOT_FOUND", "friend user not found", 404)

        # 중복 방지
        obj, created = Friend.objects.get_or_create(
            user=request.user, friend_user=friend_user
        )
        if not created:
            return ok({"added": False})  # 이미 친구

        return ok({"added": True, "friendUserId": friend_user.id})
