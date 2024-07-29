import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (
    # Favorite,
    Ingredient,
    Recipe,
    RecipeIngredientsAmount,
    ShopList,
    Tag
)

User = get_user_model()

SUBSCRIPTION_AMOUNT_RECIPE = 10

# =============================Users=======================================


class Base64ImageField(serializers.ImageField):
    """Convert base64 format to file."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserAvatarSerializer(serializers.ModelSerializer):
    """Serializer for work with avatar."""
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class UserListRetrieveSerializer(serializers.ModelSerializer):
    """Serializer for list, retrive, me endpoints."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context['request']
        if request.user.id in obj.subscribers.all().values_list(
            'user',
            flat=True
        ):
            return True
        return False


class RecipesInSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )

    def get_recipes(self, obj):
        if ('recipes_limit' in self.context['request'].query_params
            and (self.context['request'].
                 query_params['recipes_limit'].isdigit())):
            recipes_limit = (
                int(self.context['request'].query_params['recipes_limit'])
            )
            recipes_list = (
                obj.recipes.all()[:recipes_limit]
            )
            return RecipesInSubscriptionSerializer(
                recipes_list,
                many=True
            ).data
        recipes_list = obj.recipes.all()[:SUBSCRIPTION_AMOUNT_RECIPE]
        return RecipesInSubscriptionSerializer(recipes_list, many=True).data

    def get_is_subscribed(self, obj):
        request = self.context['request']
        if request.user.id in obj.subscribers.all().values_list(
            'user',
            flat=True
        ):
            return True
        return False

    def get_recipes_count(self, obj):
        return obj.recipes.count()


# ======================Recipes=======================================


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


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
        user = self.context['request'].user
        if user.is_authenticated:
            if obj.id in user.recipes_in_favorites.all().values_list(
                'recipe',
                flat=True
            ):
                return True
            else:
                return False
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            if obj.id in user.what_by_user.all().values_list(
                'recipe',
                flat=True
            ):
                return True
            else:
                return False
        return False


class IdAmountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    def validate_id(self, value):
        if value < 1:
            serializers.ValidationError(
                'Количество ингеридента должно быть положительное целое число'
            )
        return value


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = IdAmountSerializer(many=True)
    tags = serializers.ListField(child=serializers.IntegerField())
    image = Base64ImageField()
    cooking_time = serializers.IntegerField()

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

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError('Заполните ингредиенты.')
        id_list = [item['id'] for item in value]

        for id in id_list:
            if id_list.count(id) > 1:
                raise serializers.ValidationError(
                    'Ингредиенты в рецепте не должны повторяться.'
                )
            if not Ingredient.objects.filter(pk=id).exists():
                raise serializers.ValidationError(
                    'Такого ингредиента нет.'
                )
        for item in value:
            if item['amount'] < 1:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть целое число'
                    ' больше нуля.'
                )
        return value

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError('Проверьте время приготовления.')
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Заполните теги.')
        for tag_id in value:
            if value.count(tag_id) > 1:
                raise serializers.ValidationError(
                    'Теги в рецепте не должны повторяться.'
                )
            if not Tag.objects.filter(pk=tag_id).exists():
                raise serializers.ValidationError(
                    'Такого тега нет.'
                )
        return value


class RecipeUpdateSerializer(RecipeCreateSerializer):
    image = Base64ImageField(required=False, allow_null=True)


class ShortLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = [
            'short-link',
        ]
        extra_kwargs = {
            'short-link': {'source': 'short_link'},
        }


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
