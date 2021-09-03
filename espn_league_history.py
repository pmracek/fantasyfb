# Databricks notebook source
# 
# # To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import time, re, csv
from bs4 import BeautifulSoup
from datetime import datetime
import requests
from collections import defaultdict
import math
from espn import (getsession,
                      class_not_spacer,
                      get_week_formatted,
                      outcome,
                      save_file,
                      nfl_start_dt,
                      week_of_season,
                      teams, )

seasons = range(2018,datetime.now().year+1)

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

# %% [markdown]
# ## Create a Selenium webdriver for Chrome & Login 
# ##### Originally used Requests but ESPN site redesign broke login form.

# %%
s = getsession()

# %% [markdown]
# ##  Create and Parse Soups for Weekly Team Results

# %%
quickboxurls = defaultdict(list)

for season in seasons:
        
        print('')
        print(season)
        
        ### Build matchup_recaps
        results = [('SEASON','SCORINGPERIOD', 'WEEK_NM','TEAM','TEAMNAME','SCORE','OPPONENT','OPPONENTNAME','OPPONENTSCORE', 'OUTCOME')]
        url = 'http://games.espn.go.com/ffl/schedule?leagueId=111414&seasonId='+str(season)
        r = s.post(url)
        cur_season = BeautifulSoup(r.text, "lxml")
        
        first_row = True
        while True:
                if first_row:
                        current_row = cur_season.find(class_not_leagueSettingsTable).tr
                        first_row = False
                else:
                        current_row = current_row.next_sibling
                
                if current_row is None: # Past last row; exit
                        break
                if current_row == '\n': # Line feed, do not process
                        continue

                try:    # this try block must come before the raw_score or else week never gets set.
                        class_ = current_row['class']
                except KeyError:
                        class_ = ""
                
                if 'tableSubHead' in class_:    # Header row, do not process
                        continue
                if 'tableHead' in class_:       # Weekly header.  Grab week # and move on
                        week = get_week_formatted(current_row.td.text)
                        print(week, end=" ")
                        continue

                try:
                        raw_score = current_row.contents[11].text.rstrip('*')
                        
                        if raw_score == 'Preview' or raw_score == 'Box':      # Game has not been played yet
                                continue        
                except IndexError:      # Spacer row
                        continue
                        
                                
                quickboxurls[season].append('http://games.espn.com'+current_row.contents[11].a['href'])  
                scoringperiod = scoringperiodidpattern.search(current_row.contents[11].a['href']).group('id')
                        
                team1 = teamidpattern.search(current_row.contents[1].a.get('href')).group('id')         
                team1score = float(raw_score.split('-')[0])
                
                team2 = teamidpattern.search(current_row.contents[7].a.get('href')).group('id')
                team2score = float(raw_score.split('-')[1])     
                
                results.append((season, scoringperiod, week, team1, teams[int(season)][team1], team1score, team2, teams[int(season)][team2], team2score, outcome(team1score, team2score)))
                results.append((season, scoringperiod, week, team2, teams[int(season)][team2], team2score, team1, teams[int(season)][team1], team1score, outcome(team2score, team1score)))

        save_file(season,'00','matchup_recap',results)


