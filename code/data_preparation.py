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

# global list needed for df constructing

base_fin_col_list = ['imdb_code', 'budget_$', 'domestic_box_office_$', 'worldwide_box_office_$', 'profit_loss_$', 'return_pct', 'domestic_%', 'Genre_List']

"""
INITIATION FUNCTIONS
"""

## This function returns the keys for calls to 3 apis. The key is stored in secret file on local computer
def get_api_keys():
    with open('C:/Users/james/.secret/patronOmdb.txt', 'r') as f:
        omdb_key = f.read()

    with open('C:/Users/james/.secret/imdbApi.txt', 'r') as g:
        imdb_key = g.read()

    with open('C:/Users/james/.secret/tmdbApi.txt', 'r') as h:
        tmdb_key = h.read()  
        
    return (omdb_key, imdb_key, tmdb_key)

## This function opens up the stored dataframes, to save having to scrape all the movies every time
def open_files():
    numbers_df = pd.read_csv('data/numbers_df.csv')
    attributes_df = pd.read_csv('data/attributes_df.csv', converters={'Genre_List': eval, 'Actor_List': eval, 'Writer_List': eval, 'Director_List': eval})
    financials_15_df = pd.read_csv('data/financials_15_df.csv')
    
    with open("data/financials_list.json", "r") as fp:
        financials_list = json.load(fp)
        
    with open("data/omdb_attrs.json", "r") as ffo:
        omdb_attrs = json.load(ffo)
     
    return (financials_list, numbers_df, financials_15_df, omdb_attrs, attributes_df)

## Saves raw dataframes at the end of session where they were created
def save_files(financials_list, numbers_df, financials_15_df, omdb_attrs, attributes_df):
    numbers_df.to_csv('data/numbers_df.csv', index=False)
    financials_15_df.to_csv('data/financials_15_df.csv', index=False)
    attributes_df.to_csv('data/attributes_df.csv', index=False)
    
    with open("data/financials_list.json", "w") as ffp:
        json.dump(financials_list, ffp)

    with open("data/omdb_attrs.json", "w") as ffo:
        json.dump(omdb_attrs, ffo)
     
""" SCRAPING/DATAFRAME CONSTRUCTION/CLEANING FUNCTIONS """


def the_numbers_scraping():
    chromedriver = 'C:/Users/james/AppData/Local/Google/Chrome/chromedriver.exe'
    os.environ["webdriver.chrome.driver"] = chromedriver
    driver = webdriver.Chrome(chromedriver)
    financials_list = []
    for r in range(62):
        time.sleep(random.uniform(2, 4))
        if r == 0:
            url = 'https://www.the-numbers.com/movie/budgets/all'
        else:
            url = 'https://www.the-numbers.com/movie/budgets/all/' + str(r) + '01'
        driver.get(url)  
        mytable = driver.find_element_by_css_selector('table')
        for row in mytable.find_elements_by_css_selector('tr'):
            row_list=[]
            cn=0
            for cell in row.find_elements_by_tag_name('td'):
                if cn != 0:  
                    row_list.append(cell.text)
                cn+=1
            if row_list:
                financials_list.append(row_list)
    return financials_list


