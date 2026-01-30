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
            return redirect("/admin/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()

        # 내가 담당하는 어르신
        seniors = User.objects.filter(
            care_workers__welfare_worker=self.request.user,
            is_active=True,
        ).distinct()

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
                status_text = analysis.summary if analysis else "분석 없음"
                recent_text = last_call.ended_at.strftime("%Y.%m.%d %H:%M")
                is_new = True  # 필요하면 조건 추가 가능

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
            summary = analysis.summary if analysis else "특이사항 없음"
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
        transcript = Transcript.objects.filter(session_id=call.session_id).first()
        lines = []
        if transcript:
            for i, line in enumerate(transcript.text.split("\n")):
                lines.append(
                    {
                        "speaker": line.split(":")[0],
                        "text": ":".join(line.split(":")[1:]),
                        "ts": call.started_at + timezone.timedelta(seconds=i * 10),
                    }
                )
        ctx["lines"] = lines

        ctx["call"] = call
        ctx["analysis"] = analysis
        ctx["lines"] = lines
        return ctx
