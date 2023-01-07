import datetime

from movie.helper import is_number
from .helper import parse_json
import requests
import pandas as pd
import sqlite3
import numpy as np
from sqlite3 import OperationalError
import joblib
from movie import Session, scheduler
from movie.model import Movie, ComingSoonPredictorRecord
from sqlalchemy.exc import IntegrityError

# main function
@scheduler.task('interval', id='comingSoon_auto_predictor_1', seconds=86400, misfire_grace_time=3600)
def comingSoon_auto_predictor():
    print("start scheduler job: comingSoon_auto_predictor")
    db_session = Session()
    comingSoonPredictorRecord = ComingSoonPredictorRecord(
        process_time=datetime.datetime.now()
    )
    db_session.add(comingSoonPredictorRecord)
    db_session.commit()
    id_list = get_coming_soon_list()

    in_db = db_session.query(Movie.imdb_id).filter(Movie.imdb_id.in_(id_list)).all()
    in_db = [i[0] for i in in_db]
    not_in_db = [i for i in id_list if i not in in_db]
    print(not_in_db)
    if not_in_db:
        movie_df_pre = get_movie_information(not_in_db)
        movie_df = pre_process(movie_df_pre)
        if len(movie_df) == 0:
            return "No new movie"
        movie_df = get_score(movie_df)
        if len(movie_df) == 0:
            return "No new movie"
        cleaned_movie_df = data_cleaning(movie_df)
        if len(cleaned_movie_df) == 0:
            return "No new movie"
        result_df = predict(cleaned_movie_df)
        if len(result_df) == 0:
            return "No new movie"
        commit_to_db(result_df)
        return "Finish! Add " + str(len(result_df)) + " Movie"
    else:
        return "No new movie"


def commit_to_db(df):
    if len(df) > 0:
        db_session = Session()
        for i in df.iloc:
            try:
                if i["releaseDate"] is not None:
                     releaseDate_object = datetime.datetime.strptime(i["releaseDate"], "%Y-%m-%d").date()
                else:
                    releaseDate_object = None

                movie = Movie(
                    imdb_id=i["imdb_id"],
                    title=i["title"],
                    image_url=i["image"],
                    releaseDate=releaseDate_object,
                    plot=i["plot"],
                    predict_rating=i["Predict_Rating"],
                    comingSoon_pid=
                    db_session.query(ComingSoonPredictorRecord.pid).order_by(
                        ComingSoonPredictorRecord.pid.desc()).first()[
                        0]
                )
                db_session.add(movie)
                db_session.commit()
            except IntegrityError as e:
                print("commit_to_db(): error in ->" + e)
                continue
    else:
        print("No new movie")


def get_coming_soon_list():
    response = requests.get('https://imdb-api.com/en/API/ComingSoon/k_06ah6fds')
    response_js = response.json()
    df = pd.DataFrame(response_js['items'])
    imdb_id = list(df['id'])
    return imdb_id


def get_movie_information(id_list):
    response = requests.get('https://imdb-api.com/en/API/Title/k_06ah6fds/')
    response_js = response.json()
    movie_df_pre = pd.DataFrame(columns=list(response_js.keys()))
    for i in id_list:
        response = requests.get('https://imdb-api.com/en/API/Title/k_06ah6fds/{}'.format(i))
        response_js = response.json()
        movie_df_pre.loc[len(movie_df_pre)] = list(response_js.values())
    return movie_df_pre


