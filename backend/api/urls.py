from django.urls import include, path
from rest_framework import routers

from api.views import (IngredientViewSet, RecipeViewSet, ShoppingCartView,
                       SubscribeViewSet, TagViewSet)

app_name = 'api'

router_v1 = routers.DefaultRouter()
router_v1.register('users', SubscribeViewSet, basename='subscribe')
router_v1.register('recipes', RecipeViewSet, basename='recipe')
router_v1.register('tags', TagViewSet, basename='tag')
router_v1.register('ingredients', IngredientViewSet, basename='ingredient')


urlpatterns = [
    path(
        'recipes/download_shopping_cart/', ShoppingCartView.as_view(),
        name='download_shopping_cart'
    ),
    path('', include(router_v1.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
