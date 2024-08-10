from django.contrib import admin

from recipes.models import (
    Ingredient,
    Favorite,
    Recipe,
    RecipeIngredientsAmount,
    Shop,
    Tag
)


class RecipeIngredientsAmountInline(admin.TabularInline):
    model = RecipeIngredientsAmount
    min_num = 1
    extra = 0


class FavoriteInline(admin.TabularInline):
    model = Favorite
    extra = 0


class ShopInline(admin.TabularInline):
    model = Shop
    extra = 0


class RecipeAdmin(admin.ModelAdmin):
    readonly_fields = ('get_is_favorite',)
    list_display = (
        'name',
        'author',
        'get_is_favorite',
        'get_tags',
        'get_ingredients',
        'short_link'
    )
    search_fields = ('author',)
    list_filter = ('tags',)
    list_display_links = ('name',)
    filter_horizontal = ('tags',)
    inlines = (
        RecipeIngredientsAmountInline,
        FavoriteInline,
        ShopInline,
    )

    @admin.display(description='Кол-во добавлений в избранное')
    def get_is_favorite(self, obj):
        return obj.favorite_set.count()

    @admin.display(description='Теги')
    def get_tags(self, obj):
        return ', '.join([tag.name for tag in obj.tags.all()])

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        return ', '.join(
            [ingredient.name for ingredient in obj.ingredients.all()]
        )


class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit',
    )
    list_editable = ('measurement_unit',)
    search_fields = ('name',)
    list_filter = ('name',)
    list_display_links = ('name',)


class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    list_editable = ('slug',)
    search_fields = ('name',)
    list_filter = ('name',)
    list_display_links = ('name',)


class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )
    search_fields = ('recipe',)
    list_filter = ('user',)
    list_display_links = ('user',)


class ShopAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )
    search_fields = ('recipe',)
    list_filter = ('user',)
    list_display_links = ('user',)


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Shop, ShopAdmin)
admin.site.register(Tag, TagAdmin)
