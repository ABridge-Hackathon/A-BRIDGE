# app/transcripts/models.py
# app/transcripts/models.py
from django.db import models


class Transcript(models.Model):
    # 문서(sessionId: "abc123")에 맞춰 문자열로
    session_id = models.CharField(max_length=64, db_index=True)
    text = models.TextField()
    safe = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
