from flask import Flask, render_template, session
from sqlalchemy.orm import sessionmaker, clear_mappers, scoped_session, class_mapper
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from flask_login import LoginManager, current_user
from .model import Base, User
from flask_apscheduler import APScheduler

Session = None
login_manager = LoginManager()
scheduler = APScheduler()

def create_app():
    global Session, login_manager
    app = Flask(__name__)
    app.config.from_object('config.Config')
    Session = config_database(app)
    config_blueprint(app)
    config_login(app)
    scheduler.init_app(app)
    scheduler.start()
    global_variable(app)

    return app


def config_database(app):
    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    database_echo = app.config.get('SQLALCHEMY_ECHO', False)
    database_engine = create_engine(database_uri, connect_args={"check_same_thread": False}, poolclass=NullPool,
                                    echo=database_echo)
    session_factory = sessionmaker(autocommit=False, autoflush=True, bind=database_engine)
    if len(database_engine.table_names()) == 0:
        print("REPOPULATING DATABASE for SecondHand Plugin ...")
        Base.metadata.create_all(database_engine)
        print("REPOPULATING DATABASE for SecondHand Plugin ... FINISHED")

    return session_factory


def config_blueprint(app):
    with app.app_context():
        # Register blueprints.
        from .home_bp import home
        app.register_blueprint(home.home_bp)

        from .login_bp import login
        app.register_blueprint(login.login_bp)

        from .movie_detail_bp import movie_detail
        app.register_blueprint(movie_detail.movie_detail_bp)



def config_login(app):
    @login_manager.user_loader
    def load_user(userName):
        """
        You will need to provide a user_loader callback. This callback is used to reload the user object from the user ID
        stored in the session. It should take the str ID of a user, and return the corresponding user object.
        :param user_id:
        :return:
        """
        session = Session()
        user = session.query(User).filter(User.userName == userName).one_or_none()
        return user

    login_manager.init_app(app)
    login_manager.login_view = 'login_bp.login'



def global_variable(app):

    @app.context_processor
    def add_global_variable():
        return dict(current_user=current_user)