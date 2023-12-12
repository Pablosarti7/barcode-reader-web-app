from openai import OpenAI
import os
import json


client = OpenAI(
    api_key=os.environ.get('API_KEY'),
)


def get_response(list_of_ingredients):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "set_ingredients",
                "description": "Use this function to structure the list of ingredients for a database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ingredients": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "rating": {"type": "string"},
                                },
                                "required": ["name", "description"],
                            }
                        },
                    },
                    "required": ["ingredients"],
                },
            },
        }
    ]

    messages = [
        {"role": "system", "content": "You are a knowledgeable nutritionist."},
        {"role": "user", "content": f"Please analyze each ingredient in this list individually {list_of_ingredients}. For each ingredient, \
                in a few words, provide information about its impact on health and a rating between 'healthy' or 'unhealthy'."}
    ]

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        temperature=0.2,
        tools=tools,
        tool_choice={"type": "function",
                        "function": {"name": "set_ingredients"}},
        messages=messages,
    )
    response = completion.choices[0].message
    data = response.tool_calls[0].function.arguments
    parsed_data = json.loads(data)
    ingredients = parsed_data['ingredients']

    return ingredients
