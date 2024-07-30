import pandas as pd
import short_url
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.conf import settings
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.pagination import UsersPagination
from api.permissions import (
    AllowAny,
    IsAuthor,
    IsAuthenticated,
)
from api.serializers import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeCreateSerializer,
    ShortLinkSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserAvatarSerializer,
    UserListRetrieveSerializer,
)

from backend.settings import DOMAIN
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredientsAmount,
    RecipeTag,
    ShopList,
    Tag
)
from users.models import Subscription

# ==========================Users==============================================

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
        if self.action == 'subscriptions':
            return SubscriptionSerializer
        if self.action == 'create_subscription':
            return SubscriptionSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'list':
            return (AllowAny(),)
        if self.action == 'retrieve':
            self.permission_classes = settings.PERMISSIONS.token_create
        if self.action == 'subscriptions':
            self.permission_classes = settings.PERMISSIONS.token_destroy
        if self.action == 'create_subscription':
            self.permission_classes = settings.PERMISSIONS.token_destroy
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

# =============================Recipes=======================================


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if name is not None:
            queryset = queryset.filter(name__iregex=rf'^{name}.*$')
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    pagination_class = UsersPagination
    serializer_class = RecipeSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.all()
        author_id = self.request.query_params.get('author')
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )
        tag_slugs = self.request.query_params.getlist('tags')
        if author_id is not None and author_id.isdigit():
            queryset = queryset.filter(author=author_id)
        if tag_slugs:
            tags = Tag.objects.filter(slug__in=tag_slugs).all()
            tag_recipe_queryset_id = RecipeTag.objects.filter(
                tag__in=tags
            ).values_list(
                'recipe',
                flat=True
            )
            queryset = queryset.filter(id__in=tag_recipe_queryset_id)
        if user.is_authenticated:
            in_favorite = user.recipes_in_favorites.all().values_list(
                'recipe',
                flat=True
            )
            in_shopping_cart = user.what_by_user.all().values_list(
                'recipe',
                flat=True
            )
            if is_favorited == '1':
                queryset = queryset.filter(id__in=in_favorite)
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(id__in=in_shopping_cart)
        return queryset

    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'partial_update':
            return RecipeCreateSerializer
        if self.action == 'get_short_link':
            return ShortLinkSerializer
        if self.action == 'add_delete_favorite':
            return FavoriteSerializer
        if self.action == 'add_delete_shopping_cart':
            return FavoriteSerializer
        return RecipeSerializer

    @action(
        methods=['get'],
        detail=False,
        url_path=r'(?P<id>\d+)/get-link'
    )
    def get_short_link(self, request, id):
        recipe = get_object_or_404(Recipe, pk=id)
        short_link = 'https://{domain}/{link_id}'.format(
            domain=DOMAIN,
            link_id=short_url.encode_url(int(id), min_length=10)
        )
        recipe.short_link = short_link
        recipe.save()
        serializer = self.get_serializer(recipe)
        return Response(serializer.data)

    def get_permissions(self):
        if self.action == 'destroy':
            return (IsAuthor(),)
        if self.action == 'partial_update':
            return (IsAuthor(),)
        if self.action == 'download_shopping_cart':
            return (IsAuthenticated(),)
        return super().get_permissions()

    @action(
        methods=['post', 'delete'],
        detail=False,
        url_path=r'(?P<id>\d+)/favorite'
    )
    def add_delete_favorite(self, request, id):
        recipe = get_object_or_404(Recipe, pk=id)
        user = request.user
        if request.method == 'POST':
            curr_recipe, get_status = Favorite.objects.get_or_create(
                recipe=recipe,
                user=user,
            )
            if get_status is False:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            serializer = self.get_serializer(recipe)
            return Response(serializer.data, status.HTTP_201_CREATED)
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            Favorite.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=['post', 'delete'],
        detail=False,
        url_path=r'(?P<id>\d+)/shopping_cart'
    )
    def add_delete_shopping_cart(self, request, id):
        recipe = get_object_or_404(Recipe, pk=id)
        user = request.user
        if request.method == 'POST':
            curr_recipe, get_status = ShopList.objects.get_or_create(
                recipe=recipe,
                user=user,
            )
            if get_status is False:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            serializer = self.get_serializer(recipe)
            return Response(serializer.data, status.HTTP_201_CREATED)
        if ShopList.objects.filter(user=user, recipe=recipe).exists():
            ShopList.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=['get'],
        detail=False,
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        user = request.user
        user_recipes_in_shopping_cart = list(
            user.what_by_user.all().values_list(
                'recipe',
                flat=True
            )
        )
        recipe_ingredient_amount = []
        for recipe_id in user_recipes_in_shopping_cart:
            recipe_ingredient_amount += list(
                RecipeIngredientsAmount.objects.filter(
                    recipe=recipe_id
                )
            )
        shop_list = []
        for item in recipe_ingredient_amount:
            shop_list.append(
                [
                    item.ingredient.name,
                    item.amount,
                    item.ingredient.measurement_unit
                ]
            )
        df = pd.DataFrame(shop_list, columns=['ingredient', 'amount', 'unit'])
        df_grouped = df.groupby(['ingredient', 'unit']).amount.sum()
        df_grouped.to_csv('recipes/shop_list/shop_list.csv')
        with open('recipes/shop_list/shop_list.csv', 'rb') as f:
            data = f.read()
        response = HttpResponse(
            data,
            content_type='text',
            headers={
                "Content-Disposition": 'attachment; filename="shop_list.txt"'
            },
        )
        return response
