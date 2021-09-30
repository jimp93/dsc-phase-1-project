from selenium import webdriver
from PIL import Image
import os
from os import path
import time
import random
import pandas as pd
import requests
import json
from pprint import pprint
import numpy as np
from wordcloud import WordCloud
from pandasql import sqldf
pysqldf = lambda q: sqldf(q, globals())
import matplotlib.pyplot as plt
import seaborn as sns
%matplotlib inline


# takes in dataframe and 2 columns to produce bar chart using their values
def basic_sns_bar(x, y, title, x_lab, y_lab, file_name, rotation): 
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.set_context('poster')
    sns.barplot(x=x, y=y)
    plt.title(title, y=1.03)
    plt.xticks(rotation=rotation)
    plt.ylabel(y_lab)
    plt.xlabel(x_lab)
    fig.tight_layout()
    plt.savefig(file_name, transparent = True)
    plt.show();

# takes df, desired columns to create lineplot
def lineplotter(df, x_col, y_col, title, x_lab, y_lab, file, h=None):
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.set_context('poster')
    ax = sns.lineplot(data=df, x=x_col, y=y_col, hue=h)
    plt.title(title, y=1.05)
    plt.xlabel(x_lab)
    plt.xticks()
    plt.ylabel(y_lab)
    fig.tight_layout()
    plt.savefig(file, transparent = True);
    return ax


# this takes in a dataframe created by the ranking function and makes it into a bar chart
def rank_seaborn_bar(df, x_col, x_label, title, file_name, invert = False, f=12):
    dfi=df.copy()
    dfi = dfi.reset_index()
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.set_context('poster')
    pal = sns.color_palette("Reds_d", len(dfi['combined_rank']))
    ax=sns.barplot(x=dfi[x_col], y=dfi['combined_rank'], palette=np.array(pal[::-1]))
    if invert == True:
        ax.invert_yaxis()
    plt.title(title, y=1.05)
    plt.xlabel(x_label)
    plt.xticks(rotation=90)
    ax.set_xticklabels(df[x_col], fontsize=f)
    plt.ylabel('Rank')
    fig.tight_layout()
    plt.savefig(file_name, transparent = True)
    return ax;

# makes a grouped bar chart showing number of hits and flops for each genre
def grouped_bar_genre(filtered_concat_gen_df):
    labels = filtered_concat_gen_df['Genre_List'].to_list()
    flop_count = filtered_concat_gen_df['Flop_Counts'].to_list()
    hit_count = filtered_concat_gen_df['Hit_Counts'].to_list()

    x = np.arange(len(labels))  # the label locations
    width = 0.4  # the width of the bars

    fig, ax = plt.subplots(figsize=(12, 10))

    rects1 = ax.barh(x - width/2, hit_count, width, label='Hits')
    rects2 = ax.barh(x + width/2, flop_count, width, label='Flops')

    ax.set_xlabel('Scores', fontsize =17)
    ax.set_title('Number of hits and flops by genre', fontsize = 20, y = 1.03)
    ax.set_yticks(x)
    ax.set_yticklabels(labels, fontsize=17)
    ax.legend()
    plt.savefig(f'flops_v_hits.png', transparent = True)
    fig.tight_layout()
    plt.show()
    
# Make box plot to show the variance in gross profit and loss by genre
def profit_box_plot():
    genre_count = financial_attributes_join.explode('Genre_List')
    both_dic ={}
    for index, row in genre_count.iterrows():
        key = row['Genre_List']
        if key not in both_dic:
            both_dic[key] = []
        both_dic[key].append(row['profit_loss_$']/1000000)
            
    bp_dic = {k:v for k, v in both_dic.items() if len(v)>300}
    labels, data = [*zip(*bp_dic.items())] 
    sns.set_style("whitegrid")
    f, ax = plt.subplots(figsize=(15, 9))
    ax.set_yscale("symlog")
    sns.boxplot(data = data)
    plt.xticks(range(0, len(labels)), labels, rotation = 0, fontsize=17)
    plt.tick_params(axis="x", labelsize=17)
    plt.xlabel('Genre', fontsize=17)
    plt.ylabel('Profit/Loss $m', fontsize=17)
    plt.title('Profit/Loss spread using every film in each genre', y = 1.03, fontsize=20)
    plt.savefig(f'genre-pl-boxplot.png', transparent = True)
    #fig.tight_layout()
    plt.show();

