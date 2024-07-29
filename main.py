from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, validators
from wtforms.validators import DataRequired, EqualTo
from openfoodfacts_api import get_product_info
from ingredients_api import get_all_ingredients, get_ingredient, add_ingredient
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from openai_api import get_response
from flask_caching import Cache
from thefuzz import process
import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Ensures cookies are only sent over HTTPS
app.config['SESSION_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
# Prevents JavaScript access to cookies
app.config['SESSION_COOKIE_HTTPONLY'] = True

# dont need this anymore
engine = create_engine(os.environ.get("DATABASE_URL"), pool_pre_ping=True)

# dont need this anymore
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# dont need this anymore
db = SQLAlchemy(app, session_options={"bind": engine})

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, user_id)

# your database


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class ScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    item_barcode = db.Column(db.String(100), nullable=True)

    user = db.relationship(
        'Users', backref=db.backref('scan_history', lazy=True))

# dont need this anymore


@app.teardown_appcontext
def shutdown_session(exception=None):
    Session.remove()


# with app.app_context():
#     db.create_all()

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(
    ), validators.Email()], render_kw={"placeholder": "Enter Email"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={
                             "placeholder": "Enter Password"})
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()], render_kw={
                       "placeholder": "Enter Name"})
    email = StringField('Email', validators=[DataRequired(
    ), validators.Email()], render_kw={"placeholder": "Enter Email"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={
                             "placeholder": "Enter Password"})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(
    ), EqualTo('password')], render_kw={"placeholder": "Re-enter Password"})
    submit = SubmitField('Register')

# your flask forms


class SearchBarcode(FlaskForm):
    ingredients = StringField('Search', validators=[DataRequired()], render_kw={
                              "placeholder": "Enter barcode here"})
    submit = SubmitField('Search')


class SearchIngredient(FlaskForm):
    ingredient = StringField('Search', validators=[DataRequired()], render_kw={
        "placeholder": "Enter ingredient here"})
    submit = SubmitField('Search')


def autosuggest(prefix):
    ingredients = get_all_ingredients()
    # you can add code here that will specify not to append matches with less then 70 percent score if the words are not relevant
    if prefix:
        best_match = process.extract(prefix, ingredients)

        matches_list = [t[0] for t in best_match]

        return matches_list

    return ''


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
    clean_ingredients = [clean_ingredient(
        ingredient) for ingredient in split_string if ingredient]
    # Getting rid of the list item with % signs
    filtered_list = [
        item for item in clean_ingredients if '%' not in item and 'contains' not in item]

    return filtered_list


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/', methods=['GET', 'POST'])
def home():
    form = SearchBarcode()

    if request.method == 'POST':
        # Check for barcode in the form data
        barcode = request.form.get('barcode')

        if not barcode:
            # If no barcode is found in the form data, fall back to the SearchBarcode form
            barcode = form.ingredients.data

        ingredients = get_product_info(str(barcode))

        if 'product' in ingredients:
            # accessing the key called product
            product_info = ingredients['product']

            # nutriscore data extraction from the api
            nutriscore = product_info.get('nutriscore', {})

            # original data extraction name and ingredients
            name = product_info.get('product_name', 'Sorry no name was found.')
            ingredients = product_info.get(
                'ingredients_text_en', 'Sorry no ingredients where found.')

            final_list = clean_ingredients(ingredients)

            # Ingredients that we in out database go in one list and non existing one ask chat gpt
            openai_list, database_list = [], []

            for final_ingredient in final_list:
                # Get the ingredient from your database
                single_ingredient = get_ingredient(final_ingredient)
                # If we get none instead of an object it means we need to search it because is not in the database
                if single_ingredient != None:
                    database_list.append(single_ingredient)
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

            complete_list = database_list + response_list

            if current_user.is_authenticated:
                # access the scan history to gather all the scanned codes
                user = db.session.execute(db.select(ScanHistory).filter_by(
                    user_id=current_user.id)).scalars()
                # TODO use this below instead
                oneee = db.session.execute(
                    db.select(ScanHistory).filter_by(user_id=current_user.id)).first()

                # for itemss in oneee:
                #     print(itemss.item_barcode)
                for items in user:
                    if barcode in items.item_barcode:
                        print("YES its there.")
                        break
                    else:  # add only if the item is not in the DB
                        new_item = ScanHistory(
                            user_id=current_user.id,
                            item_name=name,
                            item_barcode=barcode,
                        )

                        db.session.add(new_item)
                        db.session.commit()
                        break

            return render_template('index.html', form=form, name=name, ingredients_list=complete_list, nutriscore=nutriscore, logged_in=current_user.is_authenticated)
        else:
            flash('Sorry product key not found in data.')
            return redirect(url_for('home'))

    return render_template('index.html', form=form, logged_in=current_user.is_authenticated)

# search page is where users can search for specific ingredients


@app.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchIngredient()

    if form.validate_on_submit():

        searched_ingredient = form.ingredient.data
        ingredient_from_db = get_ingredient(searched_ingredient)
        return render_template('search.html', form=form, ingredient_info=ingredient_from_db)

    return render_template('search.html', form=form, logged_in=current_user.is_authenticated)

# talking to the javascript code sending requests to this url


@app.route('/search-suggestions')
@cache.cached(timeout=50, query_string=True)
def search_suggestions():

    query = request.args['q'].lower()

    prefix = autosuggest(query)

    return jsonify(suggestions=prefix)


@app.route('/about')
def about():
    return render_template('about.html', logged_in=current_user.is_authenticated)


@app.route('/settings')
def settings():
    subsection = request.args.get('section', 'main')
    if current_user.is_authenticated:
        users_scan_history = ScanHistory.query.filter_by(
            user_id=current_user.id).all()
    else:
        users_scan_history = None

    return render_template('settings.html', subsection=subsection, logged_in=current_user.is_authenticated, scan_history=users_scan_history)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    # add database

    if form.validate_on_submit():

        email = form.email.data
        password = form.password.data

        result = db.session.execute(
            db.select(Users).where(Users.email == email))

        user = result.scalar()

        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('settings'))

    return render_template('login.html', form=form, logged_in=current_user.is_authenticated)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():

        if Users.query.filter_by(email=form.email.data).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = Users(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )

        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)

        return redirect(url_for("settings"))

    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/test')
def test():
    form = SearchBarcode()
    return render_template('test.html', form=form)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
