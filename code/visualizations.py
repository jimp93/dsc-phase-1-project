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
import matplotlib.pyplot as plt
import seaborn as sns
import code.data_preparation as dprep


def seaborn_bar(df, x_col, y_col, x_label, y_label, title, file_name, invert = False, f=18, rotation=45):
    '''takes in a dataframe created by the feature v financial function and turns it into a bar chart,
    feature on the x axis and financial columns on the y axis'''
    dfi=df.copy()
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.set_context('poster')  
    pal = sns.color_palette("Spectral", len(dfi[y_col]))
    pal.reverse()
    if x_col=='Run_Time':
        ax=sns.barplot(x=dfi[x_col], y=dfi[y_col], color='red')
    else:
        ax=sns.barplot(x=dfi[x_col], y=dfi[y_col], palette=np.array(pal[::-1]))
    
    if invert == True:
        ax.invert_yaxis()
    plt.title(title, y=1.05)
    plt.xlabel(x_label, fontsize=20)
    plt.xticks(rotation=rotation, ha="right", rotation_mode="anchor", fontsize=20)
    ax.set_xticklabels(df[x_col], fontsize=f)
    plt.ylabel(y_label, fontsize=20)
    fig.tight_layout()
    plt.savefig(file_name);
    return ax


def budget_sub_scatter(df, genre):
    '''returns scatterplot of budget v profit for the genre passed in, with marks coloured by subgenre'''
    fig, ax = plt.subplots(figsize=(15, 7))
    sns.set_context('poster')
    sns.scatterplot(x='budget_$', y='profit_loss_$', hue = 'subgenre', data=df)
    plt.title('Budget vs Profit/Loss', y=1.03)
    plt.xticks(rotation=90, fontsize=17)
    plt.yticks(rotation=90, fontsize=17)
    plt.ylabel('Profit/Loss $m', fontsize=20)
    plt.xlabel('Budget $m', fontsize=20)
    plt.legend(loc='upper right')
    plt.savefig(f'images/{genre}_budget_pl_sub_scatter.png', bbox_inches = "tight")
    plt.show()


def graph_generator(top_full_crew_df, crew_column, top_crew_list, crew_type, gen):
    ''' generates subplots showing relative performance of best peforming crew members in the genre'''
    df= dprep.rank_generator(top_full_crew_df, crew_column, top_crew_list)
    df1 = df[[crew_column, 'return % rank', 'gross profit rank', 'rating rank']]
    df1 = pd.melt(df1, id_vars=[crew_column])
    
    fig, ax = plt.subplots(1, 2, figsize=(15, 8))
    fig.suptitle(f'Bar Charts of {crew_type} Overall Performance Rankings and Budgets', y=1.05, fontsize=22)
    
    sns.set_context('poster')
    sns.barplot(ax=ax[0], x=crew_column, y= 'value', hue='variable', data=df1)
    ax[0].set_title(f'Rank of Top {crew_type}', y=1.03)
    ax[0].tick_params(labelrotation=90, labelsize=17)
    ax[0].set_ylabel('Rank', fontsize=20)
    ax[0].set_xlabel(crew_type, fontsize=20)
    ax[0].legend(fontsize = 15, title = None)
    
    df_b = df.copy()
    df_b['budget_$'] = df_b['budget_$']/1000000
    sns.barplot(ax=ax[1], x=crew_column, y= 'budget_$', data=df_b)
    ax[1].set_title(f'Average Film Budget: {crew_type}', y=1.03)
    ax[1].tick_params(labelrotation=90, labelsize=17)
    ax[1].set_ylabel('Budget $m', fontsize=20)
    ax[1].set_xlabel(crew_type, fontsize=20)
    plt.savefig(f'images/{gen}_{crew_type}_ranks.png', bbox_inches = "tight")
    plt.show() 
 