# %%
for season in seasons:
    print('')
    print(season)
    
    boxresults = [('SEASON','SCORINGPERIOD', 'WEEK_NM','TEAM','TEAMNAME','SLOT','PLAYERID','PLAYERNAME','PLAYEROPP','GAMEOUTCOME', 'PLAYERPOINTS', 'STARTERPOINTS', 'BENCHPOINTS')]
    for quickboxurl in quickboxurls[season]:        
        r = s.post(quickboxurl)
        cur_matchup = BeautifulSoup(r.text, "lxml")

        scoringperiod = scoringperiodidpattern.search(quickboxurl).group('id')
        week = get_week_formatted(cur_matchup.select('.games-pageheader')[0].em.text)

        allscores = cur_matchup.select('.playertableTableHeader') # Grab the table header with team name because the class=playerTable is used for both bench and starters.  Aka get double results. 
        for box in allscores:    
            cur_team_box = box.parent.parent
            left_or_right_box = 0 if re.search('left',cur_team_box['style'],re.IGNORECASE) else 1

            cur_team_id = teamidpattern.search(cur_matchup.find(id='teamInfos').find_all('a')[left_or_right_box].get('href')).group('id')

            if int(season) > 2015:
                starterpts = cur_team_box.select('.totalScore')[0].text
            else:
                starterpts = cur_team_box.select('.playerTableBgRowTotals')[0].select('.appliedPoints')[0].text
            try: 
                benchpts = cur_matchup.find(id='tmInactivePts_'+str(cur_team_id)).text 
            except:
                benchpts = '0'

            players = cur_team_box.select('.pncPlayerRow')
            for player in players:  # will be iterable
                slot = player.select('.playerSlot')[0].text if int(season) > 2015 else player.select('.playertablePlayerName')[0].text.split()[-1]
                if slot.upper() == 'IR' or player.select('td')[1].text.strip()=='':
                    break
                playerid = player.find('a')['playerid'] if int(season) > 2015 else 'null'
                playername = player.find('a').text if int(season) > 2015 and player.select('td')[1].text.strip()!='' else player.select('.playertablePlayerName')[0].text
                if re.search('BYE', player.select('.playertablePlayerName')[0].next_sibling.text, re.IGNORECASE):
                    playeropp = 'BYE'
                    gameoutcome = 'BYE'
                else:
                    playeropp = player.select('.playertablePlayerName')[0].next_sibling.text if int(season) > 2015 else player.find_all('a')[0].text
                    gameoutcome = player.select('.gameStatusDiv')[0].text[2:] if int(season) > 2015 else player.find_all('a')[1].text
                playerpoints = player.select('.playertableStat')[0].text

                boxresults.append((season, scoringperiod, week, cur_team_id, teams[int(season)][cur_team_id],slot, playerid, playername, playeropp, gameoutcome, playerpoints, starterpts, benchpts))

    save_file(season,'00','quickbox',boxresults)


# %%
for season in seasons: 
    print('')
    print(season)
    if season < 2016:
        break
        
    url = 'http://games.espn.go.com/ffl/waiverreport?leagueId=111414&seasonId='+str(season)
    r = s.post(url)
    auction_landing_page = BeautifulSoup(r.text, "lxml")

    scoringPeriodId = 0
    bids = [('SEASON','SCORINGPERIOD','WEEK_NM','AUCTIONDATE','TEAM','TEAMNAME','PLAYERID','PLAYERNAME','BID','BIDRESULT')]
    
    for option in auction_landing_page.find_all('option'):
        auction_date = option.get('value')
        
        if scoringPeriodId != week_of_season(auction_date) and len(bids) > 1:
            print(scoringPeriodId)
            save_file(season,'{0:02d}'.format(scoringPeriodId),'faab_report',bids)                
            bids = [('SEASON','SCORINGPERIOD','WEEK_NM','AUCTIONDATE','TEAM','TEAMNAME','PLAYERID','PLAYERNAME','BID','BIDRESULT')]
        
        scoringPeriodId = week_of_season(auction_date)         
        url = 'http://games.espn.go.com/ffl/waiverreport?leagueId=111414&seasonId='+str(season)+'&date='+auction_date
        r = s.post(url)
        cur_auction = BeautifulSoup(r.text, "lxml")   
        
        bidTbl = cur_auction.find_all('tr', attrs={'class':'tableBody'})
        for bid in bidTbl:
            owner = bid.contents[2].a
            teamId = teamidpattern.search(owner.get('href')).group('id')
            player = bid.contents[4].a
            bidAmt = bid.contents[6].string.lstrip('$')
            bidResult = bidresultpattern.search(bid.contents[7].text).group()
            
            bids.append((season,week_of_season(auction_date),week_of_season(auction_date), auction_date , teamId , teams[int(season)][teamId], player.get('playerid') , player.string , bidAmt , bidResult))

    #last week each season will not be saved yet
    save_file(season,'{0:02d}'.format(scoringPeriodId),'faab_report',bids)
    print(scoringPeriodId)    


# %%



# %%



