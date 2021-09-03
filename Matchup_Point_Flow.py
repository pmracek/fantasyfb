# Databricks notebook source
# coding: utf-8

# In[1]:


import time, re, csv, espn
from bs4 import BeautifulSoup
from datetime import datetime, date
import requests
from collections import defaultdict
import math
import os.path


seasons = range(2017,datetime.now().year+1)

def outcome(score1, score2):
        if score1 > score2:
                outcome = 'W'
        elif score1 < score2:
                outcome = 'L'
        else:
                outcome = 'T'
        return outcome

teamidpattern = re.compile('teamId=(?P<id>\d+)')
weekpattern = re.compile('(?P<wktype>(WEEK|ROUND))\s(?P<wknum>\d+)')
seasonidpattern = re.compile('seasonId=(?P<season>\d+)')
scoringperiodidpattern = re.compile('scoringPeriodId=(?P<id>\d+)')
bidresultpattern = re.compile('\w+(?=\.)')

def class_not_leagueSettingsTable(tag):
        return tag.has_attr('class') and not re.match("leagueSettingsTable", ' '.join(tag['class'])) and re.match("tableBody", ' '.join(tag['class']))  # have to use the ' '.join() syntax because tag['class'] is actually a list

def class_playertablebody(tag):
    return tag.has_attr('class') and re.match("playerTableTable", ' '.join(tag['class']))  # have to use the ' '.join() syntax because tag['class'] is actually a list

def class_playerrow(tag):
    return tag.has_attr('class') and re.match("pncPlayerRow", ' '.join(tag['class']))  # have to use the ' '.join() syntax because tag['class'] is actually a list

def get_week_formatted(wk):
    weekpattern = re.compile('(?P<wktype>(WEEK|ROUND))\s(?P<wknum>\d+)', flags=re.IGNORECASE)
    wktype = weekpattern.search(wk).group('wktype')
    wknum = weekpattern.search(wk).group('wknum')
    return wknum if wktype.upper() == "WEEK" else "P"+wknum

def save_file(season,wk,file,mode,data):
    filepath = 'data/'+str(season)+'_'+str(wk)+'_'+str(file)+'.txt'
    file_exists = os.path.isfile(filepath)

    with open(filepath, mode, newline = '\n') as f:
        writer = csv.writer(f)
        #if not file_exists:
        #    writer.writeheader()  # file doesn't exist yet, write a header
        writer.writerows(data)

nfl_start_dt = {
        2008:datetime.strptime('20080901','%Y%m%d').date() 
        , 2009:datetime.strptime('20090907','%Y%m%d').date() 
        , 2010:datetime.strptime('20100906','%Y%m%d').date() 
        , 2011:datetime.strptime('20110905','%Y%m%d').date() 
        , 2012:datetime.strptime('20120903','%Y%m%d').date() 
        , 2013:datetime.strptime('20130902','%Y%m%d').date() 
        , 2014:datetime.strptime('20140901','%Y%m%d').date() 
        , 2015:datetime.strptime('20150907','%Y%m%d').date() 
        , 2016:datetime.strptime('20160905','%Y%m%d').date() 
        , 2017:datetime.strptime('20170904','%Y%m%d').date()
        , 2018:datetime.strptime('20180903','%Y%m%d').date()
       }

def week_of_season(d):    
    s = datetime.strptime(d,'%Y%m%d').year
    dt = datetime.strptime(d,'%Y%m%d').date()

    return math.ceil((dt - nfl_start_dt[s]).days/7)

# COMMAND ----------

# In[2]:


#todo figure out how to load teams / years dynamically
pre2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell'}
t2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Doogs'}
t2011 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'JonBurriss'}
t2012 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Paul'}
t2016 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Goss', '11':'Tony', '12':'Paul'}

teams = {2008:pre2010, 2009:pre2010, 2010:t2010, 2011:t2011, 2012:t2012, 2013:t2012, 2014:t2012, 2015:t2012, 2016:t2016, 2017:t2016, 2018:t2016}


