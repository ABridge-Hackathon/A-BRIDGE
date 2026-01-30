# app/matches/models.py
import uuid
from django.db import models


class MatchSession(models.Model):
    STATUS_CHOICES = (
        ("WAITING", "WAITING"),
        ("MATCHED", "MATCHED"),
        ("CALLING", "CALLING"),
        ("ENDED", "ENDED"),
        ("CANCELED", "CANCELED"),
    )

    session_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)

    user_a = models.ForeignKey(
        "users.User", related_name="match_a", on_delete=models.CASCADE
    )
    user_b = models.ForeignKey(
        "users.User",
        related_name="match_b",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="WAITING")
