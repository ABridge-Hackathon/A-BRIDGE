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
            return redirect("/admin/")  # 또는 로그인 페이지
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()

        rel_qs = CareRelation.objects.filter(
            welfare_worker=self.request.user
        ).select_related("senior")

        seniors = [r.senior for r in rel_qs]
        if q:
            seniors = [s for s in seniors if q in (s.name or "")]

        items = []
        for s in seniors:
            items.append(
                {
                    "userId": s.id,
                    "name": s.name,
                    "age": _calc_age(s),
                    "gender": s.gender,
                    "profileImageUrl": s.profile_image_url or "",
                    "statusText": "새로운 대화 분석 완료",  # 더미
                    "isNew": True,  # 더미
                    "recentText": "방금 전",  # 더미
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

        # 내 담당 어르신만
        ok_rel = CareRelation.objects.filter(
            welfare_worker=self.request.user, senior_id=senior_id
        ).exists()
        if not ok_rel:
            ctx["forbidden"] = True
            return ctx

        senior = User.objects.filter(id=senior_id, is_active=True).first()
        ctx["senior"] = senior
        ctx["seniorAge"] = _calc_age(senior)

        # 통화 기록: 최신순
        calls = (
            CallLog.objects.filter(senior_id=senior_id)
            .select_related("peer")
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
            CallLog.objects.select_related("senior", "peer")
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
        lines = list(call.transcript_lines.all())

        ctx["call"] = call
        ctx["analysis"] = analysis
        ctx["lines"] = lines
        return ctx
