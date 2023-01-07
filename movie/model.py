import datetime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Date, Table
from flask_login import UserMixin

Base = declarative_base()

class User(Base, UserMixin):
    __tablename__ = 'User'
    userName = Column(String, primary_key=True)
    password = Column(String)
    email = Column(String)
    createDateTime = Column(DateTime)
    movies_rating = relationship("UserMovieRating", back_populates="user")
    def get_id(self):
        return self.userName


class Movie(Base):
    __tablename__ = 'Movie'
    imdb_id = Column(String, primary_key=True)
    title = Column(String)
    image_url = Column(String, nullable=True)
    releaseDate = Column(Date, nullable=True)
    plot = Column(String, nullable=True)
    predict_rating = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    is_pre_select = Column(Boolean, nullable=True)
    comingSoon_pid = Column(Integer, ForeignKey('ComingSoonPredictorRecord.pid'), nullable=True)
    users_rated = relationship("UserMovieRating", back_populates="movie")

class UserMovieRating(Base):
    __tablename__ = 'UserMovieRating'
    userName = Column(ForeignKey('User.userName'), primary_key=True)
    imdb_id = Column(ForeignKey('Movie.imdb_id'), primary_key=True)
    userRating = Column(Integer)
    movie = relationship("Movie", back_populates="users_rated")
    user = relationship("User", back_populates="movies_rating")



class ComingSoonPredictorRecord(Base):
    __tablename__ = 'ComingSoonPredictorRecord'
    pid = Column(Integer, primary_key=True, autoincrement=True)
    process_time = Column(DateTime)
    movie = relationship("Movie")