def construct_prepare_numbers_df(financials_list):  
    numbers_df = pd.DataFrame(financials_list)
    numbers_df.columns=['release_date', 'title', 'budget_$', 'domestic_box_office_$', 'worldwide_box_office_$']

    # strip '$' ' '  ','  from values that need to be floats
    numbers_df= numbers_df.applymap(lambda x: x.strip())
    numbers_df= numbers_df.applymap(lambda x: x[1:].replace(',', '') if  x[0] == "$" else x)
    
    # create colums to break up the release date
    numbers_df.insert(1, "release_year", "")
    numbers_df.insert(2, "release_month", "")
    numbers_df.insert(3, "release_day", "")
    
    #split up the date into d/m/y
    no_date_list = []
    for index, row in numbers_df.iterrows():
        try:
            date_list=row['release_date'].replace(',', '').split()
            row['release_year'] = date_list[2]
            row['release_month'] = date_list[0]
            row['release_day'] = date_list[1]
        except:
            no_date_list.append([row['title'], date_list])
            
    numbers_df = numbers_df[['title', 'release_year', 'release_month', 'release_day', 'budget_$', 'domestic_box_office_$', 'worldwide_box_office_$']]
    
    # dummy date to allow int coversion
    for index, row in numbers_df.iterrows():
        if row['release_year'] == '':
            row['release_year'] = '0'
        
    # make columns numeric
    numbers_df[['release_year', 'budget_$', 'domestic_box_office_$', 'worldwide_box_office_$']] = numbers_df[['release_year', 'budget_$', 'domestic_box_office_$', 'worldwide_box_office_$']].astype('int64')
    
    #filter out any movies with less than $1m budget
    numbers_df = numbers_df[numbers_df['budget_$'] >1000000]
    
    # filter out any films where worldwide figures suggest unusable film, and where domestic 
    # takings suggest it was only a hit outside the US
    
    numbers_df = numbers_df[numbers_df['domestic_box_office_$'] > 0]
    numbers_df = numbers_df[numbers_df['worldwide_box_office_$'] > 0]
        
    return numbers_df

def make_fin_15(numbers_df):
    financials_15_df = numbers_df.copy()
    
    # make imdb_code column that will be primary key and used to join to the attributes df later
    financials_15_df.insert(0, "imdb_code", "No_code")
       
    # make profit/loss columns - gross and return on investment and column of domestic share of takings
    financials_15_df['profit_loss_$'] = financials_15_df['worldwide_box_office_$'] - financials_15_df['budget_$']
    financials_15_df['return_pct'] = (100 / financials_15_df['budget_$']) * financials_15_df['profit_loss_$']
    financials_15_df['domestic_%'] = 100 * (financials_15_df['domestic_box_office_$'] / financials_15_df['worldwide_box_office_$'])
    
    # filter for only last 15 years
    financials_15_df = financials_15_df[financials_15_df['release_year'] >= 2007]
    
    return financials_15_df
    

### These functions will be called by the next bloc of code, they will manually update the attributes dictionary obtained from 
# the omdb api for films where the imdb code could ot be found programatically, mainly due to ambiguous titles or 
#chracters in the title
update_dud_url=[]
update_retrieve_error=[]

manual_list = ['Star Wars Ep. VII: The Force Awakens', 
'Star Wars Ep. VIII: The Last Jedi', 
'Prince of Persia: Sands of Time', 
'Fast and Furious 6', 
'The Chronicles of Narnia: The Voyage of the Daw…', 
'Harry Potter and the Deathly Hallows: Part II', 
'Harry Potter and the Deathly Hallows: Part I', 
'Fantastic Four: Rise of the Silver Surfer', 
'The Hangover 3', 
'Ford v. Ferrari', 
'Dr. Seuss’ The Grinch', 
'Mamma Mia: Here We Go Again!', 
'The Angry Birds Movie', 
'Wall Street 2: Money Never Sleeps',
'Dr. Seuss’ The Lorax', 
'All Eyez on Me', 
'John Wick: Chapter Two', 
'Underworld 3: Rise of the Lycans', 
'Halloween 2',        
'Precious (Based on the Novel Push by Sapphire)']

manual_imdb = ['tt2488496', 'tt2527336', 'tt0473075', 'tt1905041', 'tt0980970', 'tt1201607', 'tt0926084', 'tt0486576', 'tt1951261', 'tt1950186', 'tt2709692', 'tt6911608', 'tt1985949', 'tt1027718', 'tt1482459', 'tt1666185', 'tt4425200', 'tt0834001', 'tt1311067', 'tt0929632']

zipped_codes = list(zip(manual_list, manual_imdb))


def update_on_success(financials_15_df, movie_data, pair, imdb_code):
    title = pair[0]
    financials_15_df.loc[financials_15_df['title'] == title, 'imdb_code'] = imdb_code
    keys = ['Actors', 'Director', 'Genre', 'Plot', 'Rated', 'Ratings', 'Runtime', 'Writer', 'Title', 'imdbRating', 'imdbVotes']
    omdb_attrs[imdb_code] = {x:movie_data[x] for x in keys}

