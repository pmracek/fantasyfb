# Databricks notebook source

# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import scipy.stats as st
input = {
    'season' : '2018'
    ,'tophalfweight' : .76
}
pd.options.display.max_rows = 200


# %%
df = pd.read_csv('data/'+input['season']+'_00_matchup_recap.txt', header=0)

scores = df.loc[df['SEASON']==int(input['season'])][['TEAMNAME','SCORINGPERIOD','SCORE','OUTCOME']]

scores['ACTUAL'] = scores.apply(lambda row: row.OUTCOME == 'W', axis=1)
scores['EXPECTED'] = scores['SCORE'].to_frame().apply(st.zscore, ddof=1).apply(st.norm.cdf)
scores['EXPECTED_TOPHALF'] = scores.apply(lambda row: row.EXPECTED > .5 , axis=1)  # top half of season long scores.  needs to be by week 
#AVG overwieghts the TOPHALF
scores['EXPECTED_WEIGHTED'] = (scores['EXPECTED']*(1-input['tophalfweight']))+(scores['EXPECTED_TOPHALF']*input['tophalfweight'])

exp_wins = scores.groupby('TEAMNAME').sum()[['ACTUAL','EXPECTED','EXPECTED_TOPHALF','EXPECTED_WEIGHTED']]
#exp_wins = scores.groupby('TEAMNAME').sum()[['ACTUAL','EXPECTED','EXPECTED_TOPHALF']]
exp_wins['LUCK_EXPECTED']=exp_wins['ACTUAL']-exp_wins['EXPECTED']
exp_wins['LUCK_TOPHALF']=exp_wins['ACTUAL']-exp_wins['EXPECTED_TOPHALF']
exp_wins['LUCK_WEIGHTED']=exp_wins['ACTUAL']-exp_wins['EXPECTED_WEIGHTED']


# %%
exp_wins[['ACTUAL','EXPECTED','LUCK_EXPECTED','LUCK_TOPHALF','LUCK_WEIGHTED']].sort_values('LUCK_WEIGHTED')


# %%
scores[scores['SCORINGPERIOD']==scores['SCORINGPERIOD'].max()][['TEAMNAME','SCORE','OUTCOME','EXPECTED','EXPECTED_TOPHALF','EXPECTED_WEIGHTED']].sort_values('EXPECTED_WEIGHTED', ascending=False)


# %%
h2h = df.groupby(['TEAMNAME','OPPONENTNAME', 'OUTCOME'])['OUTCOME'].count().unstack().fillna(0)


# %%
scores.sort_values('EXPECTED', ascending=False)


# %%
plt.close()
scores.hist(column=['SCORE'], bins=20)
plt.show()


# %%
df = pd.DataFrame({
     'length': [1.5, 0.5, 1.2, 0.9, 3],
     'width': [0.7, 0.2, 0.15, 0.2, 1.1]
     }, index= ['pig', 'rabbit', 'duck', 'chicken', 'horse'])
hist = df.hist(bins=3)


# %%



# %%



