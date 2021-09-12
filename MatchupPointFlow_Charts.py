# Databricks notebook source
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.dates as md
import pandas as pd
import numpy as np
from pandas.io.json import json_normalize
from datetime import datetime,date,timedelta

import pytz 
#from bs4 import BeautifulSoup
import requests
import io

params = {
'token' : 'jgyuNE4NXwPdjzmQS568me3TyXLAL9ZCU9NkVlKj'
,'bot_id' :'4e93908dd6e03b66cbd07fc458' #Test
}

leagueId = '111414'
season = datetime.now().astimezone(pytz.timezone('US/Eastern')).year

r = requests.get('http://www.nfl.com/liveupdate/scorestrip/ss.xml')
#schedxml = BeautifulSoup(r.text, "html.parser")
week = 1 #schedxml.find('gms')['w']

# Only run if there is an active NFL game
def _is_nfl_game_active(debug=False):
    #https://site.api.espn.com/apis/fantasy/v2/games/ffl/games
    #json.events[0].status == pre or post then false.  else true
    #seems to only give current week games.
    nflgames = requests.get("https://site.api.espn.com/apis/fantasy/v2/games/ffl/games").json()
    for game in nflgames['events']:
        if game['status'] not in ['pre','post']:
            return True
    if(debug):
      return True
    return False

# COMMAND ----------

# In[60]:


def _last_game_ended_recently():
    r = requests.get('http://www.nfl.com/liveupdate/scorestrip/ss.xml')
    #schedxml = BeautifulSoup(r.text, "html.parser")
    schedxml = {}
    
    last_game_end_utc_ts = pytz.utc.localize(datetime(2000, 1, 1, 0, 0))

    for info in schedxml.findAll('g'):
        hour, minute = info['t'].strip().split(':')
        d = datetime(int(info['eid'][:4]), int(info['eid'][4:6]), int(info['eid'][6:8]),
                              (int(hour) + 12) % 24, int(minute)).astimezone(pytz.timezone('US/Eastern'))
        if(d.hour == 21 and d.minute == 30): #Saturday 9:30am games need to be adjusted from PM to AM
            d = d - timedelta(hours=12)
        
        d = d.astimezone(pytz.timezone('UTC')) #convert to UTC for AWS Lambda environment
        
        current_utc_ts = pytz.utc.localize(datetime.utcnow())

        if(current_utc_ts.date()==d.date()): 
            last_game_end_utc_ts = d + timedelta(hours=4.5)

    return current_utc_ts<=last_game_end_utc_ts

# COMMAND ----------

# In[61]:


def generate_charts():
    columns = ['COLLECTTIMESTAMP','TEAM1','TEAM1NAME','TEAM1PTS','TEAM1PROJ','TEAM2NAME','TEAM2PTS','TEAM2PROJ','SCORINGPERIOD']
    data = spark.read.table("pm_fantasyfb.matchup_flow").select(columns)

    df = data.toPandas()
    df = df[df['SCORINGPERIOD']==week].sort_values('COLLECTTIMESTAMP', ascending=True)
    
    df[['TEAM1PTS','TEAM1PROJ','TEAM2PTS','TEAM2PROJ']] = df[['TEAM1PTS','TEAM1PROJ','TEAM2PTS','TEAM2PROJ']].apply(pd.to_numeric)


    imgs = []
    for home_team in df['TEAM1NAME'].unique():
        matchup = df[df['TEAM1NAME']==home_team]
        team1 = matchup['TEAM1NAME'].unique()[0]
        team2 = matchup['TEAM2NAME'].unique()[0]

        fig, ax = plt.subplots(1,1)

        plt.title(team1+' vs. '+team2+'\nWeek '+str(week))
        #ax.xaxis.set_minor_locator(md.HourLocator(interval=4))   # every 4 hours
        #ax.xaxis.set_minor_formatter(md.DateFormatter('%H:%M'))  # hours and minutes
        #ax.xaxis.set_major_locator(md.HourLocator(interval=12))    # every day
        #ax.xaxis.set_major_formatter(md.DateFormatter('\n%a'))
        #ax.set_xlim(datetime(2018, 10, 1, 20), datetime(2018, 10, 2 , 0))
        ax.xaxis.set_major_locator(plt.NullLocator())
        
        line_t1pts, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM1PTS'], 'r', label=matchup['TEAM1NAME'].unique()[0]+' PTS')
        line_t1proj, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM1PROJ'], 'r',linestyle='--', dashes=(2, 2), label=matchup['TEAM1NAME'].unique()[0]+' PROJ')
        line_t2pts, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM2PTS'], 'b', label=matchup['TEAM2NAME'].unique()[0]+' PTS')
        line_t2proj, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM2PROJ'], 'b',linestyle='--', dashes=(2, 2), label=matchup['TEAM2NAME'].unique()[0]+' PROJ')
        ax.legend(loc='best')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        imgs.append(buf)
        #plt.show()
        plt.close()
    return imgs


# COMMAND ----------

# In[62]:


def post_to_groupme(input, imgs):
    headers_img = {
        'X-Access-Token': input['token'],
        'Content-Type': 'image/jpeg',
    }

    headers_post = {
        'Content-Type': 'application/json',
    }

    for img in imgs:
        img.seek(0)
        img = requests.post('https://image.groupme.com/pictures', headers=headers_img, data=img)
        imgurl = img.json()['payload']['picture_url']
        data = '{"bot_id":"'+input['bot_id']+'","text":"","attachments":[{"type":"image","url":"'+imgurl+'"}]}'
        response = requests.post('https://api.groupme.com/v3/bots/post', headers=headers_post, data=data)

# COMMAND ----------

# In[63]:


def lambda_handler(input,context):
    #if not _is_nfl_game_active() and not _last_game_ended_recently():
    #    return False
    
    post_to_groupme(input, generate_charts())
    return True

# COMMAND ----------

lambda_handler(params,None)


# COMMAND ----------

columns = ['COLLECTTIMESTAMP','TEAM1','TEAM1NAME','TEAM1PTS','TEAM1PROJ','TEAM2NAME','TEAM2PTS','TEAM2PROJ','SCORINGPERIOD']
data = spark.read.table("pm_fantasyfb.matchup_flow").select(columns)

display(data)

# COMMAND ----------

columns = ['COLLECTTIMESTAMP','TEAM1','TEAM1NAME','TEAM1PTS','TEAM1PROJ','TEAM2NAME','TEAM2PTS','TEAM2PROJ','SCORINGPERIOD']
data = spark.read.table("pm_fantasyfb.matchup_flow").select(columns)

df = data.toPandas()
df = df[df['SCORINGPERIOD']==week].sort_values('COLLECTTIMESTAMP', ascending=True)

df[['TEAM1PTS','TEAM1PROJ','TEAM2PTS','TEAM2PROJ']] = df[['TEAM1PTS','TEAM1PROJ','TEAM2PTS','TEAM2PROJ']].apply(pd.to_numeric)
display(df)

# COMMAND ----------


