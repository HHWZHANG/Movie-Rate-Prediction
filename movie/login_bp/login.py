import datetime

from flask import Blueprint, render_template, url_for, request, redirect, abort, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from .form import LoginForm, RegistrationForm
from movie.helper import is_safe_url
from movie import Session
from movie.model import User
from movie.service import add_new_user_recommendation_information_to_database, get_user

login_bp = Blueprint(
    'login_bp', __name__, template_folder='templates', static_folder='static'
)


class AuthenticationException(Exception):
    pass


class NameNotUniqueException(Exception):
    pass


class UnknownUserException(Exception):
    pass


def authenticate_user(user_name: str, password: str):
    authenticated = False

    user = get_user(user_name)
    if user is None:
        raise UnknownUserException

    if user is not None:
        authenticated = check_password_hash(user.password, password)
    if not authenticated:
        raise AuthenticationException


def add_user(user_name: str, password: str, email: str):
    # Check that the given user name is available.
    user = get_user(user_name)
    if user is not None:
        raise NameNotUniqueException

    # Encrypt password so that the database doesn't store passwords 'in the clear'.
    password_hash = generate_password_hash(password)
    # Create and store the new User, with password encrypted.
    user = User(
        userName=user_name,
        password=password_hash,
        email=email,
        createDateTime=datetime.datetime.now()
    )
    session = Session()
    session.add(user)
    session.commit()





@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    form = LoginForm()
    reg_form = RegistrationForm()
    error_mesg = None
    if form.validate_on_submit():
        # Login and validate the user.
        # user should be an instance of your `User` class
        try:
            user = get_user(form.user_name.data)
            authenticate_user(form.user_name.data, form.password.data)
            login_user(user, remember=form.remember.data)
            next = request.args.get('next')
            # is_safe_url should check if the url is safe for redirects.
            # See http://flask.pocoo.org/snippets/62/ for an example.
            if not is_safe_url(next):
                return abort(400)
            return redirect(next or url_for('home_bp.home'))

        except UnknownUserException:
            error_mesg = 'User name not recognised'

        except AuthenticationException:
            error_mesg = 'Password does not match supplied user name - please check and try again'

        # except:
        #     error_mesg = 'Unknown error'
    else:
        if form.errors != {}:
            error_mesg = form.errors

    return render_template('login-and-register-2.html',
                           error_mesg=error_mesg,
                           log_form=form,
                           reg_form=reg_form,
                           is_login=True,
                           log_handler_url=url_for('login_bp.login'),
                           reg_handler_url=url_for('login_bp.register')
                           )


@login_bp.route('/register', methods=['GET', 'POST'])
def register():
    log_form = LoginForm()
    form = RegistrationForm()
    error_mesg = None

    if form.validate_on_submit():
        # Successful POST, i.e. the user name and password have passed validation checking.
        # Use the service layer to attempt to add the new user.
        try:
            add_user(form.user_name.data, form.password.data, form.email.data)
            user = get_user(form.user_name.data)
            login_user(user)
            if add_new_user_recommendation_information_to_database(form.user_name.data, session["recommended_movies_id_list"]):
                print("Store new user recommended movie information successfully")
            else:
                print("Error: Fail to store new user recommended movie information")
            next = request.args.get('next')
            # is_safe_url should check if the url is safe for redirects.
            if not is_safe_url(next):
                return abort(400)
            return redirect(next or url_for('home_bp.home'))
        except NameNotUniqueException:
            error_mesg = 'Your user name is already taken - please supply another'
    else:
        if form.errors != {}:
            error_mesg = form.errors

    # For a GET or a failed POST request, return the Registration Web page.
    return render_template('login-and-register-2.html',
                           error_mesg=error_mesg,
                           log_form=log_form,
                           reg_form=form,
                           is_login=False,
                           log_handler_url=url_for('login_bp.login'),
                           reg_handler_url=url_for('login_bp.register'))


@login_bp.route('/logout')
@login_required
def logout():
    next = request.args.get('next')
    logout_user()
    return redirect(next or url_for('home_bp.home'))




