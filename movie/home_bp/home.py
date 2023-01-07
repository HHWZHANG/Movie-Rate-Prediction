import os

import uuid
from flask import Blueprint, render_template, url_for, request, redirect, session, g, current_app
from flask_login import current_user
from movie import Session
from movie.model import Movie, ComingSoonPredictorRecord
from .comingSoon_auto_predictor import comingSoon_auto_predictor
import datetime
from sqlalchemy import or_, and_
from functools import cmp_to_key
from movie.helper import nullable_sort
from .recommendation import pre_recommendation
import random

home_bp = Blueprint(
    'home_bp', __name__, template_folder='templates', static_folder='static'
)


@home_bp.before_request
# user process
def check_anonymous():
    if current_user.is_anonymous:
        if "recommended_movies_id_list" not in session or not session["recommended_movies_id_list"]:
            session["recommended_movies_id_list"] = []
            num_of_pre_select = 6
            db_session = Session()
            pre_select = db_session.query(Movie).filter(Movie.is_pre_select.is_(True)).all()
            random.shuffle(pre_select)
            if len(pre_select) > num_of_pre_select:
                pre_select = pre_select[:6]
            g.pre_select = pre_select
            session['anonymous_id'] = uuid.uuid4()
            session['need_select'] = True
        else:
            session['need_select'] = False
    else:
        if "recommended_movies_id_list" not in session or not session["recommended_movies_id_list"]:
            session["recommended_movies_id_list"] = []



@home_bp.route('/', methods=['GET'])
def home():
    # Coming Soon
    num_of_comingSoon = 10
    db_session = Session()
    comingSoon = db_session.query(Movie).filter(and_(
        or_(Movie.releaseDate > (datetime.date.today() - datetime.timedelta(days=10)),
            Movie.releaseDate is None), Movie.predict_rating != None)).all()
    if len(comingSoon) > num_of_comingSoon:
        comingSoon.sort(key=lambda x: x.predict_rating, reverse=True)
        comingSoon = comingSoon[:10]
    recommended_movies = db_session.query(Movie).filter(Movie.imdb_id.in_(session["recommended_movies_id_list"])).all()

    return render_template('movie.html', current_user=current_user, need_select=session['need_select'],
                           anonymous_id=session['anonymous_id'], comingSoon=comingSoon,
                           recommended_movies=recommended_movies)


@home_bp.route('/comingSoon', methods=['GET'])
def comingSoon():
    sort_arg = request.args.get("sort")
    db_session = Session()
    movie: list = db_session.query(Movie).filter(
        or_(Movie.releaseDate > (datetime.date.today() - datetime.timedelta(days=10)),
            Movie.releaseDate is None), Movie.predict_rating != None).all()
    ComingSoonPredictorRecord_last = db_session.query(ComingSoonPredictorRecord).order_by(ComingSoonPredictorRecord.process_time.desc()).limit(1).one_or_none()
    if ComingSoonPredictorRecord_last is not None:
        predictionLastTime = ComingSoonPredictorRecord_last.process_time
    else:
        predictionLastTime = None
    if sort_arg is None or sort_arg == "rating":
        movie.sort(key=lambda x: x.predict_rating, reverse=True)
    elif sort_arg == "releaseDate":
        movie.sort(key=cmp_to_key(lambda x, y: nullable_sort(x.releaseDate, y.releaseDate)), reverse=False)
    return render_template('coming-soon.html', current_user=current_user, movie=movie,
                           need_select=session['need_select'], predictionLastTime = predictionLastTime)


@home_bp.route('/test_auto_predictor', methods=['GET'])
def test_auto_predictor():
    return comingSoon_auto_predictor()


@home_bp.route('/test', methods=['GET'])
def test():
    print()
    return "See terminal"


@home_bp.route('/process_pre_recommendation', methods=['GET'])
def process_pre_recommendation():
    selected_imdb_id = request.args.get("selected_imdb_id").split(",")
    recommended_movies_id_list = pre_recommendation(selected_imdb_id, str(session['anonymous_id']))
    session["recommended_movies_id_list"] = recommended_movies_id_list.copy()
    return "Success"
