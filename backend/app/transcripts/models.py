# app/transcripts/models.py
from django.db import models


class Transcript(models.Model):
    session_id = models.UUIDField(db_index=True)
    text = models.TextField()
    safe = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
