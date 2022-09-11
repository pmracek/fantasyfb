# Databricks notebook source
dbutils.widgets.text("bot_id", "4e93908dd6e03b66cbd07fc458", "Groupme Bot ID")
dbutils.widgets.text("leagueId", "111414", "League ID")

# COMMAND ----------

import matplotlib.pyplot as plt
import matplotlib.dates as md
from matplotlib.ticker import FuncFormatter

import seaborn as sns
import requests
import pandas as pd

import numpy as np
from datetime import datetime,date,timedelta



import pytz 
#from bs4 import BeautifulSoup
import io

params = {
'token' : 'jgyuNE4NXwPdjzmQS568me3TyXLAL9ZCU9NkVlKj'
,'bot_id' : dbutils.widgets.get("bot_id")
#,'bot_id' :'4e93908dd6e03b66cbd07fc458' #Test 
#,'bot_id' :'da0beb9ba4b78d5a57a2ed6dd4' #Prod
}

leagueId = dbutils.widgets.get("leagueId")
season = datetime.now().astimezone(pytz.timezone('US/Eastern')).year

colors = {
 1: 'darkred',
 2: 'maroon',
 3: 'firebrick',
 4: 'red',
 5: 'indianred',
 6: 'lightcoral',
 7: 'lightgray',
 8: 'silver',
 9: 'darkgray',
 10: 'gray',
 11: 'dimgray',
 12: 'black'}

# COMMAND ----------

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
    return False# In[60]:


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


def generate_charts():
    ### Prepare data frame
    columns_tm1 = ['COLLECTTIMESTAMP','TEAM1NAME','TEAM1PTS','TEAM1PROJ','SCORINGPERIOD']
    tm1 = (spark.read.table("pm_fantasyfb.matchup_flow")
             .select(columns_tm1)
             .where("collecttimestamp > timestamp '2022-09-08 00:00:00'")
             .withColumnRenamed("TEAM1NAME","TEAMNAME")
             .withColumnRenamed("TEAM1PTS","PTS")
             .withColumnRenamed("TEAM1PROJ","PROJ")
          )

    columns_tm2 = ['COLLECTTIMESTAMP','TEAM2NAME','TEAM2PTS','TEAM2PROJ','SCORINGPERIOD']
    tm2 = ( spark.read.table("pm_fantasyfb.matchup_flow")
             .select(columns_tm2)
             .where("collecttimestamp > timestamp '2022-09-08 00:00:00'")
             .withColumnRenamed("TEAM2NAME","TEAMNAME")
             .withColumnRenamed("TEAM2PTS","PTS")
             .withColumnRenamed("TEAM2PROJ","PROJ")
          )
    
    top_half = spark.sql("""
      SELECT 
        TEAMNAME
        , RANK
        , CASE WHEN RANK <= 6 THEN 1 ELSE 0 END AS TOPHALF
      FROM (
        SELECT COLLECTTIMESTAMP
          , TEAMNAME
          , PROJ
          , RANK() OVER (PARTITION BY COLLECTTIMESTAMP ORDER BY PROJ DESC) AS RANK
        FROM (
            select COLLECTTIMESTAMP, TEAM1NAME AS TEAMNAME, TEAM1PROJ AS PROJ 
            from pm_fantasyfb.matchup_flow
            union all
            select COLLECTTIMESTAMP, TEAM2NAME AS TEAMNAME, TEAM2PROJ AS PROJ 
            from pm_fantasyfb.matchup_flow
        )
        WHERE COLLECTTIMESTAMP = (SELECT MAX(COLLECTTIMESTAMP) FROM pm_fantasyfb.matchup_flow WHERE SCORINGPERIOD = 1)
      )
    """)
    
    data = tm1.unionAll(tm2).join(top_half,on="TEAMNAME")

    df = data.toPandas()
    df = df[df['SCORINGPERIOD']==week].sort_values(['COLLECTTIMESTAMP','RANK'], ascending=True)
    
    df[['PTS','PROJ']] = df[['PTS','PROJ']].apply(pd.to_numeric)

    ##### Prepare chart / image
    imgs = []

    fig = plt.figure()
    ax = plt.subplot(111)
    
    N = len(df['COLLECTTIMESTAMP'].unique())
    ind = np.arange(N)
        
    def format_timestamps_major(x, pos=None):
        thisind = np.clip(int(x + 0.5), 0, N - 1)
        ts_df = pd.Series(df['COLLECTTIMESTAMP'].unique())
        return ts_df.iloc[thisind].strftime('%a %I:%M %p')
        
    formatter = FuncFormatter(format_timestamps_major)
    ax.xaxis.set_major_formatter(formatter)
    fig.autofmt_xdate()
    
    for t in df.TEAMNAME.unique():
      plt_df = df[df["TEAMNAME"]==t]
      color = 'red' if plt_df.TOPHALF.max() == 1 else 'silver'
      ax.plot(ind, plt_df["PROJ"], label=t, c=plt_df['RANK'].map(colors).max())

    #Shrink current axis by 20%
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.9, box.height])

    # Put a legend to the right of the current axis
    ax.legend(loc='center left', bbox_to_anchor=(1, .5))
    plt.title("MUF - Projected Points")
    #plt.show()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='white', edgecolor='none')
    buf.seek(0)

    imgs.append(buf)

    plt.show()
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


