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

### INITIATION FUNCTIONS ###

def get_api_keys():
    '''Returns the keys for calls to 3 apis. The key is stored in secret file on local computer'''
    with open('C:/Users/james/.secret/patronOmdb.txt', 'r') as f:
        omdb_key = f.read()

    with open('C:/Users/james/.secret/imdbApi.txt', 'r') as g:
        imdb_key = g.read()

    with open('C:/Users/james/.secret/tmdbApi.txt', 'r') as h:
        tmdb_key = h.read()  
        
    return (omdb_key, imdb_key, tmdb_key)

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

def save_files(financials_list, numbers_df, financials_15_df, omdb_attrs, attributes_df):
    '''Saves raw dataframes at the end of session in which they were created'''
    numbers_df.to_csv('data/numbers_df.csv', index=False)
    financials_15_df.to_csv('data/financials_15_df.csv', index=False)
    attributes_df.to_csv('data/attributes_df.csv', index=False)
    
    with open("data/financials_list.json", "w") as ffp:
        json.dump(financials_list, ffp)

    with open("data/omdb_attrs.json", "w") as ffo:
        json.dump(omdb_attrs, ffo)

     
### SCRAPING/DATAFRAME CONSTRUCTION/CLEANING FUNCTIONS ###

def the_numbers_scraping():
    '''Srapes the Numbers webite with Selenium, returns a list of lists, each containing financial details for a movie'''
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
    '''Takes in the Numbers list of lists, returns a dataframe and formats data'''
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
    
    # insert dummy date if not present to allow int coversion
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
    '''Takes in the Numbers dataframe and filters to only include movies from last 15 years and add profit, imdb_code columns'''
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
    
# API CALLS AND DATAFRAME CONSTRUCTION
# THESE FUNCTIONS CALL THE OMDB AND TURN THE METADATA FOR EACH MOVIE IN THE NUMBERS DATAFRAME INTO A DICT OF DICTS 
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
    '''The engine of the OMDB API calls. It iterates through each movie in financials_15_df and retrieves its metadata from 
    omdb. It returns a dictionary of dictionaries containing metadata for each film. It also adds the imdb_code to 
    financials_15_df and constructs a list of movies where the API call fails due to an ambiguous title
    The important films from that list are manually stored in the manual_list variable below, and their imdb_codes manually obtained from 
    imdb website. They are then fed into the following functions to perform the same tasks with the ambiguously titled movies'''
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


update_dud_url=[]
update_retrieve_error=[]




def update_on_success(financials_15_df, movie_data, pair, omdb_attrs, imdb_code):
    title = pair[0]
    financials_15_df.loc[financials_15_df['title'] == title, 'imdb_code'] = imdb_code
    keys = ['Actors', 'Director', 'Genre', 'Plot', 'Rated', 'Ratings', 'Runtime', 'Writer', 'Title', 'imdbRating', 'imdbVotes']
    omdb_attrs[imdb_code] = {x:movie_data[x] for x in keys}

def update_get_page(url):
    response=requests.get(url)
    movie_data = json.loads(response.content.decode('utf-8')) 
    return movie_data

def update_make_omdb_dict(financials_15_df, omdb_key, omdb_attrs, zipped_codes):
    '''Similar to preceding main api call function, but called afterwards for those movies that failed due to ambiguous title
    using imdb code instead of title. Easier to use totally new functions due to the different way the url is constructed'''
    for pair in zipped_codes:
        imdb_code = pair[1]
        url = 'http://www.omdbapi.com/?i=' + imdb_code + '&apikey=' + omdb_key
        try:
            movie_data = update_get_page(url)
            update_on_success(financials_15_df, movie_data, pair, omdb_attrs, imdb_code) 
        except:
            update_dud_url.append(pair[0])

     # delete any rows in financials_15yr where there is no imdb_code

    financials_15_df = financials_15_df[financials_15_df.imdb_code != 'No_code']
    return (omdb_attrs, financials_15_df)          
            

def rating_formatter(omdb_attrs):
    '''updates attributes dict returned in above functions by exploding the ratings list, so we have a column for each site'''
    for key in omdb_attrs:
        for k in omdb_attrs[key]['Ratings']:
            outlet_ratings = list(k.values())
            if outlet_ratings[0] == 'Rotten Tomatoes':
                omdb_attrs[key]['RottenRating'] = outlet_ratings[1][:-1]
            elif outlet_ratings[0] == 'Metacritic':
                omdb_attrs[key]['MetacriticRating'] = outlet_ratings[1][:-4]


def clean_values(omdb_attrs):
    '''formats the dictionary for conversion to df '''
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


def make_attributes_df(omdb_attrs):
    '''makes the dataframe of movie metadata from ommdb'''
    rating_formatter(omdb_attrs)
    clean_values(omdb_attrs)
    
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
     

# TMDB API CALLS
def omdb_genre_keywords(financial_attributes_hits_join, tmdb_key, genre):
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
    '''Main function in data anlysis. It takes in a joined base dataframe, any one of its categorical feature, 
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

        