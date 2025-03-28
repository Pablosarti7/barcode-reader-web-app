# internal imports
from forms import LoginForm, RegistrationForm, SearchBarcode, SearchIngredient, EditProfile, ResetPasswordRequestForm, ResetPasswordForm
from utils import autosuggest, create_structure
from openfoodfacts_api import get_product_info
from ingredients_api import get_ingredient, add_ingredient
from products_api import add_product, get_specific_ingredient
from openai_sdk import json_formatter
from openai_structure_data import product_info_json
from food_recommender import recommend_healthier_food

# external imports
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort, session, json
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache  # type: ignore
from authlib.integrations.flask_client import OAuth  # type: ignore
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
import stripe
from flask_migrate import Migrate

# standard python module imports
import os
import secrets
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)


# SQLalchemy database configurations
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Ensures cookies are only sent over HTTPS
app.config['SESSION_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
# Prevents JavaScript access to cookies
app.config['SESSION_COOKIE_HTTPONLY'] = True
# OAuth configurations
app.config['GOOGLE_CLIENT_ID'] = os.environ.get("CLIENT_ID")

app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get("CLIENT_SECRET")
app.config['GOOGLE_DISCOVERY_URL'] = (
    'https://accounts.google.com/.well-known/openid-configuration'
)

# Mail SMTP configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("G_EMAIL")
app.config['MAIL_PASSWORD'] = os.environ.get("G_PASSWORD")

mail = Mail(app)

db = SQLAlchemy(app)

# Initializing Flask-Migrate for database tables modifications
migrate = Migrate(app, db)

# Initialize flask-migrate when needed
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# User loader function


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, user_id)


# Getting hold of the stripe secret key
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
    client_kwargs={
        'scope': 'openid email profile'
    }
)


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    email_confirmed = db.Column(db.Boolean, default=False)
    stripe_user_session_id = db.Column(db.String(100))
    customer_id = db.Column(db.String(100))
    invoice_id = db.Column(db.String(100))
    subscription_id = db.Column(db.String(100))

    def __repr__(self):
        return f'<User {self.email}>'


class ScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    item_barcode = db.Column(db.String(100), nullable=True)
    user = db.relationship(
        'Users', backref=db.backref('scan_history', lazy=True))


s = URLSafeTimedSerializer(app.secret_key)


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
        barcode = request.form.get('barcode') or form.ingredients.data

        # Send the barcode to the OpenFoodFacts API
        ingredients = get_product_info(str(barcode))

        # If there is a record for the barcode proceed
        if 'product' in ingredients:
            # Access the product key in ingredients to get the data needed
            product_info = ingredients['product']
            # Get necessary data
            nutriscore = product_info.get('nutriscore', {})

            name = product_info.get('product_name', 'Sorry no name was found.')
            ingredients_text = product_info.get(
                'ingredients_text_en', 'Sorry no ingredients were found.')

            boolean, product_data = get_specific_ingredient(name)

            if boolean:

                database_tasks = [get_ingredient(
                    ingredient) for ingredient in product_data]
                testing = recommend_healthier_food(name)
            else:

                list_of_objects = json_formatter(ingredients_text)

                for obj in list_of_objects:
                    obj['name'] = obj['name'].title()

                add_ingredient(list_of_objects)

                # adding the product to the product DB
                list_of_ingredients = [item['name']
                                       for item in list_of_objects]

                ingredients_string = ", ".join(list_of_ingredients)

                json_product = create_structure(
                    name, ingredients_string, barcode)

                product_information_json = product_info_json(json_product)

                add_product(product_information_json)

                database_tasks = [get_ingredient(
                    ingredient) for ingredient in list_of_ingredients]
                testing = recommend_healthier_food(name)

            # Only if the user is logged in save the product barcode in their account
            if current_user.is_authenticated:
                barcode_exists = db.session.query(
                    db.exists().where(
                        ScanHistory.user_id == current_user.id,
                        ScanHistory.item_barcode == barcode
                    )
                ).scalar()

                if not barcode_exists:
                    new_item = ScanHistory(
                        user_id=current_user.id,
                        item_name=name,
                        item_barcode=barcode,
                    )
                    db.session.add(new_item)
                    db.session.commit()

            return render_template('index.html', form=form, name=name, ingredients_list=database_tasks,
                                   nutriscore=nutriscore, logged_in=current_user.is_authenticated, testing=testing)
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


