from django.contrib import admin

from recipes.models import (
    Ingredient,
    Favorite,
    Recipe,
    RecipeIngredientsAmount,
    ShopList,
    Tag
)


class RecipeIngredientsAmountInline(admin.TabularInline):
    model = RecipeIngredientsAmount
    min_num = 1
    extra = 0


class FavoriteInline(admin.TabularInline):
    model = Favorite
    extra = 0


class ShopListInline(admin.TabularInline):
    model = ShopList
    extra = 0


class RecipeAdmin(admin.ModelAdmin):
    readonly_fields = ('how_many_add_in_favorite',)
    list_display = (
        'name',
        'author',
        'how_many_add_in_favorite',
    )
    search_fields = ('author',)
    list_filter = ('tags',)
    list_display_links = ('name',)
    filter_horizontal = ('tags',)
    inlines = (
        RecipeIngredientsAmountInline,
        FavoriteInline,
        ShopListInline,
    )

    def how_many_add_in_favorite(self, obj):
        return obj.favorite_set.count()


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


class ShopListAdmin(admin.ModelAdmin):
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
admin.site.register(ShopList, ShopListAdmin)
admin.site.register(Tag, TagAdmin)
