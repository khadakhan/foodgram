from django_filters import rest_framework as filters

from recipes.models import (
    Recipe,
    Tag
)

IS_IN = [(0, 'не добавлен'), (1, 'добавлен')]


class RecipeFilter(filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    is_in_shopping_cart = filters.ChoiceFilter(
        choices=IS_IN,
        method='filter_is_in'
    )
    is_favorited = filters.ChoiceFilter(
        choices=IS_IN,
        method='filter_is_in'
    )

    class Meta:
        model = Recipe
        fields = (
            'author',
            'tags'
        )

    def filter_is_in(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value == '1':
            if name == 'is_in_shopping_cart':
                in_list = user.recipe_add_shoplist.all().values_list(
                    'recipe',
                    flat=True
                )
            if name == 'is_favorited':
                in_list = user.favorite_set.all().values_list(
                    'recipe',
                    flat=True
                )
            queryset = queryset.filter(id__in=in_list)
        return queryset
