# app/care/models.py
from django.db import models
from app.users.models import User


class CareRelation(models.Model):
    welfare_worker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="care_seniors"
    )
    senior = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="care_workers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("welfare_worker", "senior")
