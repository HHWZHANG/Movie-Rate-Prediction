import uuid
from flask import Blueprint, render_template, url_for, request, redirect, session, g, current_app, flash
from flask_login import current_user, login_required
from movie import Session
from movie.model import Movie
import datetime
from sqlalchemy import or_, and_
from functools import cmp_to_key
from movie.helper import nullable_sort
import random
from .form import UserRating
from movie.service import add_user_rating_to_database

movie_detail_bp = Blueprint(
    'movie_detail_bp', __name__, template_folder='templates', static_folder='static'
)


@movie_detail_bp.route('/movie_detail/<imdb_id>', methods=['GET', 'POST'])
@login_required
def movie_detail(imdb_id):
    db_session = Session()
    movie = db_session.query(Movie).filter(Movie.imdb_id == imdb_id).one_or_none()
    form = UserRating()
    if form.validate_on_submit():
        rating = form.rating.data
        add_user_rating_to_database(current_user.userName, imdb_id, rating)
    return render_template("movie_detail.html", movie=movie, form=form)
