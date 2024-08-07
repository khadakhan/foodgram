from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from recipes.models import Shop
from users.models import FoodUser, Subscription


class SubscriptionInline(admin.TabularInline):
    """Inline for users administration."""

    model = Subscription
    fk_name = 'user'
    extra = 0


class ShopInline(admin.TabularInline):
    """Inline for users administration."""

    model = Shop
    fk_name = "user"
    extra = 0


class FoodUserAdmin(UserAdmin):
    readonly_fields = ('how_many_subscriptions', 'how_many_recipes')
    fieldsets = (
        (None, {'fields': (
            'email', 'password', 'how_many_subscriptions', 'how_many_recipes'
        )}),
        ('Персональные данные',
            {'fields':
             ('username',
              'first_name',
              'last_name',
              'avatar')
             }),
        ('Полномочия',
            {'fields':
             ('is_active',
              'is_staff',
              'is_superuser',
              'groups',
              'user_permissions')
             }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2',),
        }),
    )
    list_display = (
        'email',
        'username',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'how_many_subscriptions',
        'how_many_recipes'
    )
    search_fields = ('email', 'username')
    ordering = ('email',)
    inlines = (
        SubscriptionInline,
        ShopInline,
    )

    def how_many_subscriptions(self, obj):
        return obj.user_subscriptions.count()

    def how_many_recipes(self, obj):
        return obj.recipes.count()


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'author',
    )
    list_editable = ('author',)
    search_fields = ('user',)
    list_filter = ('user',)
    list_display_links = ('user',)


admin.site.register(FoodUser, FoodUserAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
