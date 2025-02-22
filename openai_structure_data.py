from openai import OpenAI
import os
from pydantic import BaseModel, Field
from typing import List
import json

openai = OpenAI(api_key=os.environ.get('API_KEY'))

class ProductInfo(BaseModel):
    name: str
    ingredients: str
    category: str = Field(description="The category for the current food product. Be very specific. Please make it singular, e.g., 'snack' instead of 'snacks'.")
    barcode: str


def product_info_json(ingredients_string):
    # Making the completion call
    completion = openai.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": "You are a structure output helper."},
            {"role": "user", "content": f"Can you add a category to the following product: {ingredients_string}"}
        ],
        response_format=ProductInfo
    )

    # Accessing the content of the response
    output_text = completion.choices[0].message

    if output_text.refusal:
        return output_text.refusal
    else:        

        # Print the result
        return output_text.content

