# Internal imports
from forms.forms import SearchBarcode, SearchIngredient, EditProfile
from utils.utils import autosuggest, create_structure
from apis.openfoodfacts_api import get_product_info
from apis.ingredients_api import get_ingredient, add_ingredient
from apis.products_api import add_product, get_specific_ingredient
from sdks.openai_sdk import json_formatter
from sdks.openai_structure_data import product_info_json
from models.models import db, Users, ScanHistory

# External imports
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort, session
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
from flask_caching import Cache  # type: ignore
from authlib.integrations.flask_client import OAuth  # type: ignore
from flask_mail import Mail
import stripe
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from config import configure_app
import click

# Standard python module imports
import os
import secrets
from functools import wraps

load_dotenv()

app = Flask(__name__)
configure_app(app)
csrf = CSRFProtect(app)

# OAuth configurations
app.config['GOOGLE_CLIENT_ID'] = os.environ.get("CLIENT_ID")
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get("CLIENT_SECRET")
app.config['GOOGLE_DISCOVERY_URL'] = ('https://accounts.google.com/.well-known/openid-configuration')

# Mail SMTP configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("G_EMAIL")
app.config['MAIL_PASSWORD'] = os.environ.get("G_PASSWORD")


# Database
db.init_app(app)
# Google Oauth
oauth = OAuth(app)
# Mail SMTP
mail = Mail(app)
# Initializing Flask-Migrate for database tables modifications
migrate = Migrate(app, db)


@app.cli.command('init-db')
def init_db():
    """Create tables in the local development database only."""
    if not app.config['DEVELOPMENT']:
        raise click.ClickException('init-db is for local development only.')
    db.create_all()
    click.echo('Local database tables created.')


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


google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
    client_kwargs={
        'scope': 'openid email profile'
    }
)



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
        barcode = (request.form.get('barcode') or form.ingredients.data or '').strip()
        if not barcode.isascii() or not barcode.isdigit() or len(barcode) not in {8, 12, 13, 14}:
            abort(400, description='Enter a barcode with 8, 12, 13, or 14 digits.')

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
                # testing = recommend_healthier_food(name)
            else:
                if not os.environ.get('OPENAI_API_KEY'):
                    abort(503, description='AI ingredient analysis is not configured yet. See README.md.')
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
                # testing = recommend_healthier_food(name)

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
                                   nutriscore=nutriscore, logged_in=current_user.is_authenticated)
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

    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify(suggestions=[])

    prefix = autosuggest(query)

    return jsonify(suggestions=prefix)


@app.route('/about')
def about():
    return render_template('about.html', logged_in=current_user.is_authenticated)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
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
            subscription_object = active_subscription(current_user)
            
            if subscription_object and subscription_object["items"]["data"][0]["price"]["lookup_key"] == 'big_monthly':
                show_history_to_user = True

                # Get all of the items under current users id only if the user is a premium subscriber.
                users_scan_history = ScanHistory.query.filter_by(
                user_id=current_user.id).all()

            elif subscription_object and subscription_object["items"]["data"][0]["price"]["lookup_key"] == 'small_monthly':
                show_history_to_user = False

            # User has a valid subscription
            if_subscribed_object = bool(subscription_object)


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
            return 'Account deletion is not available yet. Please contact support.', 501
        else:
            return "Unknown action", 400

    return render_template('settings.html', subsection=subsection, logged_in=current_user.is_authenticated, scan_history=users_scan_history, users_name=users_name, form=form, show_scan_history=show_history_to_user, subscribed=if_subscribed_object)


@app.route('/login', methods=['GET', 'POST'])
def login():

    return render_template('login.html', logged_in=current_user.is_authenticated)


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
    if not app.config['GOOGLE_CLIENT_ID'] or not app.config['GOOGLE_CLIENT_SECRET']:
        flash('Google login is not configured in this environment yet. See README.md.')
        return redirect(url_for('login'))
    
    try:
        nonce = secrets.token_urlsafe(16)
        session['nonce'] = nonce
        session['is_google'] = True
        
        redirect_uri = url_for('authorize', _external=True)
        
        return google.authorize_redirect(redirect_uri, nonce=nonce)
    except Exception as e:
        
        
        return 'error_page'


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/delete/<int:item_id>', methods=['POST'])
@login_required
def delete(item_id):

    item = ScanHistory.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return redirect("/settings?section=scan_history")


def active_subscription(user):
    """Grant access only while Stripe reports an active subscription."""
    if not user.subscription_id:
        return None
    try:
        subscription = stripe.Subscription.retrieve(user.subscription_id)
    except stripe.StripeError:
        app.logger.exception('Unable to check subscription status')
        abort(503, description='Billing is temporarily unavailable. Please try again later.')
    return subscription if subscription.get('status') in {'active', 'trialing'} else None


