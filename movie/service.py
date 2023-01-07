from movie import Session
from movie.model import Movie, UserMovieRating, User


def add_new_user_recommendation_information_to_database(userName, movie_list):
    for m in movie_list:
        db_session = Session()
        user = db_session.query(User).filter(User.userName == userName).one_or_none()
        movie = db_session.query(Movie).filter(Movie.imdb_id == m).one_or_none()
        if movie is not None and user is not None:
            userMovieRating = UserMovieRating(
                userRating=10
            )
            userMovieRating.movie = movie
            userMovieRating.user = user
            user.movies_rating.append(userMovieRating)
            movie.users_rated.append(userMovieRating)
            db_session.add(userMovieRating)
            db_session.commit()
            print(movie.imdb_id + " has been added to " + user.userName + " recommended list")


def add_user_rating_to_database(userName, imdb_id, rating: int):
    db_session = Session()
    user = db_session.query(User).filter(User.userName == userName).one_or_none()
    movie = db_session.query(Movie).filter(Movie.imdb_id == imdb_id).one_or_none()
    if movie is not None and user is not None:
        userMovieRating = db_session.query(UserMovieRating).filter(UserMovieRating.userName == userName,
                                                                   UserMovieRating.imdb_id == imdb_id).one_or_none()
        if userMovieRating is not None:
            userMovieRating.userRating = rating
            db_session.commit()
            print("Successful change score")
        else:
            userMovieRating = UserMovieRating(
                userRating=rating
            )
            userMovieRating.movie = movie
            userMovieRating.user = user
            user.movies_rating.append(userMovieRating)
            movie.users_rated.append(userMovieRating)
            db_session.add(userMovieRating)
            db_session.commit()
            print(movie.imdb_id + " has been added to " + user.userName + " rated list")



def get_user(userName):
    session = Session()
    user = session.query(User).filter(User.userName == userName).one_or_none()
    return user
