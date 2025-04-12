from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from main import google, db
from .. import google, db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    return render_template('login.html', logged_in=current_user.is_authenticated)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():

    return render_template("register.html", logged_in=current_user.is_authenticated)

@auth_bp.route('/callback')
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


@auth_bp.route('/google/login')
def googlelogin():
    
    try:
        nonce = secrets.token_urlsafe(16)
        session['nonce'] = nonce
        session['is_google'] = True
        
        redirect_uri = url_for('authorize', _external=True)
        
        return google.authorize_redirect(redirect_uri, nonce=nonce)
    except Exception as e:
        
        
        return 'error_page'


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))