@app.route('/pricing')
def pricing():
    subscribed = current_user.is_authenticated and bool(active_subscription(current_user))
    return render_template('pricing.html', logged_in=current_user.is_authenticated,
                           redirect_to_pay=subscribed)


@app.route('/success')
@login_required
def success():
    # A browser redirect is not proof of payment. The webhook updates the account.
    return render_template('success.html')


@app.route('/cancel')
@login_required
def cancel():
    return render_template('cancel.html')


def require_billing():
    if not stripe.api_key:
        abort(503, description='Billing is not configured in this environment.')


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    require_billing()
    lookup_key = request.form.get('lookup_key')
    if lookup_key not in {'small_monthly', 'big_monthly'}:
        abort(400, description='Choose a valid subscription plan.')
    if active_subscription(current_user):
        abort(409, description='Manage your existing subscription from Settings.')
    try:
        prices = stripe.Price.list(lookup_keys=[lookup_key], expand=['data.product'])
        if not prices.data:
            abort(400, description='This plan is not available.')
        if not current_user.customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'user_id': str(current_user.id)},
                idempotency_key=f'ingredient-advisor-customer-{current_user.id}',
            )
            current_user.customer_id = customer.id
            db.session.commit()
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.customer_id,
            client_reference_id=str(current_user.id),
            metadata={'user_id': str(current_user.id)},
            subscription_data={'metadata': {'user_id': str(current_user.id)}},
            line_items=[{'price': prices.data[0].id, 'quantity': 1}],
            mode='subscription',
            success_url=app.config['PUBLIC_BASE_URL'] + '/success',
            cancel_url=app.config['PUBLIC_BASE_URL'] + '/cancel',
        )
        return redirect(checkout_session.url, code=303)
    except stripe.StripeError:
        app.logger.exception('Unable to create checkout')
        abort(503, description='Billing is temporarily unavailable. Please try again later.')


@app.route('/create-portal-session', methods=['POST'])
@login_required
def customer_portal():
    require_billing()
    if not current_user.customer_id:
        abort(409, description='No billing account is linked. Please contact support.')
    try:
        portal = stripe.billing_portal.Session.create(
            customer=current_user.customer_id,
            return_url=app.config['PUBLIC_BASE_URL'] + '/settings',
        )
        return redirect(portal.url, code=303)
    except stripe.StripeError:
        app.logger.exception('Unable to create billing portal')
        abort(503, description='Billing is temporarily unavailable. Please try again later.')


@app.route('/webhook', methods=['POST'])
@csrf.exempt
def webhook_received():
    webhook_secret = app.config['STRIPE_WEBHOOK_SECRET']
    if not webhook_secret:
        abort(503, description='Stripe webhook is not configured.')
    try:
        event = stripe.Webhook.construct_event(
            payload=request.get_data(),
            sig_header=request.headers.get('Stripe-Signature'),
            secret=webhook_secret,
        )
    except (ValueError, stripe.SignatureVerificationError):
        return jsonify(error='Invalid webhook signature or payload.'), 400

    event_type = event['type']
    obj = event['data']['object']
    handled_events = {
        'checkout.session.completed', 'customer.subscription.created',
        'customer.subscription.updated', 'customer.subscription.deleted',
    }
    if event_type not in handled_events:
        return jsonify(status='success')
    # The customer association was stored on the server before checkout.
    user = Users.query.filter_by(customer_id=obj.get('customer')).first() if obj.get('customer') else None
    if not user:
        return jsonify(status='ignored')
    if event_type == 'checkout.session.completed':
        if (obj.get('mode') != 'subscription'
                or obj.get('client_reference_id') != str(user.id)
                or not obj.get('subscription')):
            return jsonify(status='ignored')
        subscription_id = obj['subscription']
    else:
        subscription_id = obj['id']
        # An old subscription event must not overwrite a newer subscription.
        if user.subscription_id and user.subscription_id != subscription_id:
            return jsonify(status='ignored')

    try:
        # Fetch current state so duplicates and delayed events cannot restore stale access.
        subscription = stripe.Subscription.retrieve(subscription_id)
        if user.subscription_id and user.subscription_id != subscription_id:
            existing = stripe.Subscription.retrieve(user.subscription_id)
            if (existing.get('status') in {'active', 'trialing'}
                    or subscription.get('status') not in {'active', 'trialing'}):
                return jsonify(status='ignored')
    except stripe.StripeError:
        app.logger.exception('Unable to synchronize subscription')
        return jsonify(error='Unable to synchronize subscription.'), 503
    if subscription.get('customer') != user.customer_id:
        return jsonify(status='ignored')
    user.subscription_id = subscription_id
    user.subscribed = subscription.get('status') in {'active', 'trialing'}
    db.session.commit()
    return jsonify(status='success')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == "__main__":
    app.run(debug=app.config['DEVELOPMENT'])
