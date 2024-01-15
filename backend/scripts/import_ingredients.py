import json

from recipes.models import Ingredient, Tag


def run():
    with open('data/ingredients.json', 'r', encoding='utf-8') as file:
        ingredient_data = json.load(file)
    for item in ingredient_data:
        obj = Ingredient(
            name=item['name'],
            measurement_unit=item['measurement_unit']
        )
        obj.save()
    print("Ingredient import finished.")

    with open('data/tags.json', 'r', encoding='utf-8') as file:
        tag_data = json.load(file)
    for item in tag_data:
        tag_obj = Tag(
            name=item['name'],
            color=item['color'],
            slug=item['slug']
        )
        tag_obj.save()
    print("Tag import finished.")
