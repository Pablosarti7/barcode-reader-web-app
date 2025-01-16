from products_api import get_all_products
from ingredients_api import get_all_ingredients
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def get_similarity_matrix():
    data = get_all_products()

    # Check if the call returned an error
    if isinstance(data, dict) and "error" in data:
        print(f"Error: {data['error']}")
    else:
        # Convert to DataFrame
        try:
            products_df = pd.DataFrame(data)  # Assuming the data is a list of dictionaries
        except ValueError as e:
            print(f"Error converting data to DataFrame: {e}")

        # Combine ingredients into a single string for each food item
        ingredient_corpus = products_df['ingredients']

        # Initialize TF-IDF Vectorizer
        vectorizer = TfidfVectorizer()

        # Fit and transform the ingredient lists
        tfidf_matrix = vectorizer.fit_transform(ingredient_corpus)

        # Compute cosine similarity between all food items
        cosine_sim = cosine_similarity(tfidf_matrix)

        # Display the similarity matrix
        similarity_df = pd.DataFrame(cosine_sim, index=products_df['name'], columns=products_df['name'])
        return products_df, similarity_df

products_df, similarity_df = get_similarity_matrix()

health_rating_to_score = {
'healthy': 2,
'neutral': 1,
'unhealthy': -1
}


def get_health_scores_from_db():
    ingredients_data = get_all_ingredients()
    # Check if the call returned an error
    if isinstance(ingredients_data, dict) and "error" in ingredients_data:
        print(f"Error: {ingredients_data['error']}")
    else:
            # Convert to DataFrame
        try:
            ingredients_df = pd.DataFrame(ingredients_data['ingredients'])
            
        except ValueError as e:
            print(f"Error converting data to DataFrame: {e}")

    
    # Exclude unwanted names first
    excluded_items = ['Sugar', 'Corn Syrup', 'Cane Sugar', 'Pure Cane Sugar', 'Coffee Caramelized Sugar', 'Corn']
    filtered_df = ingredients_df[~ingredients_df['name'].isin(excluded_items)]

    # Filter for healthy, neutral, and unhealthy ratings
    filtered_df = filtered_df[
        (filtered_df['rating'] == 'healthy') |
        (filtered_df['rating'] == 'neutral') |
        (filtered_df['rating'] == 'unhealthy')
    ]

    # Map health ratings to scores
    filtered_df['health_score'] = filtered_df['rating'].map(health_rating_to_score)
    return filtered_df.set_index('name')['health_score']


health_scores = get_health_scores_from_db()


def calculate_health_score(ingredients, health_scores):
    score = 0
    for ingredient in ingredients.split(", "):
        if ingredient not in health_scores:  # Skip if ingredient not found
            return None  # Mark this row for exclusion
        score += health_scores[ingredient]
    return score

# Apply to dataset
products_df['health_score'] = products_df['ingredients'].apply(lambda x: calculate_health_score(x, health_scores))


def recommend_healthier_food(item_name, top_n=3):
    # Get the category of the scanned item
    
    item_row = products_df[products_df['name'] == item_name].iloc[0]
    
    item_score = item_row['health_score']
    item_category = item_row['category'].lower()
    if pd.isna(item_score):
        item_score = 0

    # Filter for healthier items in the same category
    healthier_items = products_df[(products_df['health_score'] > item_score) & (products_df['category'].str.lower() == item_category)]

    # Compute similarity scores
    sim_scores = similarity_df[item_name].loc[healthier_items['name']]

    # Sort and return top recommendations
    recommended_items = sim_scores.sort_values(ascending=False).iloc[:top_n]
    
    return recommended_items.index.tolist()