# produces grouped bar showing the gross profits and losses of each genre
def p_l_gross_group_bar(financial_attributes_join):
    df = financial_attributes_join.explode('Genre_List')
    df['Count'] = 1
    df['Profit_Sum'] = np.where(df['profit_loss_$']>0, ((df['profit_loss_$']/1000000)/df['Count']), 0)
    df['Loss_Sum'] = np.where(df['profit_loss_$']<=0, (df['profit_loss_$']/1000000), 0)
    df=df.groupby(['Genre_List']).sum().reset_index()
    df['Profit_Sum'] = df['Profit_Sum']/df['Count']
    df['Loss_Sum'] = df['Loss_Sum']/df['Count']
    df = df[['Genre_List', 'Profit_Sum', 'Loss_Sum']]
    df = df[df['Genre_List'] != 'N/A']
    df = df.sort_values(by='Profit_Sum', ascending=False)
    df=df[:15]
    
    df1 = pd.melt(df, id_vars=['Genre_List'])
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.set_context('poster')
    sns.barplot(x='Genre_List', y= 'value', hue='variable', data=df1)
    plt.title('Mean profits and losses for each genre', y=1.03)
    plt.xticks(rotation=90)
    plt.ylabel('profit/loss $m')
    plt.xlabel('genre')
    plt.savefig('grouped_pl_gross.png', transparent = True)
    ax.set_yscale('symlog')
    plt.legend(loc='upper right')
    plt.show()
df = p_l_gross_group_bar()

# produces bar chart showing mean budget of movies in each genre
def budget_profit_bar(genre_df):
    genre_bud = genre_df.sort_values(by='budget_$', ascending=False)
    genre_bud = genre_bud.reset_index()
    gen_list = genre_bud['Genre_List'].to_list()
    bud_list = genre_bud['budget_$'].to_list()
    bud_list = [x/1000000 for x in bud_list]
    title = 'Mean budget per genre'
    y_lab = 'Budget $m'
    x_lab = 'Genre'
    file_name = 'budget_genre.png'
    basic_sns_bar(gen_list, bud_list, title, x_lab, y_lab, file_name, rotation=90)

# produces lineplot showing returns per budget
def budget_line(financial_attributes_join):
    df = financial_attributes_join.copy()
    for index, row in df.iterrows():
        df.loc[index,'Thriller'] = 'T' if 'Thriller' in row['Genre_List'] else 'NT'
    df['return_%'] = df['return_pct']
    df['budget_$'] = df['budget_$']/1000000
    df=df.sort_values(by='return_%', ascending = False)
    df = df[3:]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.set_context('poster')
    sns.lineplot(x='budget_$', y='return_pct', hue = 'Thriller', data=df)
    plt.title('Budget vs return_%', y=1.03)
    plt.xticks(rotation=90)
    plt.ylabel('return %')
    plt.xlabel('budget $m')
    plt.savefig('budget_pl_scatter.png', transparent = True)
    plt.legend(loc='upper right')
    plt.show()

def budget_sub_scatter(thriller_all_s)
    fig, ax = plt.subplots(figsize=(15, 7))
    sns.set_context('poster')
    sns.scatterplot(x='budget_$', y='return_pct', hue = 'subgenre', data=thriller_all_s)
    plt.title('Budget vs return_%', y=1.03)
    plt.xticks(rotation=90)
    plt.ylabel('return %')
    plt.xlabel('budget $m')
    plt.savefig('budget_pl__sub_scatter.png', transparent = True)
    plt.legend(loc='upper right')
    plt.show()

    
