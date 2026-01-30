# app/users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("phone_number must be set")

        phone_number = str(phone_number).strip()
        user = self.model(phone_number=phone_number, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone_number, password=password, **extra_fields)


class User(AbstractUser):
    # username 기반 로그인 제거 (phone_number로 로그인)
    username = None

    phone_number = models.CharField(max_length=20, unique=True)

    # 서비스 필드
    name = models.CharField(max_length=50)
    gender = models.CharField(max_length=1)  # "M" / "F"
    birth_year = models.IntegerField()
    address = models.CharField(max_length=255)
    profile_image_url = models.TextField(blank=True, default="")
    is_welfare_worker = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []  # createsuperuser에서 추가로 요구할 필드(해커톤이면 비워도 OK)

    objects = UserManager()

    def __str__(self):
        return f"{self.id} {self.phone_number}"
