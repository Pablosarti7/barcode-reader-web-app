from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, validators
from wtforms.validators import DataRequired, EqualTo, Regexp


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), validators.Email()], render_kw={"placeholder": "Enter Email"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Enter Password"})
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired(),
        Regexp(r'^[A-Za-z ]+$', message="Please enter a valid name with alphabetic characters only.")
    ], render_kw={"placeholder": "Enter Name"})
    email = StringField('Email', validators=[DataRequired(), validators.Email()], render_kw={"placeholder": "Enter Email"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Enter Password"})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')], render_kw={"placeholder": "Re-enter Password"})
    submit = SubmitField('Register')


class SearchBarcode(FlaskForm):
    ingredients = StringField('Search', validators=[DataRequired()], render_kw={"placeholder": "Enter barcode here"})
    submit = SubmitField('Search')


class SearchIngredient(FlaskForm):
    ingredient = StringField('Search', validators=[DataRequired()], render_kw={"placeholder": "Enter ingredient here"})
    submit = SubmitField('Search')


class EditProfile(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), validators.Email()], render_kw={"placeholder": "Enter Email"})


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), validators.Email()], render_kw={"placeholder": "Enter Email"})
    submit = SubmitField('Reset Password')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Enter Password"})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')], render_kw={"placeholder": "Re-enter Password"})
    submit = SubmitField('Reset Password')