def pre_process(movie_df_pre):
    movie_df = movie_df_pre.copy()
    movie_df.dropna(subset="title", inplace=True)
    movie_df = movie_df[movie_df["type"] == 'Movie']
    delete_col = [
        "metacriticRating", "ratings", "wikipedia", "posters", "images", "trailer", "tagline", "keywords", "similars",
        "tvSeriesInfo", "tvEpisodeInfo", "errorMessage", "runtimeStr", "plotLocal", "plotLocalIsRtl", "awards",
        "writerList", "stars", "starList", "fullCast", "genreList", "companies", "countryList",
        "languageList"

    ]
    movie_df.drop(
        delete_col,
        axis=1,
        inplace=True,
        errors='ignore')
    rename_dict = {
        "id": "imdb_id",
        "actorList": "cast",
        "countries": "production_countries",
        "languages": "original_language",
        "keywordList": "keywords",
        "companyList": "production_companies",
        "runtimeMins": "runtime"
    }
    movie_df.rename(columns=rename_dict, inplace=True)

    movie_df['cast'] = movie_df['cast'].apply(parse_json, args=("id", "", "", "list", 5))
    movie_df['directorList'] = movie_df['directorList'].apply(parse_json, args=("id", "", "", "list", 5))
    movie_df["production_companies"] = movie_df["production_companies"].apply(parse_json, args=("name",))
    movie_df["writers"] = movie_df["writers"].str.split(",")
    movie_df["directors"] = movie_df["directors"].str.split(",")
    movie_df["production_countries"] = movie_df["production_countries"].str.split(",")
    movie_df["genres"] = movie_df["genres"].str.split(",")
    # movie_df['budget'] = movie_df['boxOffice'].apply(lambda x: x["budget"])

    # movie_df = movie_df[movie_df["budget"] != ""].copy()
    #
    # movie_df['budget'] = movie_df['budget'].apply(lambda x: "".join(list(filter(str.isdigit, x))))
    return movie_df


def get_score(movie_df):
    conn = sqlite3.connect('imdb.db')
    print("Opened database successfully")

    def cast_crew_value(x, job):
        total = 0
        count = 0
        job = str(job)[1:-1]
        for element in x:
            cursor = conn.execute(f'''SELECT avg(rating)
            FROM (SELECT DISTINCT c.title_id, r.rating
            FROM crew c, ratings r
            WHERE c.title_id = r.title_id
                AND c.person_id = '{element}' AND c.category in ({job}));
            ''')

            var = cursor.fetchone()[0] or 0
            if var != 0:
                total += var
                count += 1
        if count == 0:
            return 0
        else:
            return total / count

    def company_info_to_database(js):
        company = js["name"]
        for i in js['items']:
            try:
                cursor = conn.execute(f'''SELECT *
                    FROM company
                    WHERE title_id = '{i["id"]}' AND company_name = '{company}';''')
            except OperationalError:
                cursor = conn.execute(f'''SELECT *
                    FROM company
                    WHERE title_id = '{i["id"]}' AND company_name = "{company}";''')
            result = cursor.fetchall()
            if result == []:
                try:
                    conn.execute(f'''INSERT INTO company VALUES("{i["id"]}", "{company}")
                        ''')
                except OperationalError:
                    conn.execute(f'''INSERT INTO company VALUES("{i["id"]}", '{company}')
                        ''')
                conn.commit()
                print("Successful insert into company!")

            cursor = conn.execute(f'''SELECT *
                FROM ratings
                WHERE title_id = '{i["id"]}';''')
            result = cursor.fetchall()
            if result == [] and is_number(i["imDbRating"]):
                conn.execute(f'''INSERT INTO ratings(title_id, rating) VALUES("{i["id"]}", "{i["imDbRating"]}")
                        ''')
                conn.commit()
                print("Successful insert into ratings!")

    def process_special_char(x):
        x = x.replace("/", "%2F")
        return x

    def get_company_online(x):
        result = 0
        x = process_special_char(x)
        response_company_search = requests.get(
            'https://imdb-api.com/en/API/SearchCompany/k_06ah6fds/{}'.format(x))
        response_company_search_js = response_company_search.json()
        if response_company_search_js['results']:
            company_id = response_company_search_js['results'][0]['id']
            response_company_result = requests.get(
                'https://imdb-api.com/en/API/Company/k_06ah6fds/{}'.format(company_id))
            response_company_result_js = response_company_result.json()
            print(response_company_result_js)
            company_info_to_database(response_company_result_js)
            average = np.mean(
                [float(i['imDbRating']) for i in response_company_result_js['items'] if is_number(i['imDbRating'])])
            if not np.isnan(average):
                result = average
        else:
            result = None
        return result

    def get_company_score(x):
        total = 0
        count = 0
        for element in x:
            try:
                cursor = conn.execute(f'''SELECT r.rating
                FROM company c, ratings r
                WHERE c.title_id = r.title_id
                AND c.company_name like "%{element}%";''')
            except OperationalError:
                cursor = conn.execute(f'''SELECT r.rating
                FROM company c, ratings r
                WHERE c.title_id = r.title_id
                AND c.company_name like '%{element}%';''')

            var = cursor.fetchall()
            if len(var) > 2:
                total += np.mean([i[0] for i in var])
                count += 1
            else:
                company_score = get_company_online(element)
                if company_score is not None:
                    total += company_score
                    count += 1
        if count == 0:
            return 0
        else:
            return total / count

    movie_df = movie_df[movie_df['production_companies'] != '[]']
    movie_df = movie_df[movie_df['cast'] != '[]']
    movie_df = movie_df[movie_df['directorList'] != '[]']
    movie_df['company_score'] = movie_df['production_companies'].apply(lambda x: get_company_score(x))
    movie_df['actor_score'] = movie_df['cast'].apply(lambda x: cast_crew_value(x, ["actor", "actress"]))
    movie_df['director_score'] = movie_df['directorList'].apply(lambda x: cast_crew_value(x, ["director"]))
    conn.close()
    return movie_df


