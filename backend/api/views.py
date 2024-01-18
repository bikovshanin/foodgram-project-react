from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (SAFE_METHODS, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import IngredientSearchFilter, RecipeFilter
from api.paginators import LimitPaginator
from api.permissions import AuthorOrReadOnly
from api.serializers import (FollowSerializer, IngredientSerializer,
                             RecipeCreateSerializer, RecipeSerializer,
                             RecipeShortSerializer, TagSerializer)
from followers.models import Follow
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredients,
                            ShoppingCard, Tag)

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Представление для работы с Тэгами.
    """
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Представление для работы с рецептами.
    Так же используется для работы с избранными рецептами и списком покупок.
    """
    queryset = Recipe.objects.all()
    pagination_class = LimitPaginator
    permission_classes = (IsAuthenticatedOrReadOnly, AuthorOrReadOnly)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_post(self, request, model):
        try:
            recipe = self.get_object()
        except Http404:
            return Response(
                {'detail': 'Рецепт не найден.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if model.objects.filter(
                user=request.user, recipe=recipe
        ).exists():
            return Response(
                {'detail': f'Рецепт уже добавлен в '
                           f'{model._meta.verbose_name_plural}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        model.objects.create(user=request.user, recipe=recipe)
        updated_recipe = Recipe.objects.get(pk=recipe.pk)
        serialized_recipe = RecipeShortSerializer(updated_recipe).data
        return Response(serialized_recipe, status=status.HTTP_201_CREATED)

    def perform_delete(self, request, model):
        recipe = self.get_object()
        if not model.objects.filter(
                user=request.user, recipe=recipe
        ).exists():
            return Response(
                {'detail': f'Рецепта нет в {model._meta.verbose_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        model.objects.filter(user=request.user, recipe=recipe).delete()
        return Response(
            {'detail': f'Рецепт удалён из {model._meta.verbose_name}.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=True, methods=['post'], url_path='favorite',
        permission_classes=(IsAuthenticatedOrReadOnly,)
    )
    def favorite_recipe(self, request, pk=None):
        return self.perform_post(request, Favorite)

    @favorite_recipe.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self.perform_delete(request, Favorite)

    @action(
        detail=True, methods=['post'], url_path='shopping_cart',
        permission_classes=(IsAuthenticatedOrReadOnly,)
    )
    def shopping_cart(self, request, pk=None):
        return self.perform_post(request, ShoppingCard)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.perform_delete(request, ShoppingCard)


class SubscribeViewSet(UserViewSet):
    """
    Представление для работы с подписками.
    """
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = LimitPaginator

    def get_permissions(self):
        if self.action == 'me':
            self.permission_classes = (IsAuthenticated,)
        return super().get_permissions()

    @action(detail=True, methods=['POST'])
    def subscribe(self, request, id=None):
        serializer = FollowSerializer(
            data={'following': id}, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(
            user=self.request.user,
            following=get_object_or_404(User, id=id)
        )
        return Response(
            serializer.data, status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        try:
            Follow.objects.get(
                user=self.request.user,
                following=get_object_or_404(User, id=id)
            ).delete()
            return Response(
                {'detail': 'Вы успешно отписались от пользователя.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Follow.DoesNotExist:
            return Response(
                {'detail': 'Пользователь не найден.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False)
    def subscriptions(self, request):
        queryset = Follow.objects.filter(user=request.user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Представление для работы с ингредиентами.
    """
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (IngredientSearchFilter,)
    search_fields = ('^name',)
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    pagination_class = None


class ShoppingCartView(APIView):
    """
    Представление для скачивания файла TXT со списком покупок.
    """
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, *args, **kwargs):
        shopping_carts = ShoppingCard.objects.filter(
            user=request.user
        ).prefetch_related('recipe')
        ingredients_count = self.calculate_ingredients_count(shopping_carts)
        txt_content = self.generate_txt_content(ingredients_count)
        response = HttpResponse(txt_content, content_type='text/plain')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_cart.txt"'
        return response

    def calculate_ingredients_count(self, shopping_carts):
        ingredients_count = {}
        for shopping_cart in shopping_carts:
            recipe_ingredients = RecipeIngredients.objects.filter(
                recipe=shopping_cart.recipe
            ).values('ingredient__id').annotate(amount=Sum('amount'))
            for recipe_ingredient in recipe_ingredients:
                ingredient_id = recipe_ingredient['ingredient__id']
                amount = recipe_ingredient['amount']
                if ingredient_id in ingredients_count:
                    ingredients_count[ingredient_id] += amount
                else:
                    ingredients_count[ingredient_id] = amount
        return ingredients_count

    def generate_txt_content(self, ingredients_count):
        ingredient_ids = list(ingredients_count.keys())
        ingredients = (
            Ingredient.objects
            .filter(id__in=ingredient_ids)
            .values('id', 'name', 'measurement_unit')
        )
        txt_content = ''
        for ingredient in ingredients:
            amount = ingredients_count[ingredient['id']]
            txt_content += (
                f"{ingredient['name']} - {amount} "
                f"{ingredient['measurement_unit']}\n"
            )
        return txt_content
