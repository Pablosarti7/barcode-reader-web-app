from openai import OpenAI
import os
from pydantic import BaseModel, Field
from typing import List
import json


openai = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

class Ingredient(BaseModel):
    name: str = Field(description="This is the name of the ingredient.")
    description: str = Field(description="Short description of the ingredient, e.g., 'synthetic dye derived from petroleum' or 'gut-disrupting artificial sweetener'.")
    rating: str = Field(description="Either 'healthy', 'neutral', or 'unhealthy' rating based on clean eating like avoiding processed foods, hormone-disrupting ingredients, endocrine disruptor ingredients, and gut-disrupting ingredients.")

class SetIngredientsRequest(BaseModel):
    ingredients: List[Ingredient] = Field(description="A list of ingredients, each represented with name, description, and rating. If not an ingredient don't return anything.")

def json_formatter(ingredients_string):
    # Making the completion call
    completion = openai.beta.chat.completions.parse(
        model="gpt-4.1-mini-2025-04-14",
        messages=[
            {"role": "system", "content": "Act like you are Bobby Parrish or Dr. Eric Berg."},
            {"role": "user", "content": f"Analyze the ingredients and return a JSON list with each ingredient details (name, description, and rating). The focus here is to find the processed ingredients, hormone-disrupting ingredients, endocrine disrupting ingredients, gut-disrupting ingredients, etc. Ingredients: {ingredients_string}"}
        ],
        response_format=SetIngredientsRequest
    )

    # Accessing the content of the response
    output_text = completion.choices[0].message

    if output_text.refusal:
        return output_text.refusal
    else:
        # Directly parse the JSON content without re-encoding it
        data = json.loads(output_text.content)

        # Access the list of dictionaries
        ingredients_list = data["ingredients"]

        return ingredients_list