def update_get_page(url):
    response=requests.get(url)
    movie_data = json.loads(response.content.decode('utf-8')) 
    return movie_data

def update_make_omdb_dict(financials_15_df, omdb_key):
    for pair in zipped_codes:
        imdb_code = pair[1]
        url = 'http://www.omdbapi.com/?i=' + imdb_code + '&apikey=' + omdb_key
        try:
            movie_data = update_get_page(url)
            update_on_success(financials_15_df, movie_data, pair, imdb_code) 
        except:
            update_dud_url.append(pair[0])
     # delete any rows in financials_15yr where there is no imdb_code

    financials_15_df = financials_15_df[financials_15_df.imdb_code != 'No_code']
    return financials_15_df

# this goes through each of the films in numbers_df and retrieves its data from
# omdb. has similar data to imdb with high call limit
# it then creates a dictionary of dictionaries for each film, holding values for 
# attributes that are likely to influence the business proposals

# it also uses the imdbd key to update the imdb_code column in financials_15_df, a copy of numbers_df
# giving us a primary key


omdb_attrs = {}
dud_url=[]
retrieve_error=[]

def on_success(financials_15_df, movie_data, movie):
    imdb_id = movie_data['imdbID'] 
    financials_15_df['imdb_code'][financials_15_df.title == movie] = imdb_id
    keys = ['Actors', 'Director', 'Genre', 'Plot', 'Rated', 'Ratings', 'Runtime', 'Writer', 'Title', 'imdbRating', 'imdbVotes']
    omdb_attrs[imdb_id] = {x:movie_data[x] for x in keys}

def url_maker(year, title, omdb_key):
    url = 'http://www.omdbapi.com/?t=' + title + '&y=' + year + '&apikey=' + omdb_key
    return url


def get_page(url):
    response=requests.get(url)
    movie_data = json.loads(response.content.decode('utf-8')) 
    return movie_data

def make_omdb_dict(financials_15_df, omdb_key):
    for index, row in financials_15_df.iterrows():
        movie = row['title']
        title = movie.replace(',', '%2C').replace (' ', '+').replace (':', '%3A')
        year = str(row['release_year'])
        url = url_maker(year, title, omdb_key)
        try:
            movie_data = get_page(url)
            if "Error" in movie_data:  
                prev_year = (str(int(year) -1))
                url = url_maker(prev_year, title, omdb_key)
                movie_data = get_page(url)  
                #used during dev to check for non returning films
                if "Error" in movie_data:
                    film_error = movie + " - " + movie_data_t['Error'] + "\n"
                    retrieve_error.append(prev_film_error)
                else:
                    on_success(financials_15_df, movie_data, movie)
            else:
                on_success(financials_15_df, movie_data, movie)  
        except:
            dud_url.append(movie)

    return (omdb_attrs, financials_15_df)
         
            
            
# the dud urls were passed into the following encoding cleaning function, and reentered into api
# but still returned movie not found
# mainly due to not recognising characters or ambiguous/ extended titles
# not ideal, but best way to deal with them was to discard the lesser known movies and
# then manually get the code for the remaining list, then get the attributes
# using that in the api call

# clean_budget = {}
# not_decoded = []
# cleaned_movies = []
# for k in dud_url:
#    try:
#        clean_year = financials_15_df.release_year[financials_15_df.title == k].values[0]
#        bytes_string = bytes(k, encoding="raw_unicode_escape")
#        clean_movie = bytes_string.decode("utf-8", "strict")
#        two_list = [clean_movie, clean_year]
#        cleaned_movies.append(two_list)
#    except:
#        not_decoded.append(k)


# bloc of code makes the attributes_df using the data from omdb

# updates attributes dict by exploding the ratings list, so we have a column for each site
def rating_formatter():
    for key in omdb_attrs:
        for k in omdb_attrs[key]['Ratings']:
            outlet_ratings = list(k.values())
            if outlet_ratings[0] == 'Rotten Tomatoes':
                omdb_attrs[key]['RottenRating'] = outlet_ratings[1][:-1]
            elif outlet_ratings[0] == 'Metacritic':
                omdb_attrs[key]['MetacriticRating'] = outlet_ratings[1][:-4]

