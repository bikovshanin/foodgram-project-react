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

    @action(
        detail=True, methods=['post', 'delete'], url_path='favorite',
        serializer_class=RecipeShortSerializer,
        permission_classes=(IsAuthenticatedOrReadOnly,)
    )
    def favorite_recipe(self, request, pk=None):
        if request.method == 'POST':
            try:
                recipe = self.get_object()
            except Http404:
                return Response(
                    {'detail': 'Рецепт не найден.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Favorite.objects.filter(
                    user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'detail': 'Рецепт уже добавлен в избранное.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=request.user, recipe=recipe)
        elif request.method == 'DELETE':
            recipe = self.get_object()
            if not Favorite.objects.filter(
                    user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'detail': 'Рецепта нет в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.filter(user=request.user, recipe=recipe).delete()
            return Response(
                {'detail': 'Рецепт удалён из избранного.'},
                status=status.HTTP_204_NO_CONTENT
            )
        updated_recipe = Recipe.objects.get(pk=self.get_object().pk)
        serialized_recipe = RecipeShortSerializer(updated_recipe).data
        return Response(serialized_recipe, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=['post', 'delete'], url_path='shopping_cart',
        serializer_class=RecipeShortSerializer,
        permission_classes=(IsAuthenticatedOrReadOnly,)
    )
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            try:
                recipe = self.get_object()
            except Http404:
                return Response(
                    {'detail': 'Рецепт не найден.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if ShoppingCard.objects.filter(
                    user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'detail': 'Рецепт уже добавлен в список покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCard.objects.create(user=request.user, recipe=recipe)
        elif request.method == 'DELETE':
            recipe = self.get_object()
            if not ShoppingCard.objects.filter(
                    user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'detail': 'Рецепта нет в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCard.objects.filter(
                user=request.user, recipe=recipe
            ).delete()
            return Response(
                {'detail': 'Рецепта удалён из списка покупок.'},
                status=status.HTTP_204_NO_CONTENT
            )
        updated_recipe = Recipe.objects.get(pk=self.get_object().pk)
        serialized_recipe = RecipeShortSerializer(updated_recipe).data
        return Response(serialized_recipe, status=status.HTTP_201_CREATED)


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

    @action(detail=True, methods=['POST', 'DELETE'])
    def subscribe(self, request, id=None):
        following_user = get_object_or_404(User, id=id)
        if request.method == 'POST':
            serializer = FollowSerializer(
                data={'following': id}, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            follow = Follow.objects.create(
                user=self.request.user, following=following_user
            )
            user_serializer = FollowSerializer(
                follow, context={'request': request}
            )
            return Response(
                user_serializer.data, status=status.HTTP_201_CREATED
            )
        if request.method == 'DELETE':
            try:
                Follow.objects.get(
                    user=self.request.user, following=following_user
                ).delete()
                return Response(
                    {'detail': 'Вы успешно отписались от пользователя.'},
                    status=status.HTTP_204_NO_CONTENT)
            except Follow.DoesNotExist:
                return Response(
                    {'detail': 'Пользователь не найден.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(detail=False)
    def subscriptions(self, request):
        queryset = Follow.objects.filter(user=request.user).order_by('id')
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
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    pagination_class = None


class ShoppingCartView(APIView):
    """
    Представление для скачивания файла TXT со списком покупок.
    """
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, *args, **kwargs):
        shopping_carts = ShoppingCard.objects.filter(user=request.user)
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
        ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        txt_content = ''
        for ingredient in ingredients:
            ingredient_id = ingredient.id
            amount = ingredients_count[ingredient_id]
            txt_content += (f'{ingredient.name} - '
                            f'{amount} {ingredient.measurement_unit}\n')
        return txt_content
