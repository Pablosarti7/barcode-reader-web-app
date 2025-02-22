from ingredients_api import get_all_ingredients
from thefuzz import process
import re
import json


def autosuggest(prefix):
    ingredients = get_all_ingredients()
    possible_words_list = [ingredient['name'].lower() for ingredient in ingredients['ingredients']]

    # you can add code here that will specify not to append matches with less then 70 percent score if the words are not relevant
    if prefix:
        best_match = process.extract(prefix, possible_words_list)

        matches_list = [t[0] for t in best_match]

        return matches_list

    return ''


# Simple function to create a dictionary structure
def create_structure(name: str, ingredients: str, barcode):
    return {"name": name, "ingredients": ingredients, 'barcode': barcode}


def split_string_advanced(input_string):
    # Match items with optional parentheses that might contain commas
    pattern = r'([^,(]+(?:\([^)]*\))?[^,]*)'
    matches = re.findall(pattern, input_string)
    # Clean up any leading/trailing spaces
    return [match.strip() for match in matches if match.strip()]

