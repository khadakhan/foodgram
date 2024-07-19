from django.urls import include, path
from rest_framework import routers
from users import views

app_name = 'api'

router_v1 = routers.DefaultRouter()
router_v1.register('users', views.CustomUserViewSet, basename='users')

urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/token/login/', views.CustomTokenCreateView.as_view()),
    path('auth/', include('djoser.urls.authtoken')),
]
