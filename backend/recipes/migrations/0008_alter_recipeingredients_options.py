# Generated by Django 5.0 on 2024-01-13 08:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0007_alter_recipe_options_recipe_pub_date'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='recipeingredients',
            options={'verbose_name': 'Ингредиент в рецепте', 'verbose_name_plural': 'Ингредиенты в рецептах'},
        ),
    ]