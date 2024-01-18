import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from followers.models import Follow
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredients,
                            ShoppingCard, Tag)

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """
    Сериализатор для обработки картинок.
    """
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class CustomUserSerializer(UserSerializer):
    """
    Сериализатор для обработки данных пользователей.
    Так же применяется при обработке данных рецептов.
    """
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        request_user = (
            self.context['request'].user
            if 'request' in self.context else None
        )
        if request_user and not isinstance(request_user, AnonymousUser):
            return Follow.objects.filter(
                user=request_user,
                following=obj
            ).exists()
        return False


class CustomCreateUserSerializer(UserCreateSerializer):
    """
    Сериализатор для обработки данных при добавлении новых пользователей.
    """
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'password'
        )
        required_fields = (
            'email', 'username', 'first_name', 'last_name', 'password'
        )


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обработки данных ингредиентов без их количества.
    """
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обработки данных тэгов.
    """
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class RecipeIngredientsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обработки ингредиентов с их количеством.
    Используется создания рецепта.
    """
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class IngredientAmountSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обработки данных ингредиентов и их количества.
    Используется для сериализации рецептов при GET запросах.
    """
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredients
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обработки данных рецептов в сокращенном виде.
    Используется для отображения данных при подписке.
    """
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения данных рецептов.
    """
    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = IngredientAmountSerializer(
        many=True, source='recipe', required=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Favorite.objects.filter(
            user=user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and ShoppingCard.objects.filter(
            user=user, recipe=obj
        ).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обработки данных рецептов при их добавлении.
    """
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientsSerializer(many=True, required=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=True
    )
    image = Base64ImageField(max_length=None)

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time',
            'author'
        )
        required_fields = ('tags', 'ingredients')

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        if not tags or not ingredients:
            raise serializers.ValidationError(
                {'detail': 'Недостаточно данных.'}
            )
        return data

    def validate_cooking_time(self, value):
        # cooking_time = self.fields['cooking_time']
        if value > 300 or value < 1:
            raise serializers.ValidationError({
                'detail': 'Время приготовления блюда от 1 до 300 минут.'
            })
        return value

    def validate_ingredients(self, value):
        # ingredients = self.fields['ingredients']
        for ingredient_data in value:
            if not Ingredient.objects.filter(
                    id=ingredient_data['id']
            ).exists():
                raise serializers.ValidationError(
                    {'detail': 'Ингредиента не существует.'}
                )
        if len(value) != len(set([item['id'] for item in value])):
            raise serializers.ValidationError(
                {'detail': 'Ингредиенты не должны повторяться.'}
            )
        if [item for item in value if item['amount'] < 1]:
            raise serializers.ValidationError({
                'detail': 'Количество ингредиента не ниже 1.'
            })
        return value

    def validate_tags(self, value):
        # tags = self.fields['tags']
        if len(value) != len(set([item for item in value])):
            raise serializers.ValidationError(
                {'detail': 'Тэги не должны повторяться.'}
            )
        return value

    def create_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            RecipeIngredients.objects.bulk_create(
                [
                    RecipeIngredients(
                        recipe=recipe,
                        ingredient_id=ingredient.get('id'),
                        amount=ingredient.get('amount'),
                    )
                ]
            )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)
        if 'tags' in validated_data:
            instance.tags.set(validated_data.pop('tags'))
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(
            instance, context={'request': self.context.get('request')}
        ).data


class FollowSerializer(serializers.Serializer):
    """
    Сериализатор для обработки данных подписок.
    """
    id = serializers.ReadOnlyField(source='following.id')
    email = serializers.ReadOnlyField(source='following.email')
    username = serializers.ReadOnlyField(source='following.username')
    first_name = serializers.ReadOnlyField(source='following.first_name')
    last_name = serializers.ReadOnlyField(source='following.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count'
        )

    def validate(self, data):
        request = self.context.get('request')
        current_user_id = request.user.id
        following_user_id = request.parser_context['kwargs']['id']
        if int(current_user_id) == int(following_user_id):
            raise serializers.ValidationError(
                {'detail': 'Вы не можете подписаться на себя.'}
            )
        if Follow.objects.filter(
                user=request.user, following=following_user_id
        ).exists():
            raise serializers.ValidationError(
                {'detail': 'Вы уже подписаны на этого пользователя.'}
            )
        return data

    def create(self, validated_data):
        return Follow.objects.create(**validated_data)

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = Recipe.objects.filter(author=obj.following)
        if limit:
            queryset = queryset[:int(limit)]
        return RecipeShortSerializer(queryset, many=True,
                                     context={'request': request}).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.following).count()

    def get_is_subscribed(self, obj):
        request_user = self.context.get('request').user
        if request_user and not isinstance(request_user, AnonymousUser):
            return Follow.objects.filter(
                user=request_user, following=obj.following
            ).exists()
        return False
