import pandas as pd
import os
from flask import current_app
import re


# main function for recommendation
def pre_recommendation(movie_list, new_user_id):
    # store_user_pre_csv(new_user_id, movie_list)
    selected_user_file = os.listdir("Recommend_user_datas")
    selected_user = [u.rsplit(".", 1)[0] for u in selected_user_file]
    most_similar_users = sorted_by_similarity(movie_list, selected_user)
    most_similar_users = most_similar_users[:2]
    recommended_movies = get_recommend_movies(most_similar_users)
    print(recommended_movies)
    recommended_movies_result = [m[0] for m in recommended_movies]
    number_of_recommended_movie = 10
    if len(recommended_movies_result) > number_of_recommended_movie:
        result = recommended_movies_result[:number_of_recommended_movie]
    else:
        result = recommended_movies_result

    return result


# 根据相似度排序。输入为用户id列表
def sorted_by_similarity(movie_list, b):
    df = pd.DataFrame({"user_id": b, "similarity": [get_similarity(movie_list, user_id) for user_id in b]})
    df.sort_values(by='similarity', ascending=False, inplace=True)
    return df['user_id'].values


# 计算相似度
def get_similarity(movie_list, another_ID, check_stored=False):
    try:
        # df = pd.read_csv('Recommend_user_datas/' + str(Recommender_ID) + '.csv')
        df1 = pd.read_csv('Recommend_user_datas/' + str(another_ID) + '.csv')
    except:
        if check_stored:
            print(another_ID + " is not stored yet!!")
        return -1
    # df1_filtered=df1.loc[df['film_id'].isin(df['film_id'])]

    return len(set(movie_list).intersection(set(df1['film_id'])))


# 计算出最推荐电影。输入为用户id列表
def get_recommend_movies(most_similar_users):
    recommend_movies = {}
    for user_id in most_similar_users:
        try:
            df = pd.read_csv('Recommend_user_datas/' + user_id + '.csv')
        except:
            print(user_id + " is not stored yet!!")
            continue

        for idx, data in df.iterrows():
            if data['film_id'] not in recommend_movies.keys():
                recommend_movies[data['film_id']] = int(data['rank'])
            else:
                recommend_movies[data['film_id']] = int(data['rank']) + recommend_movies[data['film_id']]

    final_list = sorted(recommend_movies.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    return final_list


# 需要事先有一个Recommend_user_datas文件夹用来保存csv文件
# def store_user_pre_csv(user_ID, movie_list):
#     try:
#         df = pd.DataFrame({"film_id": movie_list, "rank": 10}, index=range(len(movie_list)))
#         df.to_csv('Recommend_user_datas/' + user_ID + '.csv')
#     except:
#         print(user_ID + " is illegal to access")
