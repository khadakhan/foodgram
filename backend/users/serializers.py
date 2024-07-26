import base64
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import Recipe

User = get_user_model()

SUBSCRIPTION_AMOUNT_RECIPE = 10


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