def data_cleaning(df):
    def hasUS(x):
        if 'United States of America' or 'USA' in x:
            return 1
        else:
            return 0

    df["hasUS"] = df['production_countries'].apply(lambda x: hasUS(x))

    def is_Drama(x):
        if 'Drama' in x:
            return 1
        else:
            return 0

    df['is_Drama'] = df['genres'].apply(lambda x: is_Drama(x))

    def is_Comedy(x):
        if 'Comedy' in x:
            return 1
        else:
            return 0

    df['is_Comedy'] = df['genres'].apply(lambda x: is_Comedy(x))

    def is_Action(x):
        if 'Action' in x:
            return 1
        else:
            return 0

    df['is_Action'] = df['genres'].apply(lambda x: is_Action(x))

    def is_Adventure(x):
        if 'Adventure' in x:
            return 1
        else:
            return 0

    df['is_Adventure'] = df['genres'].apply(lambda x: is_Adventure(x))

    def is_Crime(x):
        if 'Crime' in x:
            return 1
        else:
            return 0

    df['is_Crime'] = df['genres'].apply(lambda x: is_Crime(x))

    def is_Romance(x):
        if 'Romance' in x:
            return 1
        else:
            return 0

    df['is_Romance'] = df['genres'].apply(lambda x: is_Romance(x))

    def is_Thriller(x):
        if 'Thriller' in x:
            return 1
        else:
            return 0

    df['is_Thriller'] = df['genres'].apply(lambda x: is_Thriller(x))

    def is_Horror(x):
        if 'Horror' in x:
            return 1
        else:
            return 0

    df['is_Horror'] = df['genres'].apply(lambda x: is_Horror(x))

    def is_Sci_Fi(x):
        if 'Sci-Fi' in x:
            return 1
        else:
            return 0

    df['is_Sci_Fi'] = df['genres'].apply(lambda x: is_Sci_Fi(x))

    def is_Mystery(x):
        if 'Mystery' in x:
            return 1
        else:
            return 0

    df['is_Mystery'] = df['genres'].apply(lambda x: is_Mystery(x))

    def is_Fantasy(x):
        if 'Fantasy' in x:
            return 1
        else:
            return 0

    df['is_Fantasy'] = df['genres'].apply(lambda x: is_Fantasy(x))

    def is_Biography(x):
        if 'Biography' in x:
            return 1
        else:
            return 0

    df['is_Biography'] = df['genres'].apply(lambda x: is_Biography(x))

    def is_Family(x):
        if 'Family' in x:
            return 1
        else:
            return 0

    df['is_Family'] = df['genres'].apply(lambda x: is_Family(x))

    def is_Animation(x):
        if 'Animation' in x:
            return 1
        else:
            return 0

    df['is_Animation'] = df['genres'].apply(lambda x: is_Animation(x))

    def is_History(x):
        if 'History' in x:
            return 1
        else:
            return 0

    df['is_History'] = df['genres'].apply(lambda x: is_History(x))

    def is_Music(x):
        if 'Music' in x:
            return 1
        else:
            return 0

    df['is_Music'] = df['genres'].apply(lambda x: is_Music(x))

    def is_Sport(x):
        if 'Sport' in x:
            return 1
        else:
            return 0

    df['is_Sport'] = df['genres'].apply(lambda x: is_Sport(x))

    def is_War(x):
        if 'War' in x:
            return 1
        else:
            return 0

    df['is_War'] = df['genres'].apply(lambda x: is_War(x))

    def is_Musical(x):
        if 'Musical' in x:
            return 1
        else:
            return 0

    df['is_Musical'] = df['genres'].apply(lambda x: is_Musical(x))

    def is_Documentary(x):
        if 'Documentary' in x:
            return 1
        else:
            return 0

    df['is_Documentary'] = df['genres'].apply(lambda x: is_Documentary(x))

    def is_Western(x):
        if 'Western' in x:
            return 1
        else:
            return 0

    df['is_Western'] = df['genres'].apply(lambda x: is_Western(x))

    def is_Film_Noir(x):
        if 'Film-Noir' in x:
            return 1
        else:
            return 0

    df['is_Film_Noir'] = df['genres'].apply(lambda x: is_Film_Noir(x))

    def is_News(x):
        if 'News' in x:
            return 1
        else:
            return 0

    df['is_News'] = df['genres'].apply(lambda x: is_News(x))

    # df["runtime"].fillna(100, inplace=True)

    # df["budget"] = df["budget"].astype(float)
    # df["runtime"] = df["runtime"].astype(float)
    # df.drop(
    #     ["boxOffice", "directors", "directorList", "writers", "cast", "genres", "production_companies",
    #      "production_countries", "original_language", "runtime", "budget"],
    #     axis=1,
    #     inplace=True,
    #     errors='ignore')

    df = df[df['company_score'] != 0.0]
    df = df[df['actor_score'] != 0.0]
    df = df[df['director_score'] != 0.0]

    return df


