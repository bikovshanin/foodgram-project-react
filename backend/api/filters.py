from django.contrib.auth import get_user_model
from django_filters.rest_framework import FilterSet, filters
from rest_framework.filters import SearchFilter

from recipes.models import Recipe

User = get_user_model()


class IngredientSearchFilter(SearchFilter):
    """
    Фильтр для поиска по ингредиентам при добавлении рецепта.
    """
    search_param = 'name'


class RecipeFilter(FilterSet):
    """
    Фильтр для сортировки рецептов по параметрам переданным в запросе.
    """
    is_favorited = filters.BooleanFilter(method='filter_is_favorite')
    author = filters.ModelChoiceFilter(queryset=User.objects.all())
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_in_shopping_cart'
    )
    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'author', 'is_in_shopping_cart', 'tags']

    def filter_is_favorite(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorite_recipe__user=user)
        return queryset

    def filter_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shoping_cart_recipes__user=user)
        return queryset
