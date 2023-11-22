from flask import Flask, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from openfoodfacts_api import get_product_info
from ingredients_api import get_ingredient, add_ingredient
from openai_api import ChatGPT
import os
import re
import json


app = Flask(__name__)
app.secret_key = os.urandom(24)

class SearchField(FlaskForm):
    ingredients = StringField('Search', validators=[DataRequired()], render_kw={"placeholder": "Enter barcode here"})
    submit = SubmitField('Search')


def clean_up(response):
    response_list = response.split('\n')
    ingredients_list = []
    for item in response_list:
        if item:
            ingredient_info = item.strip('- ')
            ingredients_list.append(ingredient_info)
    return ingredients_list


@app.route('/', methods=['GET', 'POST'])
def home():
    chatgpt = ChatGPT()
    form = SearchField()
    
    # maybe have an if statement

    if form.validate_on_submit():
        barcode = form.ingredients.data
        ingredients = get_product_info(str(barcode))

        if 'product' in ingredients:
            product_info = ingredients['product']

            name = product_info.get('product_name', 'Sorry not name was found.')
            ingredients = product_info.get('ingredients_text_en', 'Sorry not ingredients where found.')
            
            # you might not need the code below
            def clean_ingredient(ingredient):
                # Remove parentheses and their contents
                ingredient = re.sub(r'\(.*?\)', '', ingredient)
                
                # Trim whitespace
                ingredient = ingredient.strip()
                
                # Remove trailing special characters
                ingredient = re.sub(r'[\*\)&]$', '', ingredient)
                
                # Convert to lowercase
                return ingredient.lower()

            def clean_ingredients(input_string):
                # Split the string by commas
                
                splitted_string = re.split(',|\.|:', input_string)
                print(splitted_string)
                # Clean each ingredient
                cleaned_ingredients = [clean_ingredient(ingredient) for ingredient in splitted_string if ingredient]
                
                # print(flattened_ingredients)
                return cleaned_ingredients

            array = clean_ingredients(ingredients)
            
            # refactor this code in the future
            # This is the final clean up of the string
            final_array = []
            for c in array:
                if re.search(r'[()\[\]0-9]', c):
                    print(f"1st from Inside-> {c}")
                    c = re.sub(r'[()\[\]0-9]', '', c)
                    print(f"2nd from inside-> {c}")
                    final_array.append(c)
                else:
                    final_array.append(c)
            print(final_array)
            # search the database for item
            ingredients_list = []
            for final_ingredient in final_array:
                
                single_ingredient = get_ingredient(final_ingredient)
                
                if single_ingredient != None:
                    print(f"IN DATABASE: {single_ingredient}")
                    ingredients_list.append(single_ingredient)
                else:
                    print(final_ingredient)
                    # search for the ingredient information with openai api
                    answer = chatgpt.get_response(final_ingredient)
                    arguments_str = answer.tool_calls[0].function.arguments
                    arguments = json.loads(arguments_str)
                    # turning them to title so that they are always title case in the database
                    arguments['name'] = arguments['name'].title()
                    print(f"Not in database: {arguments}")
                    # append the object to the list to display later on the front end
                    ingredients_list.append(arguments)
                    # add ingredients to database
                    add_ingredient(arguments)

            return render_template('index.html', form=form, name=name, ingredients_list=ingredients_list)
        else:
            return 'Sorry product not found.'

    return render_template('index.html', form=form)


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
