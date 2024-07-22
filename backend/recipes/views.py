from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response

from recipes.models import (Ingredient, Recipe,
                            RecipeIngredientsAmount,
                            RecipeTag,
                            Tag)
from recipes.serializers import (IngredientSerializer,
                                 RecipeSerializer,
                                 RecipeCreateSerializer,
                                 TagSerializer)
from users.pagination import UsersPagination


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
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return RecipeCreateSerializer
        return RecipeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = dict(serializer.validated_data)
        id_amount = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        user = request.user
        recipe = Recipe.objects.create(**validated_data, author=user)
        for item in id_amount:
            current_ingredient = get_object_or_404(Ingredient, pk=item['id'])
            RecipeIngredientsAmount.objects.create(
                recipe=recipe,
                ingredient=current_ingredient,
                amount=item['amount']
            )
        for id in tags:
            current_tag = Tag.objects.get(pk=id)
            RecipeTag.objects.create(
                recipe=recipe,
                tag=current_tag,
            )
        instance_serializer = RecipeSerializer(
            recipe,
            context={'request': request}
        )
        return Response(
            instance_serializer.data,
            status=status.HTTP_201_CREATED
        )
