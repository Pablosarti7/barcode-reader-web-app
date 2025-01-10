from openai import OpenAI
import os
from pydantic import BaseModel, Field
from typing import List
import json

openai = OpenAI(api_key=os.environ.get('API_KEY'))

class ProductInfo(BaseModel):
    name: str
    ingredients: str
    category: str = Field(description="The category for the current food product. Please make it singular, e.g., 'snack' instead of 'snacks' and capitalize every time.")

class SetProductRequest(BaseModel):
    information: ProductInfo = Field(description="Return the product information with the added category and in a json like format.")

def product_info_json(ingredients_string):
    # Making the completion call
    completion = openai.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": "You are a structure output helper."},
            {"role": "user", "content": f"Can you add a category to the following product: {ingredients_string}"}
        ],
        response_format=SetProductRequest
    )

    # Accessing the content of the response
    output_text = completion.choices[0].message

    if output_text.refusal:
        return output_text.refusal
    else:
        # Directly parse the JSON content without re-encoding it
        data = json.loads(output_text.content)

        # Access the list of dictionaries
        information = data["information"]

        # Print the result
        return json.dumps(information)

