from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from openfoodfacts_api import get_product_info
from ingredients_api import get_ingredient, add_ingredient
from openai_api import get_response
import os
import re


app = Flask(__name__)
app.secret_key = os.urandom(24)


class SearchField(FlaskForm):
    ingredients = StringField('Search', validators=[DataRequired()], render_kw={
                              "placeholder": "Enter barcode here"})
    submit = SubmitField('Search')


@app.route('/', methods=['GET', 'POST'])
def home():
    form = SearchField()

    if request.method == 'POST':
        # Check for barcode in the form data
        barcode = request.form.get('barcode')

        if not barcode:
            # If no barcode is found in the form data, fall back to the SearchField form
            barcode = form.ingredients.data
        
        ingredients = get_product_info(str(barcode))

        if 'product' in ingredients:
            product_info = ingredients['product']

            name = product_info.get('product_name', 'Sorry no name was found.')
            ingredients = product_info.get(
                'ingredients_text_en', 'Sorry no ingredients where found.')

            def clean_ingredient(ingredient):
                # Remove parentheses and their contents
                ingredient = re.sub(r'\(.*?\)', '', ingredient)
                # Trim whitespace
                ingredient = ingredient.strip()
                # Remove trailing special characters
                ingredient = re.sub(r'[()\[\]0-9]', '', ingredient)

                return ingredient.lower()

            def clean_ingredients(input_string):
                # Splitting the words by the chosen characters
                split_string = re.split(',|\.|:', input_string)
                # Clean each ingredient
                clean_ingredients = [clean_ingredient(ingredient) for ingredient in split_string if ingredient]
                # Getting rid of the list item with % signs
                filtered_list = [item for item in clean_ingredients if '%' not in item and 'contains' not in item]

                return filtered_list

            final_list = clean_ingredients(ingredients)
            
            openai_list = []
            ingredients_list = []

            for final_ingredient in final_list:
                # Get the ingredient from your database
                single_ingredient = get_ingredient(final_ingredient)
                # If we get none instead of an object it means we we to search it because is not in the database
                if single_ingredient != None:
                    ingredients_list.append(single_ingredient)
                else:
                    openai_list.append(final_ingredient)

            response_list = []
            # If list is not empty proceed (to save some time when the list is empty)
            if openai_list:
                response = get_response(openai_list)
                for object in response:
                    object['name'] = object['name'].title()
                    response_list.append(object)

                add_ingredient(response_list)

            complete_list = ingredients_list + response_list
            
            return render_template('index.html', form=form, name=name, ingredients_list=complete_list)
        else:
            return 'Sorry product not found.'

    return render_template('index.html', form=form)


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
