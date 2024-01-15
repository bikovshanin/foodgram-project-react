from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters.rest_framework import FilterSet, filters
from rest_framework.filters import SearchFilter

from recipes.models import Recipe, Tag

User = get_user_model()


class IngredientSearchFilter(SearchFilter):
    """
    Фильтр для поиска по ингредиентам при добавлении рецепта.
    """
    search_param = 'name'

    def filter_queryset(self, request, queryset, view):
        search_terms = self.get_search_terms(request)
        if not search_terms:
            return queryset
        starts_with_conditions = [
            Q(name__istartswith=term) for term in search_terms
        ]
        contains_conditions = [
            Q(name__icontains=term) for term in search_terms
        ]
        q_objects = sorted(
            starts_with_conditions + contains_conditions,
            key=lambda q: q.negated
        )
        final_q_object = Q()
        for q_obj in q_objects:
            final_q_object |= q_obj
        return queryset.filter(final_q_object)


class RecipeFilter(FilterSet):
    """
    Фильтр для сортировки рецептов по параметрам переданным в запросе.
    """
    is_favorited = filters.BooleanFilter(method='filter_is_favorite')
    author = filters.ModelChoiceFilter(queryset=User.objects.all())
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_in_shopping_cart'
    )
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
    )

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
