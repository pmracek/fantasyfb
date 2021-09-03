# Databricks notebook source
# 
# # To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import time, re, csv
from bs4 import BeautifulSoup
from datetime import datetime
import requests

def save_file(season,wk,file,data):
    with open('data/'+str(season)+'_'+str(wk)+'_'+str(file)+'.txt', 'w', newline = '\n') as f:
            writer = csv.writer(f)
            writer.writerows(data)

input = {
    'leagueId' : '111414'
    ,'season' : '2018'
}

# COMMAND ----------
# %%
positions = (('QB',0,150),('RB',2,350),('WR',4,450),('TE',6,250),('DEF',16,0),('K',17,50),('DL',11,250),('LB',10,250),('DB',14,250))
players = [('POS','PLAYERID','NAME','NFLTEAM')]

for pos in positions:
    position = pos[0]
    category = str(pos[1])
    curstartindex = 0
    maxstartindex = pos[2]

    while curstartindex<=maxstartindex:	
        url = 'http://games.espn.go.com/ffl/freeagency'
        r = requests.get(url,
                    params={'leagueId': input['leagueId']
                            , 'seasonId': input['season']
                            , 'teamId':'12'
                            , 'avail':'-1'
                            , 'slotCategoryId': category
                            , 'startIndex' : str(curstartindex)
                           })
        #r = s.post(url)
        soup = BeautifulSoup(r.text, "html.parser")

        for playerRow in soup(id=re.compile("plyr")):
            id = re.search('plyr(?P<pid>\d+)', playerRow.attrs['id']).group('pid')
            name = playerRow.td.a.text
            teamabbr = re.search(',?\s+(?P<team>\w+)', playerRow.td.contents[1]).group('team') #RE = 0-1 comma followed by 1+ space
            players.append((position, id , name , teamabbr ))
        curstartindex += 50

save_file(input['season'],'00','players',players)

# COMMAND ----------
# %%



