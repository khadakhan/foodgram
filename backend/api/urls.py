from django.urls import include, path
from rest_framework import routers

from api.views import (
    FoodUserViewSet,
    IngredientViewSet,
    RecipeViewSet,
    TagViewSet
)

app_name = 'api'

router_v1 = routers.DefaultRouter()
router_v1.register('users', FoodUserViewSet, basename='users')
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register('ingredients', IngredientViewSet, basename='ingredients')
router_v1.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