# formats the dictionary for conversion to df              
def clean_values():
    for mov in omdb_attrs:
        actor_list = omdb_attrs[mov]['Actors'].split(',')
        actor_list = [ac.strip() for ac in actor_list]
        omdb_attrs[mov]['Actor_List'] = actor_list
        
        genre_list = omdb_attrs[mov]['Genre'].split(',')
        genre_list = [ge.strip() for ge in genre_list]
        omdb_attrs[mov]['Genre_List'] = genre_list
        
        writer_list = omdb_attrs[mov]['Writer'].split(',')
        writer_list = [wr.strip() for wr in writer_list]
        omdb_attrs[mov]['Writer_List'] = writer_list
        
        director_list = omdb_attrs[mov]['Director'].split(',')
        director_list=[di.strip() for di in director_list]
        omdb_attrs[mov]['Director_List'] = director_list
        
        try:
            runtime = int(omdb_attrs[mov]['Runtime'].split(' ')[0])
            omdb_attrs[mov]['Run_Time'] = runtime
        
        except:
            omdb_attrs[mov]['Run_Time'] = 0
        
        try:
            imdb_votes = int(omdb_attrs[mov]['imdbVotes'].replace(',',''))
            omdb_attrs[mov]['imdb_votes'] = imdb_votes
        except:
            omdb_attrs[mov]['imdb_votes'] = '0'


def make_attributes_df():
    rating_formatter()
    clean_values()
    
    # make attributes linking dict
    
    to_df_dict = {}
    att_keys = ['Genre_List', 'Actor_List', 'Director_List', 'Writer_List',
          'Rated', 'Run_Time','MetacriticRating', 'RottenRating', 'imdbRating',
          'imdb_votes']
    for m in omdb_attrs:
        to_df_dict[m] = {}
        
        for ks in att_keys:
            try:
                to_df_dict[m][ks] = omdb_attrs[m][ks]
            except:
                to_df_dict[m][ks] = np.nan 

     
    #make the actual attributes_df
    
    attributes_df = pd.DataFrame(to_df_dict).transpose()
    attributes_df.reset_index(inplace=True)
    attributes_df = attributes_df.rename(columns = {'index':'imdb_code'})

    # make numeric values and make a mean ratings column
    attributes_df['imdbRating'] = attributes_df['imdbRating'].replace('N/A',np.NaN)
    attributes_df[['RottenRating', 'MetacriticRating', 'imdbRating', 'imdb_votes', 'Run_Time']] = attributes_df[['RottenRating', 'MetacriticRating', 'imdbRating', 'imdb_votes', 'Run_Time']].astype('float')

    attributes_df['imdbRating'] = attributes_df['imdbRating'].map(lambda x: 10*x)

    attributes_df['mean_rating'] =  (attributes_df['imdbRating'] +  attributes_df['RottenRating'] +  attributes_df['MetacriticRating'])/3
    
    return attributes_df
    
    
def make_hit_df(financials_15_df):
    # filter out any films where worldwide figures suggest unusable film, and where takings are not only a country outside the US
    financials_hits_df = financials_15_df.copy()
    financials_hits_df = financials_hits_df[financials_hits_df['profit_loss_$'] > 0]
    return financials_hits_df

def make_flop_df(financials_15_df):
    # filter out any films where worldwide figures suggest unusable film, and where takings are not only a country outside the US
    financials_flops_df = financials_15_df.copy()
    financials_flops_df = financials_flops_df[financials_flops_df['profit_loss_$'] <= 0]
    return financials_flops_df

def make_joined_dfs(financials_15_df, financials_hits_df, financials_flops_df, attributes_df):
    financial_attributes_join = financials_15_df.merge(attributes_df, how='left', on='imdb_code')
    financial_attributes_hits_join = financials_hits_df.merge(attributes_df, how='left', on='imdb_code')
    financial_attributes_flops_join = financials_flops_df.merge(attributes_df, how='left', on='imdb_code')
    
    financial_attributes_join.fillna({'Genre_List':'N/A', 'Actor_List':'N/A', 'Director_List': 'N/A', 'Writer_List': 'N/A', 'Rated': 'N/A'}, inplace=True)
    financial_attributes_hits_join.fillna({'Genre_List':'N/A', 'Actor_List':'N/A', 'Director_List': 'N/A', 'Writer_List': 'N/A', 'Rated': 'N/A'}, inplace=True)
    financial_attributes_flops_join.fillna({'Genre_List':'N/A', 'Actor_List':'N/A', 'Director_List': 'N/A', 'Writer_List': 'N/A', 'Rated': 'N/A'}, inplace=True)
    
    return(financial_attributes_join, financial_attributes_hits_join, financial_attributes_flops_join)



