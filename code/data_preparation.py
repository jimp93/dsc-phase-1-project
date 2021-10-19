from selenium import webdriver
from PIL import Image
import os
from os import path
import time
import random
import pandas as pd
import requests
import json
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import seaborn as sns

### INITIATION FUNCTIONS ###

def open_files():
    '''Opens up the stored dataframes, to save having to scrape all the movies every time'''
    numbers_df = pd.read_csv('data/numbers_df.csv')
    attributes_df = pd.read_csv('data/attributes_df.csv', converters={'Genre_List': eval, 'Actor_List': eval, 'Writer_List': eval, 'Director_List': eval})
    financials_15_df = pd.read_csv('data/financials_15_df.csv')
    
    with open("data/financials_list.json", "r") as fp:
        financials_list = json.load(fp)
        
    with open("data/omdb_attrs.json", "r") as ffo:
        omdb_attrs = json.load(ffo)
     
    return (financials_list, numbers_df, financials_15_df, omdb_attrs, attributes_df)

 
# TMDB API CALLS
def get_tmdb_key():
    with open('C:/Users/james/.secret/tmdbApi.txt', 'r') as h:
        tmdb_key = h.read()
    return tmdb_key

        
def tmdb_genre_keywords(financial_attributes_hits_join, tmdb_key, genre):
    '''iterates through every profitable movie in the passed genre, calls the tmdb api
    and returns a list of keywords attached to them in the tmdb databse'''
    all_profitable_in_genre_df  = feature_v_financialMean_df_maker('imdb_code', 'profit_loss_$', financial_attributes_hits_join, genre)
    imdb_list = all_profitable_in_genre_df['imdb_code'].tolist()
    all_data={}
    for m in imdb_list:
        try:
            lang_url = 'https://api.themoviedb.org/3/find/' + m + '?api_key='  + tmdb_key + '&language=en-US&external_source=imdb_id'
            response = requests.get(lang_url)
            im_movie_data = json.loads(response.content.decode('utf-8')) 
            tmd_id = str(im_movie_data['movie_results'][0]['id'])
            keywords_url = 'https://api.themoviedb.org/3/movie/' + tmd_id + '/keywords?api_key=' + tmdb_key
            keywords_response = requests.get(keywords_url)
            keywords_movie_data = json.loads(keywords_response.content.decode('utf-8')) 
            all_data[m]=keywords_movie_data
        except:
            continue
    keyword_list=[]
    for key in all_data:
        for dic in all_data[key]['keywords']:
            keyword_list.append(dic['name'])
    return keyword_list
        
        
# DATA PREPARATION FUNCTIONS 

def make_filtered_df(x_column, y_column, base_join_df, genre_filter):
    '''filters only for films in passed genres'''
    if genre_filter:
        genre_filter_list = []
        for index, row in base_join_df.iterrows():
            row_genres = row['Genre_List']
            if all(w in row_genres for w in genre_filter):
                genre_filter_list.append(row)
        variable_df = pd.DataFrame(genre_filter_list)
        
    return variable_df


def feature_v_financialMean_df_maker(x_column, y_column, base_join_df, genre_filter = None): 
    '''Main function in data analysis. It takes in a joined base dataframe, any one of its categorical feature, 
    one of its financial columns, and a filter for genres
    It returns a dataframe grouped by the categorical feature and ordered by the mean of the financial column'''
    
    variable_df = base_join_df.copy()
    variable_df[['budget_$', 'domestic_box_office_$', 'worldwide_box_office_$', 'profit_loss_$']] = variable_df[['budget_$', 'domestic_box_office_$', 'worldwide_box_office_$', 'profit_loss_$']].apply(lambda x: x/1000000)
    
    if genre_filter:
        variable_df = make_filtered_df(x_column, y_column, variable_df, genre_filter) 
        variable_df=variable_df.reset_index(drop=True)
    

    if isinstance(variable_df.loc[1, x_column], list):
        variable_df = variable_df.explode(x_column)
    
    if x_column == 'Genre_List':
        variable_df = variable_df[variable_df['Genre_List'] != 'N/A']
        
    if genre_filter and x_column == 'Genre_List':
        variable_df = variable_df[~variable_df.Genre_List.isin(genre_filter)]
    
    variable_df['Counts'] = variable_df[x_column].map(variable_df[x_column].value_counts())

    variable_df = variable_df.groupby(x_column).mean()
    variable_df = variable_df.sort_values(by = y_column, ascending=False)
    variable_df = variable_df.reset_index()
    return variable_df


# DATA MODELING

