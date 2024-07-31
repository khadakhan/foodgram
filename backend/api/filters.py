from django_filters import rest_framework as filters

from recipes.models import (
    Recipe,
    Tag
)

TAGS = [(tag.slug, tag.id) for tag in Tag.objects.all()]
IS_IN = [(0, 'не добавлен'), (1, 'добавлен')]


class RecipeFilter(filters.FilterSet):
    author = filters.CharFilter(
        field_name='author',
    )
    tags = filters.MultipleChoiceFilter(
        field_name='tags__slug',
        distinct=True,
        choices=TAGS
    )
    is_in_shopping_cart = filters.ChoiceFilter(
        choices=IS_IN,
        method='filter_is_in'
    )
    is_favorited = filters.ChoiceFilter(
        choices=IS_IN,
        method='filter_is_in'
    )

    def filter_is_in(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value == '1':
            if name == 'is_in_shopping_cart':
                in_list = user.what_by_user.all().values_list(
                    'recipe',
                    flat=True
                )
            if name == 'is_favorited':
                in_list = user.recipes_in_favorites.all().values_list(
                    'recipe',
                    flat=True
                )
            queryset = queryset.filter(id__in=in_list)
        return queryset

    class Meta:
        model = Recipe
        fields = (
            'author',
        )
