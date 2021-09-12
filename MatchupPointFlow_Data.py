# Databricks notebook source
dbutils.widgets.dropdown("debug", "False", ["True","False"], "Debug")
dbutils.widgets.text("leagueId", "111414", "League ID")

# COMMAND ----------

import requests
from datetime import datetime 

from pytz import timezone
from decimal import Decimal
import json
import pandas as pd
import pyspark.sql.functions as F


season = datetime.now().astimezone(timezone('US/Eastern')).year

def game_slot(ts):
    day = ts.strftime('%A')
    gameslot = '' 
    if ts.hour <= 15: 
        gameslot = 'Early'
    elif ts.hour <= 19:
        gameslot = 'Late'
    else:
        gameslot = 'Night'
    return gameslot+' '+day

pre2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell'}
t2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Doogs'}
t2011 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'JonBurriss'}
t2012 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Paul'}
t2016 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Goss', '11':'Tony', '12':'Paul'}


teams = {2008:pre2010, 2009:pre2010, 2010:t2010, 2011:t2011, 2012:t2012, 2013:t2012, 2014:t2012, 2015:t2012, 2016:t2016, 2017:t2016, 2018:t2016, 2019:t2016, 2020:t2016, 2021:t2016}



# COMMAND ----------

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

#IMPORTANT: can only look at current or future weeks.  
#should add query param for matchupPeriodId and change class scraping logic if weeks has a declared winner 
#(even on default scoreboard like on Tuesdays).  Matchup box has different class names in that case.  
#Not a high priority since I use NFL feed to verify that at least one game is in progress before getting into this method.
    
def save_matchup_data(input):
    # https://fantasy.espn.com/apis/v3/games/ffl/seasons/2020/segments/0/leagues/111414?view=modular&view=mNav&view=mMatchupScore&view=mScoreboard&view=mSettings&view=mTopPerformers&view=mTeam
    url = "https://fantasy.espn.com/apis/v3/games/ffl/seasons/" + \
            str(season) + "/segments/0/leagues/" + str(input['leagueId'])
    
    matchupPeriodIds = []
    # https://fantasy.espn.com/apis/v3/games/ffl/seasons/2020/segments/0/leagues/111414?view=mMatchupScore&view=mMatchup
    matchupData = requests.get(url, cookies = None, params = { 'view' : 'mMatchupScore', 'view' : 'mMatchup' }).json()
    week = matchupData['scoringPeriodId']
    
    for m in matchupData['schedule']:
        if m['matchupPeriodId'] == week:
            matchupPeriodIds.append(m['id'])

    matchupData = requests.get(url, cookies = None, params = { 'view' : 'mMatchupScore', 'view' : 'mScoreboard'}).json()
    
    matchups = []
    for matchup in matchupData['schedule']:
        if matchup['id'] not in matchupPeriodIds:
            continue

        team1 = matchup['home']
        team2 = matchup['away']

        result = {
            'SEASON':season
            ,'SCORINGPERIOD':week
            ,'WEEK_NM':week
            ,'COLLECTDATE':datetime.now().strftime('%Y-%m-%d')
            ,'DAYOFWEEK':datetime.now().strftime('%a')
            ,'GAMESLOT':game_slot(datetime.now())
            ,'COLLECTTIMESTAMP':datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ,'TEAM1':str(team1['teamId'])
            ,'TEAM1NAME':teams[int(season)][str(team1['teamId'])]
            ,'TEAM1PTS':team1['totalPointsLive']
            ,'TEAM1PROJ':round(team1['totalProjectedPointsLive'], 1)
            ,'TEAM1YETTOPLAY':-1
            ,'TEAM1INPLAY':-1
            ,'TEAM1MINREMAINING':-1
            ,'TEAM1TOPSCORER':'UNKNOWN'
            ,'TEAM2':team2['teamId']
            ,'TEAM2NAME':teams[int(season)][str(team2['teamId'])]
            ,'TEAM2PTS':team2['totalPointsLive']
            ,'TEAM2PROJ':round(team2['totalProjectedPointsLive'],1)
            ,'TEAM2YETTOPLAY':-1
            ,'TEAM2INPLAY':-1
            ,'TEAM2MINREMAINING':-1
            ,'TEAM2TOPSCORER':'UNKNOWN'
            ,'LEAGUEID':input['leagueId']
        }
        matchups.append(result)
        
    matchup_pdf = pd.DataFrame.from_records(matchups)
    matchup_pdf['COLLECTTIMESTAMP']= pd.to_datetime(matchup_pdf['COLLECTTIMESTAMP'])
    matchup_df = spark.createDataFrame(matchup_pdf)
    matchup_df.write.saveAsTable("pm_fantasyfb.matchup_flow",mode="append")
    return matchup_df
    

# COMMAND ----------

def handler(input,context):
    if not _is_nfl_game_active(debug=dbutils.widgets.get("debug")):
        return False

    df = save_matchup_data(input)
    return True
    

# COMMAND ----------

handler({'leagueId':dbutils.widgets.get("leagueId")},None)