@app.route('/settings', methods=['GET', 'POST'])
def settings():

    subsection = request.args.get('section', 'main')
    action = request.form.get('action')

    # grabbing is_google from session to later check if user is a google login user
    google_account = session.get('is_google')

    form = EditProfile()
    
    # Setting variables to None so that no variables erros happen.
    users_name = None
    users_scan_history = []
    show_history_to_user = None
    if_subscribed_object = None
    
    if current_user.is_authenticated:
        # Getting users name and email from the current user session by flask
        users_name = current_user.name
        users_email = current_user.email

        # Initialize these variables with default values
        show_history_to_user = False
        if_subscribed_object = False
        
        # Only try to retrieve subscription if the user has a subscription_id
        if current_user.subscription_id:
            subscription_object = stripe.Subscription.retrieve(current_user.subscription_id)
            
            if subscription_object["items"]["data"][0]["price"]["lookup_key"] == 'big_monthly':
                show_history_to_user = True

                # Get all of the items under current users id only if the user is a premium subscriber.
                users_scan_history = ScanHistory.query.filter_by(
                user_id=current_user.id).all()

            elif subscription_object["items"]["data"][0]["price"]["lookup_key"] == 'small_monthly':
                show_history_to_user = False

            # User has a valid subscription
            if_subscribed_object = True


    if form.validate_on_submit():
        user = Users.query.filter_by(id=current_user.id).first()

        # If user click on update then perform this action
        if action == 'update':
            if google_account:
                user.name = form.name.data
                db.session.commit()
                return "Account Name Updated"

        # If user click on delete then perform this action
        elif action == 'delete':
            # db.session.delete(id)
            # db.session.commit()
            return "Account deleted successfully"
        else:
            return "Unknown action", 400

    return render_template('settings.html', subsection=subsection, logged_in=current_user.is_authenticated, scan_history=users_scan_history, users_name=users_name, form=form, show_scan_history=show_history_to_user, subscribed=if_subscribed_object)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():

        email = form.email.data
        password = form.password.data

        # Use ORM method for querying.
        user = Users.query.filter_by(email=email).first()

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

    return render_template("register.html", logged_in=current_user.is_authenticated)


@app.route('/callback')
def authorize():

    try:
        google_token = google.authorize_access_token()
        
        user_info = google.parse_id_token(google_token, nonce=session['nonce'])

        email = user_info['email']
        name = user_info['name']

        newest_user = Users.query.filter_by(email=email).first()
        
        if not newest_user:
            newest_user = Users(email=email,
                                name=name,
                                )
            db.session.add(newest_user)
            db.session.commit()

        login_user(newest_user)

        session.pop('nonce')  # Remove the nonce after successful use
        return redirect(url_for('settings'))
    except Exception as e:
        
        
        # Redirect to a custom error page
        return 'error_page'


@app.route('/google/login')
def googlelogin():
    
    try:
        nonce = secrets.token_urlsafe(16)
        session['nonce'] = nonce
        session['is_google'] = True
        
        redirect_uri = url_for('authorize', _external=True)
        
        return google.authorize_redirect(redirect_uri, nonce=nonce)
    except Exception as e:
        
        
        return 'error_page'


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/delete/<int:item_id>')
def delete(item_id):

    item = ScanHistory.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect("/settings?section=scan_history")


