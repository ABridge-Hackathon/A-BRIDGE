# app/matches/services.py
from django.db import transaction
from django.db.models.functions import Random

from app.matches.models import MatchSession


def create_waiting_session(user) -> MatchSession:
    return MatchSession.objects.create(user_a=user, status="WAITING")


@transaction.atomic
def request_match(user) -> MatchSession:
    """
    랜덤 매칭 정책:
    - 내가 이미 WAITING이면 그대로 반환
    - 후보: WAITING 세션 중 user_a != 나
    - 후보가 있으면 랜덤 1개 pick -> user_b=나, status=MATCHED
    - 후보 없으면 내가 WAITING 세션 생성
    """
    existing = (
        MatchSession.objects.select_for_update(skip_locked=True)
        .filter(user_a=user, status="WAITING")
        .order_by("-started_at")
        .first()
    )
    if existing:
        return existing

    candidate = (
        MatchSession.objects.select_for_update(skip_locked=True)
        .filter(status="WAITING")
        .exclude(user_a=user)
        .order_by(Random())
        .first()
    )

    if not candidate:
        return create_waiting_session(user)

    candidate.user_b = user
    candidate.status = "MATCHED"
    candidate.save(update_fields=["user_b", "status"])
    return candidate
