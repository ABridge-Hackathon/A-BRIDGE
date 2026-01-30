# app/matches/services.py
import math
from django.db import transaction
from django.utils import timezone

from app.matches.models import MatchSession
from app.user_locations.models import UserLocation

import json
from app.common.redis_client import get_redis

SESSION_TTL_SEC = 60 * 30  # 30분

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@transaction.atomic
def request_match(user, *, candidate_limit: int = 200):
    """
    return:
      {
        "session": MatchSession,
        "matched": bool,
        "peer_user_id": int|None,
        "distance_km": float|None,
      }
    """

    # 1) 내 WAITING 세션 생성 (큐 등록)
    my_session = MatchSession.objects.create(
        user_a=user,
        status="WAITING",
    )

    # 2) 내 위치 가져오기 (없으면 매칭 시도 안 하고 대기만)
    my_loc = UserLocation.objects.filter(user=user).first()
    if not my_loc:
        return {
            "session": my_session,
            "matched": False,
            "peer_user_id": None,
            "distance_km": None,
        }

    # 3) 후보 WAITING 세션들 (나 제외)
    #    - select_for_update로 잠가서 "동시에 같은 사람 잡는 문제" 줄임
    candidates = (
        MatchSession.objects.select_for_update(skip_locked=True)
        .filter(status="WAITING", user_b__isnull=True)
        .exclude(user_a=user)
        .order_by("-started_at")[:candidate_limit]
    )

    if not candidates:
        return {
            "session": my_session,
            "matched": False,
            "peer_user_id": None,
            "distance_km": None,
        }

    # 4) 후보들의 위치를 한번에 로드
    candidate_user_ids = [c.user_a_id for c in candidates]
    loc_map = {
        loc.user_id: loc
        for loc in UserLocation.objects.filter(user_id__in=candidate_user_ids)
    }

    # 5) 거리 계산해서 가장 가까운 후보 선택
    best = None  # (distance, candidate_session)
    for c in candidates:
        loc = loc_map.get(c.user_a_id)
        if not loc:
            continue
        d = haversine_km(my_loc.latitude, my_loc.longitude, loc.latitude, loc.longitude)
        if (best is None) or (d < best[0]):
            best = (d, c)

    if best is None:
        # 후보들은 있는데 위치가 하나도 없으면 매칭 불가 → WAITING 유지
        return {
            "session": my_session,
            "matched": False,
            "peer_user_id": None,
            "distance_km": None,
        }

    distance_km, peer_session = best

    # 6) "peer_session"에 user_b로 나를 붙여서 하나의 session으로 매칭 완료
    peer_session.user_b = user
    peer_session.status = "MATCHED"
    peer_session.save(update_fields=["user_b", "status"])

    # 내 세션은 필요 없어졌으니 CANCEL 처리(혹은 삭제)
    my_session.status = "CANCELED"
    my_session.ended_at = timezone.now()
    my_session.save(update_fields=["status", "ended_at"])

    return {
        "session": peer_session,
        "matched": True,
        "peer_user_id": peer_session.user_a_id,  # 상대는 peer_session.user_a
        "distance_km": float(distance_km),
    }


def save_session_state(session, *, status: str):
    r = get_redis()
    payload = {
        "sessionId": str(session.session_id),
        "status": status,
        "userAId": session.user_a_id,
        "userBId": session.user_b_id,
        "updatedAt": timezone.now().isoformat(),
    }
    r.set(
        _session_key(str(session.session_id)), json.dumps(payload), ex=SESSION_TTL_SEC
    )
    return payload


def load_session_state(session_id: str):
    r = get_redis()
    raw = r.get(_session_key(session_id))
    if not raw:
        return None
    return json.loads(raw)


def delete_session_state(session_id: str):
    r = get_redis()
    r.delete(_session_key(session_id))
