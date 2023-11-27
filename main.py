from flask import Flask, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from openfoodfacts_api import get_product_info
from ingredients_api import get_ingredient, add_ingredient
from openai_api import ChatGPT
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
    chatgpt = ChatGPT()
    form = SearchField()

    if form.validate_on_submit():
        barcode = form.ingredients.data
        ingredients = get_product_info(str(barcode))

        if 'product' in ingredients:
            product_info = ingredients['product']

            name = product_info.get('product_name', 'Sorry no name was found.')
            ingredients = product_info.get(
                'ingredients_text_en', 'Sorry no ingredients where found.')

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

                splitted_string = re.split(',|\.|:', input_string)

                # Clean each ingredient
                cleaned_ingredients = [clean_ingredient(
                    ingredient) for ingredient in splitted_string if ingredient]

                return cleaned_ingredients

            array = clean_ingredients(ingredients)

            # refactor this code in the future
            # This is the final clean up of the string
            final_list = []
            for c in array:
                if re.search(r'[()\[\]0-9]', c):

                    c = re.sub(r'[()\[\]0-9]', '', c)
                    
                    final_list.append(c)
                else:
                    final_list.append(c)

            openai_list = []
            ingredients_list = []
            for final_ingredient in final_list:
                # get the ingredient from your database
                single_ingredient = get_ingredient(final_ingredient)

                # if we get none instead of an object it means we we to search it because is not in the database
                if single_ingredient != None:
                    print(single_ingredient)
                    ingredients_list.append(single_ingredient)
                else:
                    print(single_ingredient)
                    openai_list.append(final_ingredient)

            response_list = []
            # if list is not empty
            # have a flask loading message here so that if it happens then users will know 
            if openai_list:
                response = chatgpt.get_response(openai_list)
                
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
