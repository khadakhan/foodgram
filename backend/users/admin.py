from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser, Subscription


class SubscriptionInline(admin.TabularInline):
    """Inline for users administration."""
    model = Subscription
    fk_name = "user"
    extra = 0


class CustomUserAdmin(UserAdmin):
    """Users """
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
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
        'is_active')
    search_fields = ('email', 'username')
    ordering = ('email',)
    inlines = [
        SubscriptionInline,
    ]


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'subscription',
    )
    list_editable = ('subscription',)
    search_fields = ('user',)
    list_filter = ('user',)
    list_display_links = ('user',)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
