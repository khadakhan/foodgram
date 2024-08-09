from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from users.const import MAX_EMAIL_LENGTH, MAX_LENGHT_CHAR


class FoodUser(AbstractUser):
    """Redefined user model."""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    email = models.EmailField(
        max_length=MAX_EMAIL_LENGTH,
        unique=True,
        verbose_name='email'
    )
    first_name = models.CharField(
        max_length=MAX_LENGHT_CHAR,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_LENGHT_CHAR,
        verbose_name='Фамиля'
    )
    avatar = models.ImageField(
        upload_to='users/',
        null=True,
        blank=True,
        verbose_name='Аватар',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email


class Subscription(models.Model):
    """Model for following."""

    user = models.ForeignKey(
        FoodUser, on_delete=models.CASCADE,
        related_name='user_subscriptions'
    )
    author = models.ForeignKey(
        FoodUser, on_delete=models.CASCADE,
        related_name='author_subscriptions'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_user_author'
            )
        ]

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Нельзя подписаться на себя')

    def __str__(self):
        return (f'{self.user.username} subscribed'
                f' on {self.author.username}')