def make_profit_loss_df(financial_attributes_join, financial_attributes_flops_join, financial_attributes_hits_join):
    '''returns a dataframe showing number of flops and hits for each genre, for genres with more than 200 movies'''
    all_genre_df = feature_v_financialMean_df_maker('Genre_List', 'profit_loss_$', financial_attributes_join)
    all_genre_df['All_Counts'] = all_genre_df['Counts'] 
    all_genre_df.set_index('Genre_List', inplace=True)
    all_genre_df = all_genre_df['All_Counts']
    
    flops_genre_df = feature_v_financialMean_df_maker('Genre_List', 'profit_loss_$', financial_attributes_flops_join)
    flops_genre_df['Flop_Counts'] = flops_genre_df['Counts'] 
    flops_genre_df.set_index('Genre_List', inplace=True)
    flops_genre_df = flops_genre_df['Flop_Counts']
    
    hits_genre_df = feature_v_financialMean_df_maker('Genre_List', 'profit_loss_$', financial_attributes_hits_join)
    hits_genre_df['Hit_Counts'] = hits_genre_df['Counts'] 
    hits_genre_df.set_index('Genre_List', inplace=True)
    hits_genre_df = hits_genre_df['Hit_Counts']

    # limit to genres with over 200 movies 
    concat_gen_df = pd.concat([all_genre_df, flops_genre_df, hits_genre_df], axis=1, sort=False)
    filtered_concat_gen_df = concat_gen_df[concat_gen_df['All_Counts'] > 200]
    filtered_concat_gen_df.index.names = ['Genre_List']
    filtered_concat_gen_df=filtered_concat_gen_df.reset_index()
    filtered_concat_gen_df['Percent_Hits']=(filtered_concat_gen_df['Hit_Counts']/filtered_concat_gen_df['All_Counts'])*100
    
    return filtered_concat_gen_df


def horror_genre_filter(row):
    if 'Mystery' in row['Genre_List'] and 'Thriller' in row['Genre_List']:
        value = 'Horror/Mystery/Thriller'
    elif 'Mystery' in row['Genre_List'] and 'Thriller' not in row['Genre_List']:
        value = 'Horror/Mystery'
    elif 'Mystery' not in row['Genre_List'] and 'Thriller' in row['Genre_List']:
        value = 'Horror/Thriller'
    else:
        value = 'Horror'
    return value
    
def adventure_genre_filter(row):
    if 'Action' in row['Genre_List'] and 'Sci-Fi' in row['Genre_List']:
        value = 'Adventure/Sci-Fi/Action'
    elif 'Action' in row['Genre_List'] and 'Sci-Fi' not in row['Genre_List']:
        value = 'Adventure/Action'
    elif 'Action' not in row['Genre_List'] and 'Sci-Fi' in row['Genre_List']:
        value = 'Adventure/Sci-Fi'
    else:
        value = 'Adventure'
    return value

def budget_prep(gen_bud_df, genre):
    '''returns a dataframe including only movies in the passed genre (only used for adventure and horror). 
    It creates a new subgenre column that specifies which of the subgenres of the main genre the movie belongs to
    It also converts the financial columns into $m sted $'''   
    gen_bud_s = gen_bud_df.copy()
    for index, row in gen_bud_s.iterrows():
        if genre == 'horror':
            value = horror_genre_filter(row)
        else:
            value = adventure_genre_filter(row)
        gen_bud_s.loc[index, 'subgenre'] = value
        
    gen_bud_s[['budget_$', 'profit_loss_$']] = gen_bud_s[['budget_$', 'profit_loss_$']].apply(lambda x: x/1000000)
    gen_bud_s = gen_bud_s.sort_values(by='profit_loss_$', ascending = False)
    return gen_bud_s
    

def make_crew_df(financial_attributes_join, top_actors, top_directors, top_writers):
    '''returns a dataframe containing all the movies worked on by the top 5 most profitable actors, directors and writers'''
    top_rows_list = []
    for index, row in financial_attributes_join.iterrows():
        if (pd.isnull(row['mean_rating'])):
            continue
        w_list = row['Writer_List']
        a_list = row['Actor_List']
        d_list = row['Director_List']
        
        if any(x in a_list for x in top_actors):
            top_rows_list.append(row)
        if any(y in w_list for y in top_writers):
            top_rows_list.append(row)
        if any(z in d_list for z in top_directors):
            top_rows_list.append(row)

    top_full_crew_df = pd.DataFrame(top_rows_list)
    top_full_crew_df = top_full_crew_df.drop_duplicates(subset=['imdb_code'])
    return top_full_crew_df

def df_generator(top_full_crew_df, crew_column, top_crew_list):
    '''returns dataframe containing all the movies worked on by the top 5 most profitable names in the crew type passed in 
    (actors, directors or writers)'''
    top_crew_df = top_full_crew_df.explode(crew_column)
    top_crew_df = top_crew_df.groupby(crew_column).mean()
    top_crew_df = top_crew_df.reset_index()
    top_crew_df = top_crew_df[top_crew_df[crew_column].isin(top_crew_list)]
    return top_crew_df

def rank_generator(top_full_crew_df, crew_column, top_crew_list):
    '''returns a dataframe where the 5 most profitable names in the crew type passed in are ranked in terms of 
    profitability, ROI and user ratings'''
    df = df_generator(top_full_crew_df, crew_column, top_crew_list)
    df=df[[crew_column, 'profit_loss_$', 'return_pct', 'budget_$', 'mean_rating']]
    
    df = df.sort_values(by = 'return_pct', ascending=False)   
    df['return % rank'] = range(1, 1+len(df))
    
    df = df.sort_values(by = 'profit_loss_$', ascending = False)
    df['gross profit rank'] = range(1, 1+len(df))
    
    df = df.sort_values(by = 'mean_rating', ascending = False)
    df['rating rank'] = range(1, 1+len(df))
    return df

        