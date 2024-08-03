import os

import pandas as pd
import short_url
from django.http import HttpResponse
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from api.filters import RecipeFilter
from api.pagination import UsersRecipesPagination
from api.permissions import (
    IsAuthor,
)
from api.serializers import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeCreateSerializer,
    ShortLinkSerializer,
    SubscriptionSerializer,
    SubscriptionCreateSerializer,
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
    ShopList,
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
        url_path='me/avatar'
    )
    def me_avatar(self, request):
        serializer = UserAvatarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = dict(serializer.validated_data)
        user = request.user
        user.avatar = validated_data['avatar']
        user.save()
        instance_serializer = UserAvatarSerializer(user)
        return Response(
            instance_serializer.data,
            status=status.HTTP_200_OK
        )

    @me_avatar.mapping.delete
    def delete_me_avatar(self, request):
        user = request.user
        os.remove(user.avatar.path)
        user.avatar = ''
        user.save()
        return Response(
            data=None,
            status=status.HTTP_204_NO_CONTENT
        )

    def get_serializer_class(self):
        # а вот без этого не получается подсунуть сериалайзер
        if (self.action == 'list' or self.action == 'retrieve'
           or self.action == 'me'):
            return UserListRetrieveSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'me':
            return (IsAuthenticated(),)
        # нужно для анонимных юзеров
        if self.action == 'list' or self.action == 'retrieve':
            return (AllowAny(),)
        return super().get_permissions()
# ------------------------------список-подписок-------------------------

    @action(
        methods=('get',),
        detail=False,
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        user = request.user
        user_subscriptions_id = user.subscriptions.all().values_list(
            'subscription',
            flat=True
        )
        queryset = User.objects.filter(id__in=user_subscriptions_id).annotate(
            recipes_count=Count(
                'recipes'
            )
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            context = {'request': self.request}
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context=context
            )
            return self.get_paginated_response(serializer.data)

        return Response(
            SubscriptionSerializer(
                queryset, many=True, context={'request': self.request}
            )
        )
# ---------------------создание подписки--------------------------------

    @action(
        methods=('post',),
        detail=False,
        url_path=r'(?P<id>\d+)/subscribe'
    )
    def create_subscription(self, request, id):
        subscription = get_object_or_404(User, pk=id)
        user = request.user
        serializer = SubscriptionCreateSerializer(
            data={'id': id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        Subscription.objects.create(user=user, subscription=subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @create_subscription.mapping.delete
    def delete_subscription(self, request, id):
        if not User.objects.filter(pk=id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        user = request.user
        user_subscriptions = user.subscriptions
        user_subscriptions_id = user_subscriptions.values_list(
            'subscription',
            flat=True
        )
        if int(id) not in user_subscriptions_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        user_subscriptions.filter(subscription=id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# =============================Recipes=======================================


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    # queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    # filter_backends = [filters.SearchFilter]
    # search_fields = ['^name']

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if name is not None:
            queryset = queryset.filter(name__iregex=rf'^{name}.*$')
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = UsersRecipesPagination
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            is_favorited = user.recipes_in_favorites.filter(
                recipe=OuterRef('pk')
            )
            is_in_shopping_cart = user.what_by_user.filter(
                recipe=OuterRef('pk')
            )
            return Recipe.objects.annotate(
                is_favorited=Exists(is_favorited),
                is_in_shopping_cart=Exists(is_in_shopping_cart)
            )
        return super().get_queryset()

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
        methods=('get',),
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
        return super().get_permissions()

    @action(
        methods=('post', 'delete'),
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
        methods=('post', 'delete'),
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
        methods=('get',),
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
