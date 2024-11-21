#internal imports
from forms import LoginForm, RegistrationForm, SearchBarcode, SearchIngredient, EditProfile, ResetPasswordRequestForm, ResetPasswordForm
from utils import autosuggest, clean_ingredients, create_structure
from openfoodfacts_api import get_product_info
from ingredients_api import get_ingredient, add_ingredient
from openai_api import get_response
from products_api import get_all_products, add_product

# external imports
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort, session
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache  # type: ignore
from authlib.integrations.flask_client import OAuth  # type: ignore
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message

# standard python module
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

# Initialize flask-migrate when needed

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, user_id)


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
            
            final_list = clean_ingredients(ingredients_text)
            ingredients_string = ", ".join(final_list)

            # Collect the name/ingredients and convert to json structure for the DB
            json_product = create_structure(name, ingredients_string)
            
            # If the product doesn't exist in the DB add it
            add_product(json_product)
            
            database_tasks = [get_ingredient(ingredient)
                              for ingredient in final_list]
            
            database_list = [task for task in database_tasks]
            
            openai_list = [ingredient for ingredient, result in zip(
                final_list, database_list) if result is None]

            if openai_list:
                response = get_response(openai_list)
                for obj in response:
                    obj['name'] = obj['name'].title()
                database_list.extend(response)
                add_ingredient(response)
            
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

            return render_template('index.html', form=form, name=name, ingredients_list=database_list,
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

    query = request.args['q'].lower()

    prefix = autosuggest(query)

    return jsonify(suggestions=prefix)


@app.route('/about')
def about():
    return render_template('about.html', logged_in=current_user.is_authenticated)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if current_user.is_authenticated:
        if not current_user.email_confirmed:
            flash('Please confirm your email address to access settings.', 'warning')
            return redirect(url_for('unconfirmed'))

    subsection = request.args.get('section', 'main')
    action = request.form.get('action')
    users_email = None  # why is this bugging

    google_account = session.get('is_google')

    form = EditProfile()

    if current_user.is_authenticated:
        users_name = current_user.name
        users_email = current_user.email
        # Get all of the items under current users id
        users_scan_history = ScanHistory.query.filter_by(
            user_id=current_user.id).all()
    else:
        users_name = None
        users_scan_history = None

    if form.validate_on_submit():
        user = Users.query.filter_by(id=current_user.id).first()

        # If user click on update then perform this action
        if action == 'update':
            # the thing is that if you add email to the first one that defeats the purpose of
            # checking the user because you are changing the user
            if google_account:
                user.name = form.name.data
                db.session.commit()
                return "Account Name Updated"
            else:
                user.name = form.name.data
                user.email = form.email.data
                db.session.commit()
                return "Account Name and Email Updated"

        # If user click on delete then perform this action
        elif action == 'delete':
            # db.session.delete(id)
            # db.session.commit()
            return "Account deleted successfully"
        else:
            return "Unknown action", 400

    return render_template('settings.html', subsection=subsection, logged_in=current_user.is_authenticated, scan_history=users_scan_history, users_name=users_name, form=form, users_email=users_email)

@app.route('/unconfirmed')
def unconfirmed():
    if current_user.is_authenticated and current_user.email_confirmed:
        return redirect(url_for('settings'))

    flash('Please confirm your account!', 'warning')
    return render_template('unconfirmed.html')

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


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    
    form = ResetPasswordRequestForm()
    
    if form.validate_on_submit():
        
        user = Users.query.filter_by(email=form.email.data).first()
        
        if user:
            token = s.dumps(user.email, salt='password-reset-salt')
            
            msg = Message('Password Reset Request',
                        sender=os.environ.get("G_EMAIL"),
                        recipients=[user.email])
            msg.body = f"Click the link below to reset your password:\n\n{url_for('reset_password', token=token, _external=True)}"
            mail.send(msg)

            # Send email to user with reset link, e.g., url_for('reset_password', token=token, _external=True)
        flash("Check your email for the instructions to reset your password.")
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=1800)  # Link valid for 1 hour
    except:
        flash("The reset link is invalid or has expired.")
        return redirect(url_for('reset_password_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=email).first()
        if user:
            new_hashed_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256',
                salt_length=8
            )
            user.password = new_hashed_password
            db.session.commit()
            flash("Your password has been updated.")
            return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    # helper function to send email
    def send_email(to, subject, body):
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)

    if form.validate_on_submit():
        if Users.query.filter_by(email=form.email.data).first():
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
            email_confirmed=False  # Add a field in your database for email confirmation status
        )

        db.session.add(new_user)
        db.session.commit()

        # Generate confirmation token
        token = s.dumps(new_user.email, salt='email-confirmation')

        # Send confirmation email
        confirm_url = url_for('confirm_email', token=token, _external=True)
        subject = "Please confirm your email"
        body = f"Welcome! Please confirm your email by clicking on the link: {confirm_url}"
        send_email(new_user.email, subject, body)

        flash('A confirmation email has been sent to your email address. Please confirm your email to complete registration.', 'info')
        return redirect(url_for('login'))

    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        # Verify the token within 30 mins (seconds)
        email = s.loads(token, salt='email-confirmation', max_age=1800)
    except Exception:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('register'))
    
    user = Users.query.filter_by(email=email).first()
    if user is None:
        flash('Invalid confirmation request.', 'danger')
        return redirect(url_for('register'))

    if user.email_confirmed:
        flash('Account already confirmed. Please log in.', 'success')
    else:
        user.email_confirmed = True
        db.session.commit()
        flash('You have confirmed your email. Thanks!', 'success')

    return redirect(url_for('login'))



@app.route('/callback')
def authorize():
    
    try:
        token = google.authorize_access_token()
        
        user_info = google.parse_id_token(token, nonce=session['nonce'])

        email = user_info['email']
        name = user_info['name']

        user = Users.query.filter_by(email=email).first()

        if not user:
            user = Users(email=email,
                         name=name,
                         password=None,
                         )
            db.session.add(user)
            db.session.commit()

        login_user(user)

        session.pop('nonce')  # Remove the nonce after successful use
        return redirect(url_for('settings'))
    except Exception as e:
        flash("Authorization failed. Please try again or contact support if the problem persists.")
        # Redirect to a custom error page
        return render_template('error_page')


@app.route('/google/login')
def googlelogin():
    
    try:
        nonce = secrets.token_urlsafe(16)
        session['nonce'] = nonce
        session['is_google'] = True
        
        redirect_uri = url_for('authorize', _external=True)
        return google.authorize_redirect(redirect_uri, nonce=nonce)
    except Exception as e:
        flash("Failed to initiate Google login. Please try again later.")
        return render_template('error_page')


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


@app.route('/test')
def test():
    return render_template('test.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
