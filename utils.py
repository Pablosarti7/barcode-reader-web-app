from ingredients_api import get_all_ingredients
from thefuzz import process
import re
import json


def autosuggest(prefix):
    ingredients = get_all_ingredients()
    # you can add code here that will specify not to append matches with less then 70 percent score if the words are not relevant
    if prefix:
        best_match = process.extract(prefix, ingredients)

        matches_list = [t[0] for t in best_match]

        return matches_list

    return ''


def clean_ingredient(ingredient):
    # Remove parentheses and their contents
    ingredient = re.sub(r'\(.*?\)', '', ingredient)
    # Trim whitespace
    ingredient = ingredient.strip()
    # Remove trailing special characters
    ingredient = re.sub(r'[()\[\]0-9]', '', ingredient)

    return ingredient.lower()


def clean_ingredients(input_string):
    # Splitting the words by the chosen characters
    split_string = re.split(',|\.|:', input_string)
    # Clean each ingredient
    clean_ingredients = [clean_ingredient(
        ingredient) for ingredient in split_string if ingredient]
    # Getting rid of the list item with % signs
    filtered_list = [
        item for item in clean_ingredients if '%' not in item and 'contains' not in item]

    return filtered_list

# Simple function to create a dictionary structure
def create_structure(name, ingredients):
    return json.dumps({"name": name, "ingredients": ingredients})