# generates subplots showing relative performance of best peforming crew members in the genre
def graph_generator(top_full_crew_df, crew_column, top_crew_list, crew_type):
    df= dprep.rank_generator(top_full_crew_df, crew_column, top_crew_list)
    df1 = df[[crew_column, 'return % rank', 'gross profit rank', 'rating rank']]
    df1 = pd.melt(df1, id_vars=[crew_column])
    
    fig, ax = plt.subplots(1, 2, figsize=(15, 8))
    fig.suptitle('Bar charts of actors performance rankings and budgets', y=1.05)
    
    sns.set_context('poster')
    sns.barplot(ax=ax[0], x=crew_column, y= 'value', hue='variable', data=df1)
    ax[0].set_title(f'Rank of top {crew_type}', y=1.03)
    ax[0].tick_params(labelrotation=90)
    ax[0].set_ylabel('Rank')
    ax[0].set_xlabel(crew_type)
    ax[0].legend(fontsize = 12, title = None)
    
    df_b = df.copy()
    df_b['budget_$'] = df_b['budget_$']/1000000
    sns.barplot(ax=ax[1], x=crew_column, y= 'budget_$', data=df_b)
    ax[1].set_title(f'Average budget film budget: {crew_type}', y=1.03)
    ax[1].tick_params(labelrotation=90)
    ax[1].set_ylabel('Budget $m')
    ax[1].set_xlabel(crew_type)
    plt.savefig(f'{crew_type}_ranks.png', transparent = True)
    plt.show()

# makes bar plot of profit vx rating classification
def rated(ranked_df):
    x = ranked_df['Rated']
    y = ranked_df['return_pct']
    x_lab= 'rating'
    y_lab= 'return %'
    title =  "Most profitable rating by rank" 
    file_name = 'rated_rank.png'
    rotation = 0
    basic_sns_bar(x, y, title, x_lab, y_lab, file_name, rotation);   
    
# makes scatterplot showing any link between user ratings and profit
 def user_rating_v_profit(financial_attributes_join):
    df=financial_attributes_join.copy()
    df= df.sort_values(by='return_pct', ascending=False)
    df=df[3:]
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.suptitle('User ratings vs profit return %')
    
    sns.set_context('poster')
    ax = sns.regplot(x="mean_rating", y="return_pct", data=df, fit_reg=True)
    ax.set_xlabel('mean rating')
    ax.set_ylabel('return %')
    plt.savefig(f'ratings_return.png', transparent = True);

# makes linplot showing yearly takings trend, overall and by genre
def overall_time_trend(financial_attributes_join):
    df = financial_attributes_join.copy()
    for index, row in df.iterrows():
        if 'Thriller' in row['Genre_List'] and 'Horror' in row['Genre_List']:
            value = (row['worldwide_box_office_$']/1000000)
        else:
            value = 0
        df.loc[index, 'genre_takings'] = value
    df['worldwide_box_office_$']=df['worldwide_box_office_$']/1000000
    df=df.groupby('release_year').sum()
    df=df.reset_index()
    df=df[['release_year', 'worldwide_box_office_$', 'genre_takings']]
    df=df[:15]
    df=df.melt(id_vars=['release_year'])
    ax = lineplotter(df, 'release_year', 'value', 'wordwide takings by genre', 'year', 'total takings $b', 'word_genre_takings.png', h='variable')
    ax.set_yscale('log')
    
# makes ranked bar graph of most profitable films in the genre over last 15 years
def best_genre_films(financial_attributes_join):   
    top_20_df = full_dataframe_maker(['title'], financial_attributes_join, ['Horror', 'Thriller', 'Mystery'])
    top_20_df = top_20_df.sort_values(by = 'return_pct', ascending = False)
    top_20_df['return_p_rank'] = range(1, 1+len(top_20_df))
    
    top_20_df = top_20_df.sort_values(by = 'profit_loss_$', ascending = False)
    top_20_df['gross_prof_rank'] = range(1, 1+len(top_20_df))
    
    top_20_df['combined_rank'] = top_20_df['gross_prof_rank'] + top_20_df['return_p_rank'] 
    all_df = top_20_df.sort_values(by = 'combined_rank')
    
    top_20_df = top_20_df.sort_values(by = 'combined_rank')[:20]
    ax=rank_seaborn_bar(top_20_df, 'title', 'movie title', "Most profitable movies in the genre by rank", 'all_time_rank.png', f=10);

# makes a masked wordcloud of the keywords that appear most often attached to profitable movies in the genre
def wordcloud(text):
    text = " ".join(text)
    mask = np.array(Image.open("../images/zombie.png"))
    wordcloud = WordCloud(background_color="white", width=800, height=400, mask=mask, contour_width=3, min_font_size=10, contour_color='steelblue')
    wordcloud.generate(text)
    wordcloud.to_file("../ghost.png")
    fig, ax = plt.subplots(figsize=(25, 20))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.figure()
    plt.imshow(mask, cmap=plt.cm.gray, interpolation='bilinear')
    plt.axis("off")
    plt.show()