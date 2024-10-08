from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from api.const import MAX_VALUE, MIN_VALUE
from recipes.models import (
    UserRecipeBaseModel,
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredientsAmount,
    Shop,
    Tag
)
from users.models import (
    Subscription,
)

User = get_user_model()
# =============================Users=======================================


class UserAvatarSerializer(serializers.ModelSerializer):
    """Serializer for work with avatar."""

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class UserListRetrieveSerializer(UserSerializer):
    """Serializer for list, retrive, me endpoints."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer):
        model = User
        fields = UserSerializer.Meta.fields + ('is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context['request']
        return (request and request.user
                and obj.author_subscriptions.filter(
                    user=request.user.id
                ).exists())


class SubscriptionSerializer(UserListRetrieveSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(default=0)

    class Meta(UserListRetrieveSerializer):
        model = User
        fields = UserListRetrieveSerializer.Meta.fields + (
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context['request']
        recipes_limit = request.POST.get('recipes_limit', 'привет')
        try:
            recipes_limit = int(recipes_limit)
        except ValueError:
            recipes_limit = None
        recipes_list = obj.recipes.all()[:recipes_limit]
        return FavoriteShopSubscriptSerializer(
            recipes_list,
            context=self.context,
            many=True
        ).data


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        user = data['user']
        author = data['author']
        if user.id == author.id:
            raise serializers.ValidationError(
                {'subscription error': 'Нельзя подписаться на себя.'}
            )
        if Subscription.objects.filter(
            user=user, author=author
        ).exists():
            raise serializers.ValidationError(
                {'subscription error': 'Подписка уже есть.'}
            )
        return data

    def to_representation(self, instance):
        return SubscriptionSerializer(
            instance.author,
            context=self.context
        ).data

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
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredientsAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, required=True)
    author = UserListRetrieveSerializer(read_only=True)
    ingredients = RecipeIngredientAmountSerializer(
        source='ingredient_amount',
        many=True
    )
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)

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


class IdAmountSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
    )
    amount = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE
    )


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = IdAmountSerializer(many=True)
    tags = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all()
    ))
    image = Base64ImageField(allow_null=True, allow_empty_file=True)
    cooking_time = serializers.IntegerField(min_value=MIN_VALUE,
                                            max_value=MAX_VALUE)

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

    @staticmethod
    def create_new_ingredients(ingredients, recipe):
        objs = [
            RecipeIngredientsAmount(
                recipe=recipe,
                ingredient_id=item['id'].id,
                amount=item['amount']
            )
            for item in ingredients
        ]
        RecipeIngredientsAmount.objects.bulk_create(objs)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        author = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data, author=author)
        recipe.save()
        self.create_new_ingredients(ingredients, recipe)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.tags.remove()
        instance.ingredient_amount.all().delete()
        self.create_new_ingredients(ingredients, instance)
        instance.tags.set(tags)
        return super().update(instance=instance, validated_data=validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(
            instance=instance,
            context=self.context
        ).data

    def validate(self, data):
        if 'ingredients' not in data:
            raise serializers.ValidationError(
                {'ingredients': 'Укажите ингредиенты!'}
            )
        ingredients = data['ingredients']
        id_list = [item['id'].id for item in ingredients]
        if len(set(id_list)) != len(id_list):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться.'}
            )
        if 'tags' not in data:
            raise serializers.ValidationError(
                {'tags': 'Укажите теги!'}
            )
        tags = data['tags']
        if len(set(tags)) != len(tags):
            raise serializers.ValidationError(
                {'tags': 'Теги в рецепте не должны повторяться.'}
            )
        return data


class ShortLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'short-link',
        )
        extra_kwargs = {
            'short-link': {'source': 'short_link'},
        }


class FavoriteShopSubscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class FavoriteShopCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRecipeBaseModel
        fields = (
            'user',
            'recipe',
        )
        abstract = True

    def validate(self, data):
        model = self.Meta.model
        if model.objects.filter(
                user=data['user'],
                recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError(
                {f'{model._meta.verbose_name} error': 'Был добавлен ранее.'}
            )
        return data

    def to_representation(self, instance):
        recipe = instance.recipe
        return FavoriteShopSubscriptSerializer(
            recipe,
            context=self.context
        ).data


class FavoriteCreateSerializer(FavoriteShopCreateSerializer):
    class Meta:
        model = Favorite
        fields = (
            'user',
            'recipe',
        )


class ShopCreateSerializer(FavoriteShopCreateSerializer):
    class Meta:
        model = Shop
        fields = (
            'user',
            'recipe',
        )
