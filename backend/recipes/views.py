from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import short_url

from recipes.models import (Favorite,
                            Ingredient,
                            Recipe,
                            RecipeIngredientsAmount,
                            RecipeTag,
                            ShopList,
                            Tag)
from recipes.permissions import IsAuthor
from recipes.serializers import (IngredientSerializer,
                                 RecipeSerializer,
                                 RecipeCreateSerializer,
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
            return RecipeCreateSerializer
        if self.action == 'get_short_link':
            return ShortLinkSerializer
        return RecipeSerializer

# ----------вспомогательные методы начало-----------------

    def create_new_ingredients(self, id_amount, recipe):
        for item in id_amount:
            current_ingredient = get_object_or_404(Ingredient, pk=item['id'])
            RecipeIngredientsAmount.objects.create(
                recipe=recipe,
                ingredient=current_ingredient,
                amount=item['amount']
            )

    def create_new_tags(self, tags, recipe):
        for id in tags:
            current_tag = Tag.objects.get(pk=id)
            RecipeTag.objects.create(
                recipe=recipe,
                tag=current_tag,
            )

# ---------вспомогательные методы конец-------------------

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = dict(serializer.validated_data)
        id_amount = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        user = request.user
        recipe = Recipe.objects.create(**validated_data, author=user)
        self.create_new_ingredients(id_amount, recipe)
        self.create_new_tags(tags, recipe)
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
        self.create_new_ingredients(id_amount, recipe)
        self.create_new_tags(tags, recipe)
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
        return super().get_permissions()
