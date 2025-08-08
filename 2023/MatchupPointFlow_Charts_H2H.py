# Databricks notebook source
dbutils.widgets.text("bot_id", "4e93908dd6e03b66cbd07fc458", "Groupme Bot ID")
dbutils.widgets.text("leagueId", "111414", "League ID")
dbutils.widgets.text("week", "3", "Week")
dbutils.widgets.dropdown("show_charts", "False", ["False","True"])
dbutils.widgets.dropdown("force_charts", "False", ["False","True"])

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

def get_week():
  if dbutils.widgets.get("week") == "":
    week = spark.sql("""
          select SEASON, SCORINGPERIOD
          FROM 
          (
          select SEASON, SCORINGPERIOD, ROW_NUMBER() OVER (ORDER BY SEASON DESC, SCORINGPERIOD DESC) RN
          from pmracek.pm_fantasyfb.matchup_flow 
          )
          WHERE RN = 1
          """).collect()[0]['SCORINGPERIOD']
  else:
    week = dbutils.widgets.get("week")
  return week

week = get_week()

spark.sql("SET TIME ZONE 'America/New_York'")

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

def str_to_bool(value):
  FALSE_VALUES = ['false', 'no', '0']
  TRUE_VALUES = ['true', 'yes', '1']
  lvalue = str(value).lower()
  if lvalue in (FALSE_VALUES): return False
  if lvalue in (TRUE_VALUES):  return True
  raise Exception("String value should be one of {}, but got '{}'.".format(FALSE_VALUES + TRUE_VALUES, value))

show_charts = str_to_bool(dbutils.widgets.get("show_charts"))
force_charts = str_to_bool(dbutils.widgets.get("force_charts"))

# COMMAND ----------

r = requests.get('http://www.nfl.com/liveupdate/scorestrip/ss.xml')
#schedxml = BeautifulSoup(r.text, "html.parser")



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

def get_muf_data(scoringperiod):
  columns = ['COLLECTTIMESTAMP','TEAM1','TEAM1NAME','TEAM1PTS','TEAM1PROJ','TEAM2NAME','TEAM2PTS','TEAM2PROJ','SCORINGPERIOD']
  data = spark.read.table("pmracek.pm_fantasyfb.matchup_flow").select(columns).where("SCORINGPERIOD == {} and season = {}".format(scoringperiod, season)).orderBy("COLLECTTIMESTAMP")

  df = data.toPandas()
  #df = df[df['SCORINGPERIOD']==week].sort_values('COLLECTTIMESTAMP', ascending=True)

  df[['TEAM1PTS','TEAM1PROJ','TEAM2PTS','TEAM2PROJ']] = df[['TEAM1PTS','TEAM1PROJ','TEAM2PTS','TEAM2PROJ']].apply(pd.to_numeric)
  return df

# COMMAND ----------

   
def generate_charts(df, force=False, show=False):    
    imgs = []
    for home_team in df['TEAM1NAME'].unique():
        matchup = df[df['TEAM1NAME']==home_team]
        team1 = matchup['TEAM1NAME'].unique()[0]
        team2 = matchup['TEAM2NAME'].unique()[0]
        
        #Thursday night and no one has scored any points yet
        if matchup['TEAM1PTS'].tail(1).item() == 0 and matchup['TEAM2PTS'].tail(1).item() == 0 and not force:
          continue
        
        #Monday night -- and maybe Sunday night -- if both teams are done.
        if matchup['TEAM1PTS'].tail(1).item() == matchup['TEAM1PROJ'].tail(1).item() \
              and matchup['TEAM2PTS'].tail(1).item() == matchup['TEAM2PROJ'].tail(1).item() \
              and not force:
           continue
        
        fig, ax = plt.subplots(1,1)

        plt.title(team1+' vs. '+team2+'\nWeek '+str(week))

        N = len(matchup['COLLECTTIMESTAMP'])
        ind = np.arange(N)
        
        def format_timestamps_major(x, pos=None):
          thisind = np.clip(int(x + 0.5), 0, N - 1)
          return matchup['COLLECTTIMESTAMP'].iloc[thisind].strftime('%a %I:%M %p')
        
        formatter = FuncFormatter(format_timestamps_major)
        ax.xaxis.set_major_formatter(formatter)
        fig.autofmt_xdate()
        
        
        line_t1pts, = ax.plot(ind, matchup['TEAM1PTS'], 'r', label=matchup['TEAM1NAME'].unique()[0]+' PTS')
        line_t1proj, = ax.plot(ind, matchup['TEAM1PROJ'], 'r',linestyle='--', dashes=(2, 2), label=matchup['TEAM1NAME'].unique()[0]+' PROJ')
        line_t2pts, = ax.plot(ind, matchup['TEAM2PTS'], 'b', label=matchup['TEAM2NAME'].unique()[0]+' PTS')
        line_t2proj, = ax.plot(ind, matchup['TEAM2PROJ'], 'b',linestyle='--', dashes=(2, 2), label=matchup['TEAM2NAME'].unique()[0]+' PROJ')

        
        ax.legend(loc='best')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='white', edgecolor='none') 
        buf.seek(0)
        imgs.append(buf)
        if show:
          plt.show()
        plt.close()
    return imgs


# COMMAND ----------

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


#if not _is_nfl_game_active() and not _last_game_ended_recently():
#    return False

#if not _is_nfl_game_active():
#    return False
df = get_muf_data(week)
imgs = generate_charts(df,show=False, force=False)
post_to_groupme(params, imgs)


# COMMAND ----------

show_charts = str_to_bool(dbutils.widgets.get("show_charts"))
force_charts = str_to_bool(dbutils.widgets.get("force_charts"))

imgs = generate_charts(df,show=show_charts, force=force_charts)

# COMMAND ----------


