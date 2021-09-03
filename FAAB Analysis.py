# Databricks notebook source
# # To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import pandas as pd
import numpy as np
import scipy.stats as st
import glob
import os
path = r'data'  
input = {
    'season':'2018'
}


# %%
faab_files = glob.glob(os.path.join(path, "2018*faab*.txt"))
faab_dfs = (pd.read_csv(f) for f in faab_files)
faab_results   = pd.concat(faab_dfs, ignore_index=True)
faab_added = faab_results[faab_results['BIDRESULT']=='Added'][['TEAMNAME','TEAM','PLAYERNAME','PLAYERID','BID']]
pd.to_numeric(faab_added['BID'])
faab_added.BID.replace(0,1,inplace=True)  #zero bids screw up our PTSPERDOLLAR calc later
faab_totals = faab_added.groupby(['TEAMNAME','TEAM','PLAYERNAME','PLAYERID'], axis=0)                         .agg({'BID':sum})                         .reset_index()


# %%
boxscore_files = glob.glob(os.path.join(path, "2018*quickbox*.txt"))
boxscore_dfs = (pd.read_csv(f) for f in boxscore_files)
boxscores   = pd.concat(boxscore_dfs, ignore_index=True)
boxscores.replace(to_replace='--', value=0, inplace=True, axis=None)
boxscores['PLAYERPOINTS'] = boxscores['PLAYERPOINTS'].astype('float64')
boxscores['STARTED'] = boxscores.apply(lambda row: row.SLOT !='Bench', axis=1)

boxscore_totals = boxscores[['TEAM','TEAMNAME','STARTED','PLAYERID','PLAYERNAME','PLAYERPOINTS']]                     .groupby(['TEAMNAME','TEAM','STARTED','PLAYERNAME','PLAYERID'], axis=0)                     .agg([sum,'count','mean'])                     .rename(columns={'sum':'TOTAL_PTS','count':'WEEKS','mean':'AVG_PTS'})                     .reset_index()

starter_pts = boxscores[boxscores['SLOT']!='Bench'][['TEAM','TEAMNAME','SLOT','PLAYERID','PLAYERNAME','PLAYERPOINTS']]
starter_totals = starter_pts.groupby(['TEAMNAME','TEAM','PLAYERNAME','PLAYERID','SLOT'], axis=0)                             .agg([sum,'count','mean'])                             .rename(columns={'sum':'TOTAL_PTS','count':'WEEKS','mean':'AVG_PTS'})                             .reset_index()

#Flatten MultiIndex choosing either group-by column or aggregated column name. 
boxscore_totals.columns = ['%s' % (b if b else a) 
                           for a, b in boxscore_totals.columns]

starter_totals.columns = ['%s' % (b if b else a) 
                           for a, b in starter_totals.columns]


# %%
players_file = glob.glob(os.path.join(path, "2018*players*.txt"))
players = pd.read_csv(players_file[0])


# %%
result = pd.merge(boxscore_totals,
                  faab_totals,                 
                  left_on=['TEAM','PLAYERID'],
                  right_on=['TEAM','PLAYERID'],
                  suffixes=('', '_y'))

result = pd.merge(result
                 ,players
                 ,left_on=['PLAYERID']
                 ,right_on=['PLAYERID']
                 ,suffixes=('','_P'))

result['PTSPERDOLLAR'] = result['TOTAL_PTS'] / result['BID'] # if result['BID'] > 0 else result['PLAYERPOINTS']

result = result[['TEAMNAME','PLAYERNAME','STARTED','TOTAL_PTS','POS','BID','PTSPERDOLLAR','WEEKS','AVG_PTS']]

       
result['RANK_PTS'] = result.groupby(['POS','STARTED'])['TOTAL_PTS']              .rank(method='dense',axis=0,ascending=False)  
        
result['RANK_PTS_PER_DOLLAR'] = result.groupby(['POS','STARTED'])['PTSPERDOLLAR']              .rank(method='dense',axis=0,ascending=False) 

result['RANK_WEEKS'] = result.groupby(['POS','STARTED'])['WEEKS']              .rank(method='dense',axis=0,ascending=False) 
        
result['RANK_AVG_PTS'] = result.groupby(['POS','STARTED'])['AVG_PTS']              .rank(method='dense',axis=0,ascending=False) 


# %%
df = result[['POS','STARTED','RANK_PTS','RANK_PTS_PER_DOLLAR','RANK_WEEKS','RANK_AVG_PTS','PLAYERNAME','TEAMNAME','TOTAL_PTS','BID','PTSPERDOLLAR','WEEKS','AVG_PTS']]         .sort_values(['POS','STARTED','RANK_PTS'],ascending=[False,False,True])

df_ppd = df[['POS','STARTED','RANK_PTS_PER_DOLLAR','PLAYERNAME','TEAMNAME','TOTAL_PTS','BID','PTSPERDOLLAR']]         .sort_values(['POS','STARTED','RANK_PTS_PER_DOLLAR'],ascending=[False,False,True])
    
df_raw_pts = df[['POS','STARTED','RANK_PTS','RANK_AVG_PTS','PLAYERNAME','TEAMNAME','TOTAL_PTS','WEEKS','AVG_PTS']]         .sort_values(['POS','STARTED','RANK_PTS'],ascending=[False,False,True])

df_weeks = df[['POS','STARTED','RANK_WEEKS','PLAYERNAME','TEAMNAME','TOTAL_PTS','BID','PTSPERDOLLAR','WEEKS','AVG_PTS']]         .sort_values(['POS','STARTED','RANK_WEEKS'],ascending=[False,False,True])

df_summary = df[(df['RANK_PTS_PER_DOLLAR']<=10) | (df['RANK_PTS']<=10)]         .sort_values(['POS','STARTED','RANK_PTS_PER_DOLLAR'], ascending=[False,False,True])

#df[(df['RANK_WEEKS']<=5) & (df['POS']=='QB')].sort_values('RANK_WEEKS')


# %%
writer = pd.ExcelWriter('data/2018_faab_and_player_results_data.xlsx')
df.to_excel(writer,'ALL',index=False)
df_summary.to_excel(writer,'LEADERBOARD',index=False)
df_ppd.to_excel(writer,'PTS_PER_DOLLAR',index=False)
df_raw_pts.to_excel(writer,'RAW_POINTS',index=False)
df_weeks.to_excel(writer,'WEEKS',index=False)
writer.save()


# %%
result = pd.merge(faab_results
                 ,players
                 ,left_on=['PLAYERID']
                 ,right_on=['PLAYERID']
                 ,suffixes=('','_P'))

writer = pd.ExcelWriter('data/2018_faab_past_bids_by_pos.xlsx')
result.to_excel(writer,'ALL',index=False)
writer.save()
#result[result['POS']=='WR'].sort_values(['BID'], ascending=False)


# %%




# COMMAND ----------


