# app/friends/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from app.friends.models import Friend
from app.users.models import User
from app.common.redis_client import get_redis

MAX_TOTAL = 100
DEFAULT_LIMIT = 6
MAX_LIMIT = 6


def ok(data=None):
    return Response({"success": True, "data": data, "error": None})


def fail(code: str, message: str, http_status: int = 400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}},
        status=http_status,
    )


def presence_key(user_id: int) -> str:
    return f"presence:user:{user_id}"


class FriendListView(APIView):
    permission_classes = [IsAuthenticated]

    # GET /api/friends?offset=0&limit=6
    def get(self, request):
        try:
            offset = int(request.query_params.get("offset", 0))
        except Exception:
            offset = 0
        try:
            limit = int(request.query_params.get("limit", DEFAULT_LIMIT))
        except Exception:
            limit = DEFAULT_LIMIT

        if offset < 0:
            offset = 0
        if limit <= 0:
            limit = DEFAULT_LIMIT
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        # 1) DB에서 최신순으로 100명까지만 뽑기 (정렬 재가공은 파이썬에서)
        qs = (
            Friend.objects.filter(user=request.user)
            .select_related("friend_user", "friend_user__location")
            .order_by("-created_at")[:MAX_TOTAL]
        )
        friends = list(qs)

        # 2) Redis로 온라인 여부 한 번에 조회
        r = get_redis()
        friend_user_ids = [f.friend_user_id for f in friends]
        keys = [presence_key(uid) for uid in friend_user_ids]

        online_map = {}
        if keys:
            vals = r.mget(keys)  # ["1", None, ...]
            for uid, v in zip(friend_user_ids, vals):
                online_map[uid] = v is not None

        # 3) 응답 item 만들기
        items = []
        for f in friends:
            u = f.friend_user
            age = None
            if u.birth_year:
                # 해커톤용: 만 나이 말고 대충 "출생년도 기반"
                age = 2026 - int(u.birth_year) + 1

            region = ""
            loc = getattr(u, "location", None)
            if loc and getattr(loc, "region", ""):
                region = loc.region

            items.append(
                {
                    "userId": u.id,
                    "name": u.name,
                    "age": age,
                    "region": region,
                    "profileImageUrl": u.profile_image_url,
                    "online": bool(online_map.get(u.id, False)),
                    "isWelfareWorker": bool(u.is_welfare_worker),
                    "createdAt": f.created_at.isoformat(),
                }
            )

        # 4) 정렬: 복지사 > 온라인 > 최신(createdAt desc)
        items.sort(
            key=lambda x: (
                0 if x["isWelfareWorker"] else 1,
                0 if x["online"] else 1,
                x["createdAt"],
            ),
            reverse=False,
        )
        # createdAt은 문자열이라 reverse 정렬이 애매하니,
        # 위 방식 쓰면 createdAt이 오름차순될 수 있음 -> 아래처럼 최신이 먼저 되게 처리
        # 가장 쉬운 방법: createdAt만 따로 reverse로 바꿔서 2차 처리
        # (해커톤이면 아래 한 줄로 끝내자)
        items.sort(key=lambda x: x["createdAt"], reverse=True)
        items.sort(key=lambda x: (not x["online"]), reverse=False)
        items.sort(key=lambda x: (not x["isWelfareWorker"]), reverse=False)

        # 5) 페이지네이션
        total = len(items)
        paged = items[offset : offset + limit]
        next_offset = offset + limit if (offset + limit) < total else None

        return ok(
            {
                "friends": paged,
                "offset": offset,
                "limit": limit,
                "nextOffset": next_offset,
                "total": total,
            }
        )


class FriendAddView(APIView):
    permission_classes = [IsAuthenticated]

    # POST /api/friends/add
    # body: { "targetUserId": 42 }
    def post(self, request):
        target_user_id = request.data.get("targetUserId")
        if not target_user_id:
            return fail("VALIDATION_ERROR", "targetUserId is required")

        if str(target_user_id) == str(request.user.id):
            return fail("INVALID_FRIEND", "cannot add yourself")

        target = User.objects.filter(id=target_user_id, is_active=True).first()
        if not target:
            return fail("USER_NOT_FOUND", "target user not found", 404)

        from app.friends.models import Friend

        obj, created = Friend.objects.get_or_create(
            user=request.user, friend_user=target
        )
        return ok({"added": bool(created)})
