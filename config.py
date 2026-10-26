"""Environment-based settings shared by the web server and Flask CLI."""
import os


def configure_app(app):
    development = os.environ.get('APP_ENV') == 'development'
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise RuntimeError('Set SECRET_KEY in your environment or .env file. See README.md.')
    database_url = os.environ.get('DATABASE_URL')
    if not database_url and not development:
        raise RuntimeError('Set DATABASE_URL for production. See README.md.')
    app.config.update(
        SECRET_KEY=secret_key,
        DEVELOPMENT=development,
        SQLALCHEMY_DATABASE_URI=database_url or 'sqlite:///ingredient_advisor.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_SECURE=not development,
        REMEMBER_COOKIE_SECURE=not development,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE='Lax',
        PUBLIC_BASE_URL=os.environ.get('PUBLIC_BASE_URL', 'http://127.0.0.1:5000' if development
                                       else 'https://www.ingredientadvisor.com').rstrip('/'),
        STRIPE_WEBHOOK_SECRET=os.environ.get('STRIPE_WEBHOOK_SECRET'),
    )
