
# coding: utf-8

# In[1]:


import time, re, csv, espn, espnff, configparser
from bs4 import BeautifulSoup
from datetime import datetime, date, timezone,timedelta
import requests
from collections import defaultdict
import math
import os.path

config = configparser.ConfigParser()
config.read_file(open('fantasyfb.ini'))

leagueId = config.get('main', 'leagueId') if config.has_option('main', 'leagueId') else '111414'

season = 2018

def get_week_formatted(wk):
    weekpattern = re.compile('(?P<wktype>(WEEK|ROUND))\s(?P<wknum>\d+)', flags=re.IGNORECASE)
    wktype = weekpattern.search(wk).group('wktype')
    wknum = weekpattern.search(wk).group('wknum')
    return wknum if wktype.upper() == "WEEK" else "P"+wknum

teamidpattern = re.compile('teamId=(?P<id>\d+)')
weekpattern = re.compile('(?P<wktype>(WEEK|ROUND))\s(?P<wknum>\d+)')
seasonidpattern = re.compile('seasonId=(?P<season>\d+)')
scoringperiodidpattern = re.compile('scoringPeriodId=(?P<id>\d+)')
bidresultpattern = re.compile('\w+(?=\.)')

pre2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell'}
t2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Doogs'}
t2011 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'JonBurriss'}
t2012 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Paul'}
t2016 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Goss', '11':'Tony', '12':'Paul'}

teams = {2008:pre2010, 2009:pre2010, 2010:t2010, 2011:t2011, 2012:t2012, 2013:t2012, 2014:t2012, 2015:t2012, 2016:t2016, 2017:t2016, 2018:t2016}


def save_file(season,wk,file,mode,data):
    filepath = 'data/'+str(season)+'_'+str(wk)+'_'+str(file)+'.txt'
    file_exists = os.path.isfile(filepath)
    header = [('SEASON','SCORINGPERIOD', 'WEEK_NM','COLLECTDATE','DAYOFWEEK','GAMESLOT','COLLECTTIMESTAMP', 'TEAM1','TEAM1NAME','TEAM1PTS','TEAM1PROJ','TEAM1YETTOPLAY','TEAM1INPLAY','TEAM1MINREMAINING','TEAM1TOPSCORER','TEAM2','TEAM2NAME','TEAM2PTS','TEAM2PROJ','TEAM2YETTOPLAY','TEAM2INPLAY','TEAM2MINREMAINING','TEAM2TOPSCORER')]

    with open(filepath, mode, encoding='utf-8', newline = '\n') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerows(header)  # file doesn't exist yet, write a header
        writer.writerows(data)


# #Only run if there is an active NFL game

# In[2]:


r = requests.get('http://www.nfl.com/liveupdate/scorestrip/ss.xml')
schedxml = BeautifulSoup(r.text, "lxml")
active = False
for info in schedxml.findAll('g'):
    hour, minute = info['t'].strip().split(':')
    d = datetime(int(info['eid'][:4]), int(info['eid'][4:6]), int(info['eid'][6:8]),
                          (int(hour) + 12) % 24, int(minute))
    d.astimezone(tz=None)
    gamestatus = info['q']
    if(gamestatus != 'F' and ((datetime.now() - d) > timedelta(seconds=0))):
        active = True

if not active:
    tmp=1 #raise SystemExit()


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

# In[3]:


url = 'http://games.espn.go.com/ffl/scoreboard'
r = requests.get(url,
                params={'leagueId': leagueId, 'seasonId': season})
scoreboard_html = BeautifulSoup(r.text, "lxml")
week = get_week_formatted(scoreboard_html.find("div", {"class": "games-pageheader"}).em.text)

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
