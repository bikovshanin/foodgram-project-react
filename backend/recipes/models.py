from colorfield.fields import ColorField
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Ingredient(models.Model):
    """Модель ингредиентов без их количества."""
    name = models.TextField(max_length=256, verbose_name='Название продукта')
    measurement_unit = models.TextField(
        max_length=256, verbose_name='Единицы измерения'
    )

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Tag(models.Model):
    """Модель Тэгов."""
    name = models.CharField(verbose_name='Название', max_length=20)
    color = ColorField(verbose_name='Хекс-код')
    slug = models.SlugField(unique=True, verbose_name='Идентификатор')

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('id',)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецептов."""
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги',
        blank=False
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        related_name='recipes',
        through='RecipeIngredients',
        verbose_name='Ингридиенты',
        blank=False
    )
    name = models.TextField(
        max_length=200, verbose_name='Название рецепта',
        blank=False
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        null=True,
        blank=False,
        verbose_name='Изображение'
    )
    text = models.TextField(verbose_name='Описание рецепта', blank=False)
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления', blank=False
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)

    def __str__(self):
        return f'{self.name} от автора: {self.author.username}'


class RecipeIngredients(models.Model):
    """Модель связи ингредиентов и их количества с рецептами."""
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='recipe'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингридиент',
        related_name='ingredient'
    )
    amount = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        ordering = ('ingredient',)

    def __str__(self):
        return f'{self.ingredient.name} в рецепте: {self.recipe.name}'


class Favorite(models.Model):
    """Модель добавления рецептов в избранное."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favorite_user'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favorite_recipe'
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite'
            ),)
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранное'
        ordering = ('recipe',)


class ShoppingCard(models.Model):
    """Модель добавления рецептов в список покупок."""
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             verbose_name='Пользователь')
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='shoping_cart_recipes'
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_soppingcard'
            ),)
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ('recipe',)
