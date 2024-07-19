from djoser.conf import settings
from django.contrib.auth import get_user_model
from djoser.views import TokenCreateView, UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from users.serializers import (
    UserAvatarSerializer,
    UserListRetrieveSerializer,
)
from users.pagination import UsersPagination

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Redefinition UserViewSet."""
    pagination_class = UsersPagination

    def get_queryset(self):
        user = self.request.user
        if settings.HIDE_USERS and self.action == "list" and not user.is_staff:
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
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'retrieve':
            self.permission_classes = settings.PERMISSIONS.user_create
        return super().get_permissions()


class CustomTokenCreateView(TokenCreateView):
    """Redefinition TokenCreateView because of status_code."""
    def _action(self, serializer):
        custom_response = super()._action(serializer)
        custom_response.status_code = status.HTTP_201_CREATED
        return custom_response