def predict(df):
    predict_set = df.drop(
        columns=["boxOffice", "directors", "writers", "original_language", "cast", "genres", "runtime", "budget",
                 "imdb_id", "directorList", "production_companies", "production_countries", "title", "originalTitle",
                 "fullTitle", "type", "year", "image", "releaseDate", "plot", "contentRating", "imDbRating",
                 "imDbRatingVotes", "keywords"],
        inplace=False, errors='ignore').copy()

    model1 = joblib.load("ML_model/new_model1.pkl")
    model2 = joblib.load('ML_model/new_model2.pkl')
    model3 = joblib.load('ML_model/new_model3.pkl')

    # temp = predict_set['runtime']
    # predict_set.drop(columns=['runtime'], axis=1, inplace=True)
    # predict_set.insert(1, 'runtime', temp)

    y_pre_1 = model1.predict(predict_set)
    y_pre_2 = model2.predict(predict_set)
    y_pre_3 = model3.predict(predict_set)
    prediction = (y_pre_1 + y_pre_2 + y_pre_3) / 3

    df["Predict_Rating"] = prediction
    test_df = df[
        ["imdb_id", "title", "cast", "genres", "runtime", "releaseDate", "year", "directorList", "production_companies",
         "production_countries", "contentRating", "imDbRating", "imDbRatingVotes", "Predict_Rating"]].copy()
    test_df.to_csv("comingSoon_test.csv", index=None)
    df.to_csv("test_data/comingSoon_test.csv")
    output_df = df[["imdb_id", "title", "image", "releaseDate", "plot", "Predict_Rating"]].copy()
    return output_df
