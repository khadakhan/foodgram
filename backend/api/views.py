from django.http import FileResponse
from django.db.models import Exists, OuterRef, Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.filters import RecipeFilter
from api.pagination import UsersRecipesPagination
from api.permissions import (
    RecipePermission,
)
from api.serializers import (
    FavoriteCreateSerializer,
    ShopCreateSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeCreateSerializer,
    ShortLinkSerializer,
    SubscriptionSerializer,
    SubscriptionCreateSerializer,
    TagSerializer,
    UserAvatarSerializer,
)

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredientsAmount,
    Shop,
    Tag,
    User
)
from users.models import Subscription

# ==========================Users==============================================


class FoodUserViewSet(UserViewSet):
    """Redefinition UserViewSet."""

    pagination_class = UsersRecipesPagination

    @action(
        methods=('put',),
        detail=False,
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,)
    )
    def me_avatar(self, request):
        serializer = UserAvatarSerializer(
            instance=request.user,
            context={'request': request},
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    @me_avatar.mapping.delete
    def delete_me_avatar(self, request):
        user = request.user
        user.avatar.delete(save=True)
        return Response(
            data=None,
            status=status.HTTP_204_NO_CONTENT
        )

    def get_permissions(self):
        if self.action == 'me':
            return (IsAuthenticated(),)
        return super().get_permissions()

    @action(
        methods=('get',),
        detail=False,
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(
            author_subscriptions__user=user
        )
        page = self.paginate_queryset(queryset)
        if page:
            context = {'request': self.request}
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context=context
            )
            return self.get_paginated_response(serializer.data)
        return Response(status=status.HTTP_200_OK)

    @action(
        methods=('post',),
        detail=False,
        url_path=r'(?P<id>\d+)/subscribe',
        permission_classes=(IsAuthenticated,)
    )
    def create_subscription(self, request, id):
        author = get_object_or_404(User, pk=id)
        user = request.user
        serializer = SubscriptionCreateSerializer(
            data={'user': user.id, 'author': author.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @create_subscription.mapping.delete
    def delete_subscription(self, request, id):
        author = get_object_or_404(User, pk=id)
        user = request.user
        delete_status, delete_dict = Subscription.objects.filter(
            user=user, author=author
        ).delete()
        if delete_status:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

# =============================Recipes=======================================


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    pagination_class = UsersRecipesPagination
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (RecipePermission,)

    def get_queryset(self):
        queryset = Recipe.objects.select_related(
            'author'
        ).prefetch_related(
            'tags',
            'ingredients'
        )
        user = self.request.user
        if user.is_authenticated:
            is_favorited = user.favorite_set.filter(
                recipe=OuterRef('pk')
            )
            is_in_shopping_cart = user.shop_set.filter(
                recipe=OuterRef('pk')
            )
            return queryset.annotate(
                is_favorited=Exists(is_favorited),
                is_in_shopping_cart=Exists(is_in_shopping_cart)
            )
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeCreateSerializer
        return RecipeSerializer

# -----------get short_link-------------------------------------

    @action(
        methods=('get',),
        detail=False,
        url_path=r'(?P<id>\d+)/get-link'
    )
    def get_short_link(self, request, id):
        recipe = get_object_or_404(Recipe, pk=id)
        serializer = ShortLinkSerializer(recipe)
        return Response(serializer.data)

# ---------------------------------------------

    @staticmethod
    def create_favorite_shop(serializer, pk, request):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        serializer = serializer(
            data={'user': user.id, 'recipe': recipe.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer

    @staticmethod
    def shop_list(shop_ingredients):
        shop_list_text = 'название, ед.изм., кол-во'
        for item in shop_ingredients:
            shop_list_text += (f'\n{item["ingredient__name"]}'
                               f', {item["ingredient__measurement_unit"]}'
                               f', {item["amount"]}')
        return shop_list_text

# ------------favorite_add_delete-----------------------------------------

    @action(
        methods=('post',),
        detail=False,
        url_path=r'(?P<id>\d+)/favorite'
    )
    def add_favorite(self, request, id):
        return Response(
            self.create_favorite_shop(
                serializer=FavoriteCreateSerializer,
                pk=id,
                request=request
            ).data,
            status=status.HTTP_201_CREATED
        )

    @add_favorite.mapping.delete
    def delete_favorite(self, request, id):
        delete_status, delete_dict = Favorite.objects.filter(
            user=request.user,
            recipe=get_object_or_404(Recipe, pk=id)
        ).delete()
        if delete_status:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

# --------------shop_cart_add_delete----------------------

    @action(
        methods=('post',),
        detail=False,
        url_path=r'(?P<id>\d+)/shopping_cart'
    )
    def add_shop(self, request, id):
        return Response(
            self.create_favorite_shop(
                serializer=ShopCreateSerializer,
                pk=id,
                request=request
            ).data,
            status=status.HTTP_201_CREATED
        )

    @add_shop.mapping.delete
    def delete_shop(self, request, id):
        delete_status, delete_dict = Shop.objects.filter(
            user=request.user,
            recipe=get_object_or_404(Recipe, pk=id)
        ).delete()
        if delete_status:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

# --------------------download shop list-------------------------------

    @action(
        methods=('get',),
        detail=False,
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        user = request.user
        shop_ingredients = RecipeIngredientsAmount.objects.filter(
            recipe__shop_set__user=user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit',
        ).annotate(
            amount=Sum('amount')
        ).order_by('ingredient__name')
        return FileResponse(
            self.shop_list(shop_ingredients),
            content_type='text'
        )
