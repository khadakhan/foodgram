from django_filters import rest_framework as filters

from recipes.models import (
    Recipe,
    Tag
)


class RecipeFilter(filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shop',
    )
    is_favorited = filters.BooleanFilter(
        method='filter_is_favorite'
    )

    class Meta:
        model = Recipe
        fields = (
            'author',
            'tags'
        )

    def filter_is_in_shop(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value:
            queryset = queryset.filter(user_add_shop__user=user)
            return queryset
        return queryset

    def filter_is_favorite(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value:
            queryset = queryset.filter(user_add_shop__user=user)
            return queryset
        return queryset
