from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ.get('API_KEY'),
)


class ChatGPT:

    def __init__(self) -> None:
        pass

    def get_response(self, ingredient):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "set_ingredients",
                    "description": "Use this function to structure the ingredient for a database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
            }
        ]

        messages = [
            {"role": "system", "content": "You are a knowledgeable nutritionist."},
            {"role": "user", "content": f"For this food ingredient '{ingredient}' provide information about what it is and its impact on health."}
        ]

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            temperature=0.1,
            tools=tools,
            tool_choice={"type": "function",
                         "function": {"name": "set_ingredients"}},
            messages=messages,
        )
        response = completion.choices[0].message

        return response
    