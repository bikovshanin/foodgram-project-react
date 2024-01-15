from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Дополнение стандартной модели пользователя."""
    email = models.EmailField(
        _('email address'),
        unique=True
    )
    first_name = models.CharField(max_length=30, blank=False)
    last_name = models.CharField(max_length=30, blank=False)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
