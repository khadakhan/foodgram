from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import pandas as pd
import short_url
from recipes.models import (Favorite,
                            Ingredient,
                            Recipe,
                            RecipeIngredientsAmount,
                            RecipeTag,
                            ShopList,
                            Tag)
from recipes.permissions import IsAuthor, IsAuthenticated
from recipes.serializers import (FavoriteSerializer,
                                 IngredientSerializer,
                                 RecipeSerializer,
                                 RecipeCreateSerializer,
                                 RecipeUpdateSerializer,
                                 ShortLinkSerializer,
                                 TagSerializer)
from users.pagination import UsersPagination

DOMAIN = 'foodgramdo.zapto.org'


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
        queryset = Recipe.objects.all()
        recipes_is_in_favorite = Favorite.objects.all().values_list(
            'recipe',
            flat=True
        )
        recipes_is_in_shopping_cart = ShopList.objects.all().values_list(
            'recipe',
            flat=True
        )
        author_id = self.request.query_params.get('author')
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )
        tag_slugs = self.request.query_params.getlist('tags')
        if author_id is not None and author_id.isdigit():
            queryset = queryset.filter(author=author_id)
        if is_favorited == '1':
            queryset = queryset.filter(id__in=recipes_is_in_favorite)
        if is_in_shopping_cart == '1':
            queryset = queryset.filter(id__in=recipes_is_in_shopping_cart)
        if tag_slugs:
            tags = Tag.objects.filter(slug__in=tag_slugs)
            tag_recipe_queryset_id = RecipeTag.objects.all().values_list(
                'recipe',
                flat=True
            )
            for tag in tags:
                tag_recipes_id = tag.tag_recipes.all().values_list(
                    'recipe',
                    flat=True
                )
                tag_recipe_queryset_id = (
                    tag_recipe_queryset_id.intersection(tag_recipes_id)
                )

            queryset = queryset.filter(id__in=tag_recipe_queryset_id)
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return RecipeCreateSerializer
        if self.action == 'partial_update':
            return RecipeUpdateSerializer
        if self.action == 'get_short_link':
            return ShortLinkSerializer
        if self.action == 'add_delete_favorite':
            return FavoriteSerializer
        if self.action == 'add_delete_shopping_cart':
            return FavoriteSerializer
        return RecipeSerializer

    def create_new_ingredients(self, id_amount, recipe):
        if not id_amount:
            return False
        for item in id_amount:
            if id_amount.count(item) > 1:
                return False

        for item in id_amount:
            current_ingredient = get_object_or_404(Ingredient, pk=item['id'])
            if item['amount'] < 1:
                return False
            RecipeIngredientsAmount.objects.create(
                recipe=recipe,
                ingredient=current_ingredient,
                amount=item['amount']
            )
        return True

    def create_new_tags(self, tags, recipe):
        if not tags:
            return False
        for tag in tags:
            if tags.count(tag) > 1:
                return False
        for tag_id in tags:
            current_tag = get_object_or_404(Tag, pk=tag_id)
            RecipeTag.objects.create(
                recipe=recipe,
                tag=current_tag,
            )
        return True

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = dict(serializer.validated_data)
        id_amount = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        user = request.user
        recipe = Recipe.objects.create(**validated_data, author=user)
        if (
            not self.create_new_ingredients(id_amount, recipe)
            or not self.create_new_tags(tags, recipe)
        ):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        instance_serializer = RecipeSerializer(
            recipe,
            context={'request': request}
        )
        return Response(
            instance_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = dict(serializer.validated_data)
        recipe = get_object_or_404(Recipe, pk=pk)
        if recipe.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if 'image' in validated_data:
            recipe.image = validated_data['image']
        recipe.cooking_time = validated_data['cooking_time']
        recipe.text = validated_data['text']
        recipe.name = validated_data['name']
        recipe.save()
        id_amount = validated_data['ingredients']
        tags = validated_data['tags']
        recipe.recipe_tags.all().delete()
        recipe.ingredient_amount.all().delete()
        if (
            not self.create_new_ingredients(id_amount, recipe)
            or not self.create_new_tags(tags, recipe)
        ):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        instance_serializer = RecipeSerializer(
            recipe,
            context={'request': request}
        )
        return Response(
            instance_serializer.data
        )

    @action(
        methods=['get',],
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
        methods=['get',],
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
        df = pd.DataFrame(shop_list, columns=['Ingredient', 'amount', 'unit'])
        df_grouped = df.groupby(['Ingredient', 'unit']).amount.sum()
        df_grouped.to_csv('recipes/shop_list/shop_list.csv')
        with open('recipes/shop_list/shop_list.csv', 'rb') as f:
            data = f.read()
        response = HttpResponse(
            data,
            content_type='text/csv',
            headers={
                "Content-Disposition": 'attachment; filename="shop_list.csv"'
            },
        )
        return response
