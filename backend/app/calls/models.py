# app/calls/models.py
import uuid
from django.db import models
from app.users.models import User


class CallLog(models.Model):
    call_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # 통화 참여자(어르신/상대방)
    senior = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="call_as_senior"
    )
    peer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="call_as_peer"
    )

    # 매칭 세션 연결(있으면)
    session_id = models.UUIDField(null=True, blank=True, db_index=True)


class CallAnalysis(models.Model):
    STATUS_CHOICES = (
        ("SAFE", "SAFE"),
        ("WARNING", "WARNING"),
        ("DANGER", "DANGER"),
    )
    call = models.OneToOneField(
        CallLog, on_delete=models.CASCADE, related_name="analysis"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="SAFE")
    category = models.CharField(
        max_length=50, blank=True, default=""
    )  # 예: "피싱의심/악성욕설"
    keywords = models.JSONField(default=list, blank=True)  # ["송금","사움"]
    summary = models.TextField(blank=True, default="")  # "금융 사기 키워드 감지"


class CallTranscriptLine(models.Model):
    call = models.ForeignKey(
        CallLog, on_delete=models.CASCADE, related_name="transcript_lines"
    )
    ts = models.CharField(max_length=5)  # "18:30" 처럼 단순 문자열로 시작(더미용)
    speaker = models.CharField(max_length=30)  # "김철수" / "김상대"
    text = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]
