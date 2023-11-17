from flask import Flask, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from openfoodfacts_api import get_product_info
from openai_api import ChatGPT
import os


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
        ingredients = get_product_info(barcode)
        name = ingredients['product']['product_name']
        ingredients = ingredients['product']['ingredients_text_en']
        
        
        response = chatgpt.get_response(ingredients)
        
        ingredients_list = clean_up(response)

        return render_template('index.html', form=form, name=name, ingredients_list=ingredients_list)

    return render_template('index.html', form=form)


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
