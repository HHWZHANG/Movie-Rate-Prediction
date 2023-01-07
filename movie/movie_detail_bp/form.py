from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, ValidationError, Email
from password_validator import PasswordValidator


class UserRating(FlaskForm):
    rating = SelectField("rating", choices=[
        10, 9, 8, 7, 6, 5, 4, 3, 2, 1
    ])
    confirm = SubmitField('Confirm')
