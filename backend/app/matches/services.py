# app/matches/services.py
import math
from django.db import transaction
from app.matches.models import MatchSession
from app.user_locations.models import UserLocation

# 위치 없으면 뒤로 보내는 값
FAR_DISTANCE = 9999.0


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    # 지구 반지름(km)
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def create_waiting_session(user) -> MatchSession:
    return MatchSession.objects.create(user_a=user, status="WAITING")


@transaction.atomic
def request_match(user) -> MatchSession:
    """
    간단 매칭 정책(문서/요구 반영):
    - 1순위: 현재 위치 기반(있으면 거리 최소)
    - 2순위 주소 기반: ❌ 안 함 (요구사항)
    - 후보: WAITING 세션 중에서 user_a != 나
    - 매칭 성공: candidate.user_b = 나, status = MATCHED
    - 실패: 내가 WAITING 세션 생성
    """
    existing = (
        MatchSession.objects.filter(user_a=user, status="WAITING")
        .order_by("-started_at")
        .first()
    )
    if existing:
        return existing
    my_loc = UserLocation.objects.filter(user=user).first()

    # 후보 20개 정도만 잡아서 거리 계산 (해커톤)
    candidates = (
        MatchSession.objects.select_for_update(skip_locked=True)
        .filter(status="WAITING")
        .exclude(user_a=user)
        .order_by("started_at")[:20]
    )

    best_session = None
    best_dist = None

    for c in candidates:
        peer_loc = UserLocation.objects.filter(user=c.user_a).first()

        if my_loc and peer_loc:
            d = haversine_km(
                my_loc.latitude, my_loc.longitude, peer_loc.latitude, peer_loc.longitude
            )
        else:
            d = FAR_DISTANCE

        if best_dist is None or d < best_dist:
            best_dist = d
            best_session = c

    if not best_session:
        return create_waiting_session(user)

    # 매칭 확정
    best_session.user_b = user
    best_session.status = "MATCHED"
    best_session.save(update_fields=["user_b", "status"])
    return best_session
