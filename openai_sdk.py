from openai import OpenAI
import os
from pydantic import BaseModel, Field
from typing import List
import json

openai = OpenAI(api_key=os.environ.get('API_KEY'))

class Ingredient(BaseModel):
    name: str
    description: str = Field(description="Small description of the ingredient eg. synthetic dye derived from petroleum or artificial sweetener gut disruptor and may act as a endocrine disruptor.")
    rating: str = Field(description="Either 'Healthy' or 'Unhealthy' rating based on clean eating like avoiding processed foods, hormone disrupting ingredients, and gut disrupting ingredients.")

class SetIngredientsRequest(BaseModel):
    ingredients: List[Ingredient]

def jsonFormater(list_of_ingredients):

    # Making the completion call
    completion = openai.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": "Act like you are Bobby Parrish."},
            {"role": "user", "content": f"Please analyze each ingredient in this list individually {list_of_ingredients}."}
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

        # Print the result
        return ingredients_list




