# app/friends/views.py
from datetime import datetime
from django.utils import timezone

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

        obj, created = Friend.objects.get_or_create(
            user=request.user,
            friend_user=target,
        )

        return ok({"added": bool(created)})

class FriendListView(APIView):
    permission_classes = [IsAuthenticated]

    # GET /api/friends?offset=0&limit=6
    def get(self, request):
        # 0) pagination params
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

        # 1) DB에서 최신순으로 100명까지만 (친구 관계 생성일 기준 최신)
        qs = (
            Friend.objects.filter(user=request.user)
            .select_related("friend_user", "friend_user__location")
            .order_by("-created_at")[:MAX_TOTAL]
        )
        friends = list(qs)

        # 2) Redis 온라인 여부 한 번에 조회
        r = get_redis()
        friend_user_ids = [f.friend_user_id for f in friends]
        keys = [presence_key(uid) for uid in friend_user_ids]

        online_map = {}
        if keys:
            vals = r.mget(keys)  # [b"1" or "1" or None, ...]
            for uid, v in zip(friend_user_ids, vals):
                online_map[uid] = v is not None

        # 3) 응답 items 구성 (정렬을 위해 created_at datetime 유지)
        now_year = timezone.now().year

        items = []
        for f in friends:
            u = f.friend_user

            # 해커톤용 나이 계산(정책 확정 전): birth_date 있으면 year 기준, 없으면 birth_year
            age = None
            if getattr(u, "birth_date", None):
                age = now_year - u.birth_date.year
            elif getattr(u, "birth_year", None):
                age = now_year - int(u.birth_year)

            # region: location.region 우선, 없으면 address fallback
            region = ""
            loc = getattr(u, "location", None)
            if loc and getattr(loc, "region", ""):
                region = loc.region
            else:
                region = getattr(u, "address", "") or ""

            created_dt = f.created_at  # datetime

            items.append(
                {
                    "userId": u.id,
                    "name": u.name,
                    "age": age,
                    "region": region,
                    "online": bool(online_map.get(u.id, False)),
                    "isWelfareWorker": bool(u.is_welfare_worker),
                    "profileImageUrl": u.profile_image_url or "",
                    "_createdAt": created_dt,  # 정렬용 내부 필드
                }
            )

        # 4) 정렬: 복지사 먼저, 온라인 먼저, 최신 먼저
        # - welfare: True 먼저  -> not isWelfareWorker (False가 먼저)
        # - online: True 먼저   -> not online (False가 먼저)
        # - 최신: createdAt desc -> -timestamp
        items.sort(
            key=lambda x: (
                not x["isWelfareWorker"],
                not x["online"],
                -x["_createdAt"].timestamp(),
            )
        )

        # 5) 페이지네이션 + createdAt 변환
        total = len(items)
        paged = items[offset : offset + limit]
        next_offset = offset + limit if (offset + limit) < total else None

        # 응답에서는 createdAt만 내보내고 내부필드 제거
        for it in paged:
            it["createdAt"] = it["_createdAt"].isoformat()
            del it["_createdAt"]

        return ok(
            {
                "friends": paged,
                "offset": offset,
                "limit": limit,
                "nextOffset": next_offset,
                "total": total,
            }
        )
