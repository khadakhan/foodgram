import short_url
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils.datastructures import MultiValueDictKeyError
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from api.const import DOMAIN, SUBSCRIPTION_AMOUNT_RECIPE
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredientsAmount,
    RecipeTag,
    ShopList,
    Tag
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
        return request.user.id in obj.author_subscriptions.all().values_list(
            'user',
            flat=True
        )


class RecipesInSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(UserListRetrieveSerializer):
    recipes_count = serializers.IntegerField()
    recipes = serializers.SerializerMethodField()

    class Meta(UserListRetrieveSerializer):
        model = User
        fields = UserListRetrieveSerializer.Meta.fields + (
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        try:
            recipes_limit = (
                int(self.context['request'].query_params['recipes_limit'])
            )
        except MultiValueDictKeyError:
            recipes_limit = SUBSCRIPTION_AMOUNT_RECIPE
        recipes_list = obj.recipes.all()[:recipes_limit]
        return RecipesInSubscriptionSerializer(recipes_list, many=True).data


class SubscriptionCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)

    def validate(self, data):
        user = self.context['request'].user
        author = get_object_or_404(User, pk=data['id'])
        user_subscriptions_id = user.user_subscriptions.values_list(
            'author',
            flat=True
        )
        if (
            user.id == author.id
            or author.id in user_subscriptions_id
        ):
            raise serializers.ValidationError(
                {'subscription error': 'Нельзя подписаться на себя'
                 ' или подписка уже есть.'}
            )
        return data

    def to_representation(self, instance):
        subscription = get_object_or_404(
            User.objects.annotate(
                recipes_count=Count('recipes')
            ),
            pk=instance['id']
        )
        return SubscriptionSerializer(
            subscription,
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
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1, max_value=10000)


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = IdAmountSerializer(many=True)
    tags = serializers.ListField(child=serializers.IntegerField())
    image = Base64ImageField(allow_null=True, allow_empty_file=True)
    cooking_time = serializers.IntegerField(min_value=1, max_value=600)

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
    def create_new_ingredients(id_amount, recipe):
        objs = [
            RecipeIngredientsAmount(
                recipe=recipe,
                ingredient=Ingredient.objects.get(pk=item['id']),
                amount=item['amount']
            )
            for item in id_amount
        ]
        RecipeIngredientsAmount.objects.bulk_create(objs)

    @staticmethod
    def create_new_tags(tags, recipe):
        for tag_id in tags:
            current_tag = get_object_or_404(Tag, pk=tag_id)
            RecipeTag.objects.create(
                recipe=recipe,
                tag=current_tag,
            )

    def create(self, validated_data):
        id_amount = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        author = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data, author=author)
        short_link = 'https://{domain}/{link_id}'.format(
            domain=DOMAIN,
            link_id=short_url.encode_url(recipe.id, min_length=10)
        )
        recipe.short_link = short_link
        recipe.save()
        self.create_new_ingredients(id_amount, recipe)
        self.create_new_tags(tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        id_amount = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        super().update(instance=instance, validated_data=validated_data)
        instance.recipe_tags.all().delete()
        instance.ingredient_amount.all().delete()
        self.create_new_ingredients(id_amount, instance)
        self.create_new_tags(tags, instance)
        return instance

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
        if not data['ingredients']:
            raise serializers.ValidationError(
                {'ingredients': 'Заполните ингредиенты.'}
            )
        id_list = [item['id'] for item in data['ingredients']]
        for id in id_list:
            if id_list.count(id) > 1:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты не должны повторяться.'}
                )
            if not Ingredient.objects.filter(pk=id).exists():
                raise serializers.ValidationError(
                    {'ingredients': 'Такого ингредиента нет.'}
                )
        if 'tags' not in data:
            raise serializers.ValidationError(
                {'tags': 'Укажите теги!'}
            )
        if not data['tags']:
            raise serializers.ValidationError(
                {'tags': 'Заполните теги.'}
            )
        for tag_id in data['tags']:
            if data['tags'].count(tag_id) > 1:
                raise serializers.ValidationError(
                    {'tags': 'Теги в рецепте не должны повторяться.'}
                )
            if not Tag.objects.filter(pk=tag_id).exists():
                raise serializers.ValidationError(
                    {'tags': 'Такого тега нет.'}
                )
        if not data['image']:
            raise serializers.ValidationError(
                {'image': 'Укажите картинку!'}
            )
        return data


class ShortLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = [
            'short-link',
        ]
        extra_kwargs = {
            'short-link': {'source': 'short_link'},
        }


class FavoriteShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class FavoriteShopCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)

    def validate(self, data):
        if (
            self.context['action'] == 'add_favorite'
            and Favorite.objects.filter(
                user=self.context['request'].user, recipe=data['id']
            ).exists()
        ):
            raise serializers.ValidationError(
                {'favorite error': 'Рецепт уже добавлен в избранное'}
            )
        if (
            self.context['action'] == 'delete_favorite'
            and not Favorite.objects.filter(
                user=self.context['request'].user, recipe=data['id']
            ).exists()
        ):
            raise serializers.ValidationError(
                {'favorite error': 'Удаление невозможно. '
                 'Рецепта нет в избранном'}
            )
        if (
            self.context['action'] == 'add_shop'
            and ShopList.objects.filter(
                user=self.context['request'].user, recipe=data['id']
            ).exists()
        ):
            raise serializers.ValidationError(
                {'shop_cart error': 'Рецепт уже добавлен'}
            )
        if (
            self.context['action'] == 'delete_shop'
            and not ShopList.objects.filter(
                user=self.context['request'].user, recipe=data['id']
            ).exists()
        ):
            raise serializers.ValidationError(
                {'shopping_cart error': 'Удаление невозможно. '
                 'Рецепта нет в корзине покупок'}
            )
        return data