# ## Create a Selenium webdriver for Chrome & Login 
# ##### Originally used Requests but ESPN site redesign broke login form.
# COMMAND ----------
# In[3]:


s = espn.getsession()


# # ESPN Week
# NFL Week
# --http://api.fantasy.nfl.com/v2/docs/service?serviceName=nflSchedule
# --https://www.hooksdata.io/signup?invite=SM4555
# 
# Season
# Week
# DayOfWeek
# Game Time Slot
# Timestamp
# MatchupID (Team1-Team2-Wk#?)
# Team1ID
# Team1Name
# Team1Points
# Team1Projected
# Team2ID
# Team2Name
# Team2Points
# Team2Projected

# COMMAND ----------
# In[5]:


season = 2018
week = 1
url = 'http://games.espn.go.com/ffl/scoreboard?leagueId=111414&seasonId='+str(season)
r = s.post(url)
scoreboard_html = BeautifulSoup(r.text, "lxml")


# COMMAND ----------
# In[6]:


matchups = scoreboard_html.select(".matchup")

teamidpattern_scoreboard = re.compile('tmTotalPts_(?P<id>\d+)')

header = [('SEASON','SCORINGPERIOD', 'WEEK_NM','COLLECTDATE','DAYOFWEEK','GAMESLOT','COLLECTTIMESTAMP', 'TEAM1','TEAM1NAME','TEAM1PTS','TEAM1PROJ','TEAM1YETTOPLAY','TEAM1INPLAY','TEAM1MINREMAINING','TEAM1TOPSCORER','TEAM2','TEAM2NAME','TEAM2PTS','TEAM2PROJ','TEAM2YETTOPLAY','TEAM2INPLAY','TEAM2MINREMAINING','TEAM2TOPSCORER')]

results = []
matchids = []

for matchup in matchups:
    teamids = [] 
    for ids in matchup.find_all(id=re.compile("^tmTotalPts")):
        teamids.append(teamidpattern_scoreboard.search(ids["id"]).group('id'))
    matchids.append(str(teamids[0])+'vs'+str(teamids[1])+'-W'+str(week))
    
    team_tmTotalPts_0 = matchup.find(id='tmTotalPts_'+str(teamids[0])).text
    team_ytp_0 = matchup.find(id='team_ytp_'+str(teamids[0])).text
    team_ip_0 = matchup.find(id='team_ip_'+str(teamids[0])).text
    team_pmr_0 = matchup.find(id='team_pmr_'+str(teamids[0])).text
    team_liveproj_0 = matchup.find(id='team_liveproj_'+str(teamids[0])).text
    #team_line_0 = matchup.find(id='team_line_'+str(teamids[0])).text
    team_topscorer_0 = matchup.find(id='team_topscorer_'+str(teamids[0])).text

    team_tmTotalPts_1 = matchup.find(id='tmTotalPts_'+str(teamids[1])).text
    team_ytp_1 = matchup.find(id='team_ytp_'+str(teamids[1])).text
    team_ip_1 = matchup.find(id='team_ip_'+str(teamids[1])).text
    team_pmr_1 = matchup.find(id='team_pmr_'+str(teamids[1])).text
    team_liveproj_1 = matchup.find(id='team_liveproj_'+str(teamids[1])).text
    #team_line_1 = matchup.find(id='team_line_'+str(teamids[1])).text
    team_topscorer_1 = matchup.find(id='team_topscorer_'+str(teamids[1])).text
    
    results.append((season,week,week,date.today(),date.today().strftime('%a'),'GameTime',datetime.now().strftime("%Y-%m-%d %H:%M:%S"),teamids[0],teams[int(season)][teamids[0]],team_tmTotalPts_0,team_liveproj_0,team_ytp_0,team_ip_0,team_pmr_0,team_topscorer_0,teamids[1],teams[int(season)][teamids[1]],team_tmTotalPts_1,team_liveproj_1,team_ytp_1,team_ip_1,team_pmr_1,team_topscorer_1))


save_file(season,week,'matchup_flow','a',results)

# COMMAND ----------