@app.route('/pricing')
def pricing():
    # Variable to None for declaration purposes.
    redirect_user_to_pay = None

    if current_user.is_authenticated:

        if current_user.subscription_id:

            subscription_object = stripe.Subscription.retrieve(current_user.subscription_id)
            
            if subscription_object["items"]["data"][0]["price"]["lookup_key"] == 'big_monthly':
                redirect_user_to_pay = True
                flash('You seem to already have a paid account or if you wish to switch subscriptions contact support.')
            elif subscription_object["items"]["data"][0]["price"]["lookup_key"] == 'small_monthly':
                redirect_user_to_pay = True
                flash('You seem to already have a paid account or if you wish to switch subscriptions contact support.')
            
    else:
        redirect_user_to_pay = False
        flash('You need to be logged in or create an account first.')
    
    return render_template('pricing.html', logged_in=current_user.is_authenticated, redirect_to_pay=redirect_user_to_pay)


@app.route('/success')
@login_required
def success():

    return render_template('success.html')


@app.route('/cancel')
@login_required
def cancel():

    return render_template('cancel.html')


YOUR_DOMAIN = 'http://127.0.0.1:5000'


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        prices = stripe.Price.list(
            lookup_keys=[request.form['lookup_key']],
            expand=['data.product']
        )

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': prices.data[0].id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=YOUR_DOMAIN +
            '/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=YOUR_DOMAIN + '/cancel',
        )

        return redirect(checkout_session.url, code=303)
    except Exception as e:
        print(e)
        return "Server error", 500


@app.route('/create-portal-session', methods=['POST'])
def customer_portal():
    # For demonstration purposes, we're using the Checkout session to retrieve the customer ID.
    # Typically this is stored alongside the authenticated user in your database.
    checkout_session_id = request.form.get('session_id')

    

    checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
    
    if current_user.is_authenticated:
        email = current_user.email

        # Storing the users stripe portal ID to be able to retrieve the session
        user_to_add_sessionid = Users.query.filter_by(email=email).first()
        if not user_to_add_sessionid.stripe_user_session_id:
            user_to_add_sessionid.customer_id = checkout_session["customer"]
            user_to_add_sessionid.stripe_user_session_id = checkout_session["id"]
            user_to_add_sessionid.invoice_id = checkout_session["invoice"]
            user_to_add_sessionid.subscription_id = checkout_session["subscription"]
            db.session.commit()
    
    # This is the URL to which the customer will be redirected after they're
    # done managing their billing with the portal.
    return_url = "https://barcode-reader-web-app.onrender.com/settings"

    portalSession = stripe.billing_portal.Session.create(
        customer=checkout_session.customer,
        return_url=return_url,
    )
    return redirect(portalSession.url, code=303)


@app.route('/webhook', methods=['POST'])
def webhook_received():
    # Replace this endpoint secret with your endpoint's unique secret
    # If you are testing with the CLI, find the secret by running 'stripe listen'
    # If you are using an endpoint defined with the API or dashboard, look in your webhook settings
    # at https://dashboard.stripe.com/webhooks
    webhook_secret = 'whsec_4cOPjgclgjZ4tq8kaB6Cwwre9hPTQXCI'
    request_data = json.loads(request.data)

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret)
            data = event['data']
        except Exception as e:
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event['type']
    else:
        data = request_data['data']
        event_type = request_data['type']
    data_object = data['object']

    print('event ' + event_type)

    if event_type == 'checkout.session.completed':
        print('🔔 Payment succeeded!')
    elif event_type == 'customer.subscription.trial_will_end':
        print('Subscription trial will end')
    elif event_type == 'customer.subscription.created':
        print('Subscription created %s', event.id)
    elif event_type == 'customer.subscription.updated':
        print('Subscription created %s', event.id)
    elif event_type == 'customer.subscription.deleted':
        # handle subscription canceled automatically based
        # upon your subscription settings. Or if the user cancels it.
        print('Subscription canceled: %s', event.id)
    elif event_type == 'entitlements.active_entitlement_summary.updated':
        # handle active entitlement summary updated
        print('Active entitlement summary updated: %s', event.id)

    return jsonify({'status': 'success'})


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == "__main__":
    app.run(debug=True)
