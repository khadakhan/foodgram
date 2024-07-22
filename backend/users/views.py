from djoser.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.views import TokenCreateView, UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from users.models import Subscription
from users.pagination import UsersPagination
from users.serializers import (
    SubscriptionSerializer,
    UserAvatarSerializer,
    UserListRetrieveSerializer,
)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Redefinition UserViewSet."""
    pagination_class = UsersPagination

    def get_queryset(self):
        user = self.request.user
        if settings.HIDE_USERS and self.action == 'list' and not user.is_staff:
            return super().queryset
        return super().get_queryset()

    @action(
        methods=['put', 'delete'],
        detail=False,
        url_path='me/avatar'
    )
    def me_avatar(self, request):
        if request.method == 'DELETE':
            user = request.user
            user.avatar = ''
            user.save()
            return Response(
                data=None,
                status=status.HTTP_204_NO_CONTENT
            )
        self.get_object = self.get_instance
        return self.update(request)

    def get_serializer_class(self):
        if self.action == 'me_avatar':
            return UserAvatarSerializer
        if (self.action == 'list' or self.action == 'retrieve'
           or self.action == 'me'):
            return UserListRetrieveSerializer
        if self.action == 'subscriptions':                                   #
            return SubscriptionSerializer                                    #
        if self.action == 'create_subscription':                             #
            return SubscriptionSerializer                                    #
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'retrieve':
            self.permission_classes = settings.PERMISSIONS.token_create
        if self.action == 'subscriptions':                                   #
            self.permission_classes = settings.PERMISSIONS.token_destroy     #
        if self.action == 'create_subscription':                             #
            self.permission_classes = settings.PERMISSIONS.token_destroy     #
        return super().get_permissions()

# ------------------------------список-подписок-------------------------
    @action(
        methods=['get'],
        detail=False,
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        user = request.user
        user_subscriptions_id = user.subscriptions.all().values_list(
            'subscription',
            flat=True
        )
        queryset = User.objects.filter(id__in=user_subscriptions_id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
# ---------------------создание подписки--------------------------------

    @action(
        methods=['post', 'delete'],
        detail=False,
        url_path=r'(?P<id>\d+)/subscribe'
    )
    def create_subscription(self, request, id):
        subscription = get_object_or_404(User, pk=id)
        user = request.user
        user_subscriptions = user.subscriptions.all()
        user_subscriptions_id = user.subscriptions.values_list(
            'subscription',
            flat=True
        )
        if (
            request.method == 'DELETE'
            and (subscription.id in user_subscriptions_id)
        ):
            user_subscriptions.filter(subscription=id).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif (
            request.method == 'DELETE'
            and (subscription.id not in user_subscriptions_id)
        ):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(subscription)
        # если пытается подписаться на себя или подписка уже есть
        if user.id == int(id) or int(id) in user_subscriptions_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        # создаем подписку
        Subscription.objects.create(user=user, subscription=subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
# ----------------------------------------------------------------------


class CustomTokenCreateView(TokenCreateView):
    """Redefinition TokenCreateView because of status_code."""
    def _action(self, serializer):
        custom_response = super()._action(serializer)
        custom_response.status_code = status.HTTP_201_CREATED
        return custom_response
