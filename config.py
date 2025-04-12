import os

# SQLalchemy database configurations
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
SQLALCHEMY_TRACK_MODIFICATIONS = False
# Ensures cookies are only sent over HTTPS
SESSION_COOKIE_SECURE = True
REMEMBER_COOKIE_SECURE = True
# Prevents JavaScript access to cookies
SESSION_COOKIE_HTTPONLY = True

# OAuth configurations
GOOGLE_CLIENT_ID = os.environ.get("CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = ('https://accounts.google.com/.well-known/openid-configuration')

# Mail SMTP configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.environ.get("G_EMAIL")
MAIL_PASSWORD = os.environ.get("G_PASSWORD")