# These are functions that will take in any categorical feature, a filter for
# genres and one of the joined base dataframes to create
# a dataframe ordered by the profitability (rank ROI and gross and add them together)

# takes in variable_column = list containing variable column to be examined
#         base_join_df = either the filtered or non fltererd join_df
#         genre_filter = list of genres to filter by, if needed

# returns dataframe of passed variable and financial data, only if budget > $1m

def full_dataframe_maker(variable_column, base_join_df, genre_filter):
    variable_df = base_join_df
    if genre_filter:
        genre_filter_list = []
        for index, row in base_join_df.iterrows():
            row_genres = row['Genre_List']
            if all(w in row_genres for w in genre_filter):
                genre_filter_list.append(row)
        variable_df = pd.DataFrame(genre_filter_list)

    if variable_column == ['Genre_List']:
        variable_df = variable_df[base_fin_col_list]
    else:
        full_col_list = base_fin_col_list + variable_column
        variable_df = variable_df[full_col_list]

    return variable_df


def ranked_df_maker(variable_column, base_join_df, genre_filter = None): 
    variable_df = full_dataframe_maker(variable_column, base_join_df, genre_filter) 
    
    variable_string = variable_column[0]
    if genre_filter:
        variable_df.index.name = 'old_index'
        variable_df=variable_df.reset_index()
    gf = variable_df.loc[1, variable_string]
    if isinstance(variable_df.loc[1, variable_string], list):
        variable_df = variable_df.explode(variable_string)
    
    variable_df['Counts'] = variable_df[variable_string].map(variable_df[variable_string].value_counts())
    
                    
    if variable_string == 'release_year':
        variable_df = variable_df.groupby(variable_string).sum()
    else:
        variable_df = variable_df.groupby(variable_string).mean()
        if variable_string == 'Actor_List':
            variable_df = variable_df[variable_df['Counts']>1]
        variable_df = variable_df.sort_values(by = 'return_pct', ascending=False)   
        variable_df['return_p_rank'] = range(1, 1+len(variable_df))
    
        variable_df = variable_df.sort_values(by = 'profit_loss_$', ascending = False)
        variable_df['gross_prof_rank'] = range(1, 1+len(variable_df))
    
        variable_df['combined_rank'] = variable_df['gross_prof_rank'] + variable_df['return_p_rank'] 
        variable_df = variable_df.sort_values(by = 'combined_rank')
    return variable_df


""" DATA MODELING
"""

# prepares data so we can make grouped bar chart showing number of hits and flops per genre
def make_profit_loss_df(financial_attributes_join, financial_attributes_flops_join, financial_attributes_hits_join):
    all_genre_df = ranked_df_maker(['Genre_List'], financial_attributes_join)
    all_genre_df['All_Counts'] = all_genre_df['Counts'] 
    all_genre_df = all_genre_df['All_Counts']
    
    flops_genre_df = ranked_df_maker(['Genre_List'], financial_attributes_flops_join)
    flops_genre_df['Flop_Counts'] = flops_genre_df['Counts'] 
    flops_genre_df = flops_genre_df['Flop_Counts']
    
    hits_genre_df = ranked_df_maker(['Genre_List'], financial_attributes_hits_join)
    hits_genre_df['Hit_Counts'] = hits_genre_df['Counts'] 
    hits_genre_df = hits_genre_df['Hit_Counts']

    # limit to genres with over 250 movies 
    concat_gen_df = pd.concat([all_genre_df, flops_genre_df, hits_genre_df], axis=1, sort=False)
    filtered_concat_gen_df = concat_gen_df[concat_gen_df['All_Counts'] > 250]
    filtered_concat_gen_df.index.names = ['Genre_List']
    filtered_concat_gen_df=filtered_concat_gen_df.reset_index()
    
    return filtered_concat_gen_df


