from django.contrib import admin

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredients,
                            ShoppingCard, Tag)


class RecipeIngredientsInline(admin.TabularInline):
    model = RecipeIngredients
    autocomplete_fields = ('ingredient',)
    extra = 1


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    inlines = [RecipeIngredientsInline]
    search_fields = ('name',)
    list_display = ('name', 'measurement_unit',)
    list_filter = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [RecipeIngredientsInline]
    list_filter = ('tags', 'author', 'name')
    list_display = ('name', 'get_author', 'get_favorites_count')

    def get_author(self, obj):
        return (obj.author.get_full_name()
                if obj.author.get_full_name() else obj.author.username)

    get_author.short_description = 'Автор'

    def get_favorites_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    get_favorites_count.short_description = 'Добавлено в избранное'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    pass


@admin.register(ShoppingCard)
class ShoppingCardAdmin(admin.ModelAdmin):
    pass


@admin.register(RecipeIngredients)
class RecipeIngredientsAdmin(admin.ModelAdmin):
    pass
