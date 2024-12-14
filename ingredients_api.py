import requests
import os

def get_all_ingredients():
    url = 'https://food-ingredients-api-production.up.railway.app/all'

    response = requests.get(url)

    data = response.json()
    
    possible_words_list = []
    
    for item in data['ingredients']:
        possible_words_list.append(item['name'].lower())

    return possible_words_list

def get_ingredient(ingredient):
    url = 'https://food-ingredients-api-production.up.railway.app/ingredients'
    parameters = {'name': ingredient}

    response = requests.get(url, params=parameters)

    data = response.json()
    
    if 'ingredient' in data:
        return data['ingredient'][0]
    else:
        return None # We are returning none because that way we can 
    
def add_ingredient(ingredients):
    add_url = 'https://food-ingredients-api-production.up.railway.app/add'
    headers = {
        "api-key": os.environ.get("SECRET_API_KEY"),  # Replace with your actual API key
        "Content-Type": "application/json"
    }

    # If a single ingredient is passed, wrap it in a list
    if isinstance(ingredients, dict):
        ingredients = [ingredients]

    response = requests.post(add_url, headers=headers, json=ingredients)

    # Error handling
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        return f'HTTP error occurred: {err}'
    except Exception as err:
        return f'Other error occurred: {err}'