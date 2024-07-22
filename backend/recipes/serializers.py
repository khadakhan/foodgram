from rest_framework import serializers

from recipes.models import (Favorite,
                            Ingredient,
                            Recipe,
                            RecipeIngredientsAmount,
                            ShopList,
                            Tag)
from users.serializers import Base64ImageField, UserListRetrieveSerializer


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')

# ------------------------------рецепты------------------------


class RecipeIngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = RecipeIngredientsAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def get_id(self, obj):
        return obj.ingredient.id

    def get_name(self, obj):
        return obj.ingredient.name


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, required=True)
    author = UserListRetrieveSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_ingredients(self, obj):
        ingredient_amount = obj.ingredient_amount.all()
        return RecipeIngredientAmountSerializer(
            ingredient_amount,
            many=True,
        ).data

    def get_is_favorited(self, obj):
        if obj.id in Favorite.objects.all().values_list(
            'recipe',
            flat=True
        ):
            return True
        return False

    def get_is_in_shopping_cart(self, obj):
        if obj.id in ShopList.objects.all().values_list(
            'recipe',
            flat=True
        ):
            return True
        return False
# -----------------------------------------------------


class IdAmountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = IdAmountSerializer(many=True)
    image = Base64ImageField(required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.IntegerField())

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    # def create(self, validated_data):
    #     id_amount = validated_data.pop('ingredients')
    #     user = self.context['request'].user
    #     tags = validated_data.pop('tags')
    #     recipe = Recipe.objects.create(**validated_data, author=user)
    #     for dict in id_amount:
    #         current_ingredient = Ingredient.objects.get(pk=dict['id'])
    #         RecipeIngredientsAmount.objects.create(
    #             recipe=recipe,
    #             ingredient=current_ingredient,
    #             amount=dict['amount']
    #         )
    #     for id in tags:
    #         current_tag = Tag.objects.get(pk=id)
    #         RecipeTag.objects.create(
    #             recipe=recipe,
    #             tag=current_tag,
    #         )
    #     return recipe
