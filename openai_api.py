from openai import OpenAI
import os

client = OpenAI(
    api_key= os.environ.get('API_KEY'),
)


class ChatGPT:

    def __init__(self) -> None:
        pass

    def get_response(self, list_of_ingredients):
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a knowledgeable nutritionist."},
                {"role": "user", "content": f"What can you tell me about ingredient in this list, what are they and what is the impact on my health. {list_of_ingredients}"}
            ]
        )
        response = completion.choices[0].message.content

        return response