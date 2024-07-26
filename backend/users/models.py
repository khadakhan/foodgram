from django.contrib.auth.models import AbstractUser
from django.db import models

MAX_EMAIL_LENGTH = 254


class CustomUser(AbstractUser):
    """Redefined user model."""
    email = models.EmailField(
        max_length=MAX_EMAIL_LENGTH,
        unique=True,
        verbose_name='email'
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамиля'
    )
    avatar = models.ImageField(
        upload_to='users/',
        null=True,
        blank=True,
        verbose_name='Аватар',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email


class Subscription(models.Model):
    """Model for following."""
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='subscriptions')
    subscription = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='subscribers')

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'subscription'],
                name='unique_user_subscription'
            )
        ]

    def __str__(self):
        return self.user.username
