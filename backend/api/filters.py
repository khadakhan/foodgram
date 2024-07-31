from django_filters import rest_framework as filters

from recipes.models import Recipe, RecipeTag, Tag


class RecipeFilter(filters.FilterSet):
    class Meta:
        model = Recipe
        fields = (
            'author',
        )

    @property
    def qs(self):
        queryset = super().qs
        user = self.request.user
        author_id = self.request.query_params.get('author')
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )
        tag_slugs = self.request.query_params.getlist('tags')
        if author_id is not None and author_id.isdigit():
            queryset = queryset.filter(author=author_id)
        if tag_slugs:
            tags = Tag.objects.filter(slug__in=tag_slugs).all()
            tag_recipe_queryset_id = RecipeTag.objects.filter(
                tag__in=tags
            ).values_list(
                'recipe',
                flat=True
            )
            queryset = queryset.filter(id__in=tag_recipe_queryset_id)
        if user.is_authenticated:
            if is_favorited == '1':
                in_favorite = user.recipes_in_favorites.all().values_list(
                    'recipe',
                    flat=True
                )
                queryset = queryset.filter(id__in=in_favorite)
            if is_in_shopping_cart == '1':
                in_shopping_cart = user.what_by_user.all().values_list(
                    'recipe',
                    flat=True
                )
                queryset = queryset.filter(id__in=in_shopping_cart)
        return queryset
