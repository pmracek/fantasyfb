
# coding: utf-8

# In[1]:


import requests, re
from bs4 import BeautifulSoup
from datetime import datetime, date, timezone,timedelta
import boto3
from pytz import timezone

dynamodb = boto3.resource('dynamodb')

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

def get_week_formatted(wk):
    weekpattern = re.compile('(?P<wktype>(WEEK|ROUND))\s(?P<wknum>\d+)', flags=re.IGNORECASE)
    wktype = weekpattern.search(wk).group('wktype')
    wknum = weekpattern.search(wk).group('wknum')
    return wknum if wktype.upper() == "WEEK" else "P"+wknum

pre2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell'}
t2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Doogs'}
t2011 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'JonBurriss'}
t2012 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Paul'}
t2016 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Goss', '11':'Tony', '12':'Paul'}

teams = {2008:pre2010, 2009:pre2010, 2010:t2010, 2011:t2011, 2012:t2012, 2013:t2012, 2014:t2012, 2015:t2012, 2016:t2016, 2017:t2016, 2018:t2016}


# #Only run if there is an active NFL game

# In[2]:


def _is_nfl_game_active():
    r = requests.get('http://www.nfl.com/liveupdate/scorestrip/ss.xml')
    schedxml = BeautifulSoup(r.text, "html.parser")
    active = False
    for info in schedxml.findAll('g'):
        #hour, minute = info['t'].strip().split(':')
        #d = datetime(int(info['eid'][:4]), int(info['eid'][4:6]), int(info['eid'][6:8]),
        #                      (int(hour) + 12) % 24, int(minute))
        #d.astimezone(tz=None)
        gamestatus = info['q']
        if(gamestatus != 'F'  and gamestatus != 'FO' and gamestatus != 'P'):
            active = True  
            break
        
    return active 


# In[32]:


#IMPORTANT: can only look at current or future weeks.  
#should add query param for matchupPeriodId and change class scraping logic if weeks has a declared winner 
#(even on default scoreboard like on Tuesdays).  Matchup box has different class names in that case.  
#Not a high priority since I use NFL feed to verify that at least one game is in progress before getting into this method.
    
def save_matchup_data(input):
    table = dynamodb.Table('MatchupGameFlow')
    
    url = 'http://games.espn.go.com/ffl/scoreboard'
    r = requests.get(url,
                    params={'leagueId': input['leagueId'], 'seasonId': season})
    
    scoreboard_html = BeautifulSoup(r.text, "html.parser")
    week = get_week_formatted(scoreboard_html.find("div", {"class": "games-pageheader"}).em.text)
    teamidpattern_scoreboard = re.compile('tmTotalPts_(?P<id>\d+)')
    
    matchups = scoreboard_html.select(".matchup")
    for matchup in matchups:
        teamids = [] 
        for ids in matchup.find_all(id=re.compile("^tmTotalPts")):
            teamids.append(teamidpattern_scoreboard.search(ids["id"]).group('id'))       
        
        result = {
            'SEASON':season
            ,'SCORINGPERIOD':week
            ,'WEEK_NM':week
            ,'COLLECTDATE':datetime.now().astimezone(timezone('US/Eastern')).strftime('%Y-%m-%d')
            ,'DAYOFWEEK':datetime.now().astimezone(timezone('US/Eastern')).strftime('%a')
            ,'GAMESLOT':game_slot(datetime.now().astimezone(timezone('US/Eastern')))
            ,'COLLECTTIMESTAMP':datetime.now().astimezone(timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")
            ,'TEAM1':teamids[0]
            ,'TEAM1NAME':teams[int(season)][teamids[0]]
            ,'TEAM1PTS':matchup.find(id='tmTotalPts_'+str(teamids[0])).text
            ,'TEAM1PROJ':matchup.find(id='team_liveproj_'+str(teamids[0])).text
            ,'TEAM1YETTOPLAY':matchup.find(id='team_ytp_'+str(teamids[0])).text
            ,'TEAM1INPLAY':matchup.find(id='team_ip_'+str(teamids[0])).text
            ,'TEAM1MINREMAINING':matchup.find(id='team_pmr_'+str(teamids[0])).text
            ,'TEAM1TOPSCORER':matchup.find(id='team_topscorer_'+str(teamids[0])).text
            #team_line_0 = matchup.find(id='team_line_'+str(teamids[0])).text
            ,'TEAM2':matchup.find(id='tmTotalPts_'+str(teamids[1])).text
            ,'TEAM2NAME':teams[int(season)][teamids[1]]
            ,'TEAM2PTS':matchup.find(id='tmTotalPts_'+str(teamids[1])).text
            ,'TEAM2PROJ':matchup.find(id='team_liveproj_'+str(teamids[1])).text
            ,'TEAM2YETTOPLAY':matchup.find(id='team_ytp_'+str(teamids[1])).text
            ,'TEAM2INPLAY':matchup.find(id='team_ip_'+str(teamids[1])).text
            ,'TEAM2MINREMAINING':matchup.find(id='team_pmr_'+str(teamids[1])).text
            ,'TEAM2TOPSCORER':matchup.find(id='team_topscorer_'+str(teamids[1])).text
            ,'LEAGUEID':input['leagueId']
            #team_line_1 = matchup.find(id='team_line_'+str(teamids[1])).text
        }
        
        table.put_item(Item=result)


# In[30]:


def handler(input,context):
    if not _is_nfl_game_active():
        return False

    save_matchup_data(input)
    return True
    


# In[34]:


#handler({'leagueId':'111414'},None)

