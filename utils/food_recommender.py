from apis.products_api import get_all_products
from apis.ingredients_api import get_all_ingredients
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def create_products_df():
    data = get_all_products()

    # Check if the call returned an error
    if isinstance(data, dict) and "error" in data:
        return None

    # Convert to DataFrame
    try:
        # Assuming the data is a list of dictionaries
        products_df = pd.DataFrame(data)
    except ValueError as e:
        return None

    return products_df



def get_similarity_matrix():

    products_df = create_products_df()

    # Combine ingredients into a single string for each food item
    ingredient_corpus = products_df['ingredients']

    # Initialize TF-IDF Vectorizer
    vectorizer = TfidfVectorizer()

    # Fit and transform the ingredient lists
    tfidf_matrix = vectorizer.fit_transform(ingredient_corpus)

    # Compute cosine similarity between all food items
    cosine_sim = cosine_similarity(tfidf_matrix)

    # Create a multi-index for rows and columns using both name and barcode
    multi_index = pd.MultiIndex.from_arrays(
        [products_df['name'], products_df['barcode']], 
        names=['name', 'barcode']
    )

    # Now create the similarity_df using the multi-index for both rows and columns
    similarity_df = pd.DataFrame(cosine_sim, index=multi_index, columns=multi_index)
    
    return products_df, similarity_df

health_rating_to_score = {
    'healthy': 2,
    'neutral': 1,
    'unhealthy': -1
}


def get_health_scores_from_db():
    ingredients_data = get_all_ingredients()
    # Check if the call returned an error
    if isinstance(ingredients_data, dict) and "error" in ingredients_data:
        return None
    else:
        # Convert to DataFrame
        try:
            ingredients_df = pd.DataFrame(ingredients_data['ingredients'])

        except ValueError as e:
            return None

    # Exclude unwanted names first
    excluded_items = ['Sugar', 'Corn Syrup', 'Cane Sugar',
                      'Pure Cane Sugar', 'Coffee Caramelized Sugar', 'Corn']

    filtered_df = ingredients_df[~ingredients_df['name'].isin(excluded_items)]

    # Filter for healthy, neutral, and unhealthy ratings
    filtered_df = filtered_df[
        (filtered_df['rating'] == 'healthy') |
        (filtered_df['rating'] == 'neutral') |
        (filtered_df['rating'] == 'unhealthy')
    ]

    # Map health ratings to scores
    filtered_df['health_score'] = filtered_df['rating'].map(
        health_rating_to_score)

    return filtered_df.set_index('name')['health_score']


def calculate_health_score(ingredients, health_scores):
    score = 0
    for ingredient in ingredients.split(", "):
        if ingredient not in health_scores:  # Skip if ingredient not found
            return None  # Mark this row for exclusion
        score += health_scores[ingredient]
    return score


def recommend_healthier_food(item_name, top_n=3):
    # Get fresh data each time the function is called
    products_df, similarity_df = get_similarity_matrix()
    health_scores = get_health_scores_from_db()

    # Apply to dataset
    products_df['health_score'] = products_df['ingredients'].apply(
        lambda x: calculate_health_score(x, health_scores))

    filtered_df = products_df[products_df['name'] == item_name]
    if not filtered_df.empty:
        item_row = filtered_df.iloc[0]
    else:
        # Handle the case where no matching item was found
        # For example:
        # raise ValueError(f"No product found with name '{item_name}'")
        # or return None, depending on your needs
        return None
    
    item_score = item_row['health_score']
    item_category = item_row['category'].lower()


    # Check if there is NaN values and set to 0 if true
    if pd.isna(item_score):
        item_score = 0
        

    # Filter for healthier items in the same category
    healthier_items = products_df[(products_df['health_score'] > item_score) & (
        products_df['category'].str.lower() == item_category)]

    # Compute similarity scores
    sim_scores = similarity_df[item_name].loc[healthier_items['name']]
    
    # Sort and return top recommendations
    recommended_items = sim_scores.sort_values(ascending=False, by='name').iloc[:top_n]
    
    return recommended_items.index
