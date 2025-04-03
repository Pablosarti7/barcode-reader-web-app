from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Users table storing all the information
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
    subscribed = db.Column(db.Boolean)

    def __repr__(self):
        return f'<User {self.email}>'

# Scan History table from a single user
class ScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    item_barcode = db.Column(db.String(100), nullable=True)
    user = db.relationship('Users', backref=db.backref('scan_history', lazy=True))