# These 2 functions prepare thriller data for scatterplot of return on budget by subgenre
def genre_filter(row):
    if 'Horror' in row['Genre_List'] and 'Mystery' in row['Genre_List']:
        value = 'Thriller/Horror/Mystery'
    elif 'Horror' in row['Genre_List'] and 'Mystery' not in row['Genre_List']:
        value = 'Thriller/Horror'
    elif 'Horror' not in row['Genre_List'] and 'Mystery' in row['Genre_List']:
        value = 'Mystery'
    else:
        value = 'Thriller'
    return value
    
def budget_prep(thriller_all):
    thriller_all_s = thriller_all.copy()
    for index, row in thriller_all_s.iterrows():
        value = genre_filter(row)
        thriller_all_s.loc[index, 'subgenre'] = value
    thriller_all_s['budget_$'] = thriller_all_s['budget_$']/1000000
    thriller_all_s=thriller_all_s.sort_values(by='return_pct', ascending = False)
    thriller_all_s = thriller_all_s[1:]
    return thriller_all_s
    

# this bloc makes dataframe of movies containing the top 5 in each crew category, 

top_rows_list = []
top_actors = ['Rose Byrne', 'Vera Farmiga', 'Patrick Wilson', 'Angus Sampson', 'James Ransone']
top_directors = ['John R. Leonetti', 'Jordan Peele', 'James Wan', 'David F. Sandberg', 'Corin Hardy']
top_writers = ['Gary Dauberman', 'Leigh Whannell', 'Carey W. Hayes', 'Jordan Peele', 'James Wan']

def make_crew_df(financial_attributes_join):
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

# used in preparation of the sublot showing the perfomances of top crew members
def df_generator(top_full_crew_df, crew_column, top_crew_list):
    top_crew_df = top_full_crew_df.explode(crew_column)
    top_crew_df = top_crew_df.groupby(crew_column).mean()
    top_crew_df = top_crew_df.reset_index()
    top_crew_df = top_crew_df[top_crew_df[crew_column].isin(top_crew_list)]
    return top_crew_df

def rank_generator(top_full_crew_df, crew_column, top_crew_list):
    df = df_generator(top_full_crew_df, crew_column, top_crew_list)
    df=df[[crew_column, 'profit_loss_$', 'return_pct', 'budget_$', 'mean_rating']]
    
    df = df.sort_values(by = 'return_pct', ascending=False)   
    df['return % rank'] = range(1, 1+len(df))
    
    df = df.sort_values(by = 'profit_loss_$', ascending = False)
    df['gross profit rank'] = range(1, 1+len(df))
    
    df = df.sort_values(by = 'mean_rating', ascending = False)
    df['rating rank'] = range(1, 1+len(df))
    return df

def omdb_genre_keywords(financial_attributes_hits_join, tmdb_key):
    all_profitable_in_genre_df = full_dataframe_maker(['title'], financial_attributes_hits_join, ['Horror', 'Thriller', 'Mystery'])
    imdb_list = all_profitable_in_genre_df['imdb_code'].tolist()
    all_data={}
    for m in imdb_list:
        lang_url = 'https://api.themoviedb.org/3/find/' + m + '?api_key='  + tmdb_key + '&language=en-US&external_source=imdb_id'
        response = requests.get(lang_url)
        im_movie_data = json.loads(response.content.decode('utf-8')) 
        tmd_id = str(im_movie_data['movie_results'][0]['id'])
        keywords_url = 'https://api.themoviedb.org/3/movie/' + tmd_id + '/keywords?api_key=' + tmdb_key
        keywords_response = requests.get(keywords_url)
        keywords_movie_data = json.loads(keywords_response.content.decode('utf-8')) 
        all_data[m]=keywords_movie_data
    keyword_list=[]
    for key in all_data:
        for dic in all_data[key]['keywords']:
            keyword_list.append(dic['name'])
    return keyword_list
        
        