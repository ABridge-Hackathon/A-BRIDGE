# app/adminpanel/views.py
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from app.users.models import User
from app.care.models import CareRelation
from app.calls.models import CallLog
from django.utils.timesince import timesince
from app.transcripts.models import Transcript
from app.friends.models import Friend


def _recent_text(dt):
    if not dt:
        return "-"
    # "0분 전"이면 "방금 전"으로
    diff = timesince(dt, timezone.now()).split(",")[0]
    if diff.startswith("0"):
        return "방금 전"
    return f"{diff} 전"


def _dashboard_status_text(status: str) -> str:
    return {
        "DANGER": "새로운대화 분석 완료",
        "WARNING": "특이사항 분석 완료",
        "SAFE": "특이사항 없음",
    }.get(status, "특이사항 없음")


def _require_welfare_worker(user: User) -> bool:
    return bool(user and user.is_authenticated and user.is_welfare_worker)


def _calc_age(user: User):
    now_year = timezone.now().year
    if user.birth_date:
        return now_year - user.birth_date.year
    if user.birth_year:
        return now_year - int(user.birth_year)
    return None


class DashboardView(TemplateView):
    template_name = "adminpanel/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not _require_welfare_worker(request.user):
            return redirect("/admin/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()

        seniors = User.objects.all().order_by("id")

        if q:
            seniors = seniors.filter(name__icontains=q)

        items = []
        for s in seniors:
            last_call = (
                CallLog.objects.filter(senior=s)
                .select_related("analysis")
                .order_by("-ended_at")
                .first()
            )

            status = "SAFE"
            status_text = "통화 기록 없음"
            recent_text = "-"
            is_new = False

            if last_call:
                analysis = getattr(last_call, "analysis", None)
                status = analysis.status if analysis else "SAFE"

                # ✅ (3)처럼 문구 고정
                status_text = _dashboard_status_text(status)

                # ✅ (3)처럼 "방금 전/1시간 전"
                recent_text = _recent_text(last_call.ended_at)

                # ✅ New 뱃지: 예) 최근 24시간 이내면 New
                if last_call.ended_at:
                    is_new = (
                        timezone.now() - last_call.ended_at
                    ).total_seconds() <= 60 * 60 * 24

            items.append(
                {
                    "userId": s.id,
                    "name": s.name,
                    "age": _calc_age(s),
                    "gender": s.gender,
                    "profileImageUrl": s.profile_image_url or "",
                    "status": status,
                    "statusText": status_text,
                    "recentText": recent_text,
                    "isNew": is_new,
                }
            )

        ctx["me"] = self.request.user
        ctx["total"] = len(items)
        ctx["items"] = items
        ctx["q"] = q
        return ctx


class SeniorDetailView(TemplateView):
    template_name = "adminpanel/senior_detail.html"

    def dispatch(self, request, *args, **kwargs):
        if not _require_welfare_worker(request.user):
            return redirect("/admin/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        senior_id = kwargs["senior_id"]

        ok_rel = CareRelation.objects.filter(
            welfare_worker=self.request.user, senior_id=senior_id
        ).exists()
        if not ok_rel:
            ctx["forbidden"] = True
            return ctx

        senior = User.objects.filter(id=senior_id, is_active=True).first()
        ctx["senior"] = senior
        ctx["seniorAge"] = _calc_age(senior)

        calls = (
            CallLog.objects.filter(senior_id=senior_id)
            .select_related("peer", "analysis")
            .order_by("-ended_at", "-started_at")[:50]
        )

        rows = []
        for c in calls:
            analysis = getattr(c, "analysis", None)
            status = analysis.status if analysis else "SAFE"
            rows.append(
                {
                    "callId": c.call_id,
                    "peerName": c.peer.name,
                    "peerId": c.peer.id,
                    "peerAge": _calc_age(c.peer),
                    "peerGender": c.peer.gender,
                    "endedAt": c.ended_at,
                    "status": status,
                    "summary": (analysis.summary if analysis else "특이사항 없음"),
                }
            )
        ctx["calls"] = rows

        # ✅ 친구 목록 추가 (여기서만 실행되어야 함!)
        friends_qs = (
            Friend.objects.filter(user_id=senior_id)
            .select_related("friend_user")
            .order_by("-created_at")[:50]
        )
        ctx["friends"] = [
            {
                "id": f.id,
                "friendId": f.friend_user.id,
                "friendName": f.friend_user.name,
                "friendProfileImageUrl": f.friend_user.profile_image_url or "",
                "createdAt": f.created_at,
            }
            for f in friends_qs
        ]

        return ctx


class CallDetailView(TemplateView):
    template_name = "adminpanel/call_detail.html"

    def dispatch(self, request, *args, **kwargs):
        if not _require_welfare_worker(request.user):
            return redirect("/admin/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        call_id = kwargs["call_id"]

        call = (
            CallLog.objects.select_related("senior", "peer", "analysis")
            .filter(call_id=call_id)
            .first()
        )
        if not call:
            ctx["not_found"] = True
            return ctx

        # 담당 복지사의 어르신인지 체크
        ok_rel = CareRelation.objects.filter(
            welfare_worker=self.request.user, senior=call.senior
        ).exists()
        if not ok_rel:
            ctx["forbidden"] = True
            return ctx

        analysis = getattr(call, "analysis", None)
        transcript = Transcript.objects.filter(session_id=call.session_id).first()
        lines = []
        transcript = Transcript.objects.filter(session_id=call.session_id).first()

        if transcript and transcript.text:
            for i, raw in enumerate(transcript.text.split("\n")):
                raw = raw.strip()
                if not raw:
                    continue

                # "김철수: 어보세요" 형태 아니면 스킵/보정
                if ":" in raw:
                    speaker, text = raw.split(":", 1)
                else:
                    speaker, text = "알 수 없음", raw

                ts = call.started_at + timezone.timedelta(seconds=i * 10)
                lines.append(
                    {
                        "speaker": speaker.strip(),
                        "text": text.strip(),
                        "ts": ts.strftime("%H:%M"),  #  화면에 18:30 처럼
                    }
                )
        ctx["lines"] = lines

        ctx["call"] = call
        ctx["analysis"] = analysis
        ctx["lines"] = lines
        return ctx


friends = (
    Friend.objects.filter(user_id=senior_id)
    .select_related("friend_user")
    .order_by("-created_at")[:50]
)

ctx["friends"] = [
    {
        "id": f.id,
        "friendId": f.friend_user.id,
        "friendName": f.friend_user.name,
        "friendProfileImageUrl": f.friend_user.profile_image_url,
        "createdAt": f.created_at,
    }
    for f in friends
]
