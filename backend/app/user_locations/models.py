# app/user_locations/models.py
from django.db import models
from app.users.models import User


class UserLocation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="location")
    latitude = models.FloatField()
    longitude = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} ({self.latitude}, {self.longitude})"
