
# coding: utf-8

# In[115]:

import time, re, csv, espn
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime

teamidpattern = re.compile('teamId=(?P<id>\d+)')
weekpattern = re.compile('(?P<wktype>(WEEK|ROUND))\s(?P<wknum>\d+)')

def outcome(score1, score2):
        if score1 > score2:
                outcome = 'W'
        elif score1 < score2:
                outcome = 'L'
        else:
                outcome = 'T'
        return outcome

def class_not_leagueSettingsTable(tag):
        return tag.has_attr('class') and not re.match("leagueSettingsTable", ' '.join(tag['class'])) and re.match("tableBody", ' '.join(tag['class']))  # have to use the ' '.join() syntax because tag['class'] is actually a list


# In[116]:

teams = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Paul'}


# ## Create a Selenium webdriver for Chrome & Login 
# ##### Originally used Requests but ESPN site redesign broke login form.

# In[117]:

driver = webdriver.Chrome(r'C:\Users\PM186016\Dropbox\Python\selenium\webdriver\chrome\chromedriver')

driver.get("http://games.espn.go.com/ffl/signin")
#implement wait it is mandatory in this case
WebDriverWait(driver,1000).until(EC.presence_of_all_elements_located((By.XPATH,"(//iframe)")))
frms = driver.find_elements_by_tag_name("iframe")

for i in range(len(frms)):
    driver.switch_to_default_content()
    #time.sleep(1)
    try:
        driver.switch_to_frame(frms[i])
        #time.sleep(1)
        driver.find_element_by_xpath('(//input[@type="email"])').send_keys("email")
        driver.find_element_by_xpath('(//input[@type="password"])').send_keys("password")
        driver.find_element_by_xpath("//button").click()
        break
    except:
        pass



# ##  Create and Parse Soups for Weekly Team Results

# In[118]:

results = [('SEASON','WEEK','TEAM','TEAMNAME','SCORE','OPPONENT','OPPONENTNAME','OPPONENTSCORE', 'OUTCOME')]

for season in range(2015,datetime.now().year+1):
        print('')
        print(season)
        url = 'http://games.espn.go.com/ffl/schedule?leagueId=111414&seasonId='+str(season)
        driver.get(url) 
        cur_season = BeautifulSoup(driver.page_source)

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
                        wktype = weekpattern.search(current_row.td.text).group('wktype')
                        wknum = weekpattern.search(current_row.td.text).group('wknum')
                        week = wknum if wktype == "WEEK" else "P"+wknum
                        print(week, end=" ")
                        continue

                try:
                        raw_score = current_row.contents[11].text.rstrip('*')
                        
                        if raw_score == 'Preview':      # Game has not been played yet
                                continue        
                except IndexError:      # Spacer row
                        continue
                        
                
                #print(current_row)
                        
                team1 = teamidpattern.search(current_row.contents[1].a.get('href')).group('id')         
                team1score = float(raw_score.split('-')[0])
                
                team2 = teamidpattern.search(current_row.contents[7].a.get('href')).group('id')
                team2score = float(raw_score.split('-')[1])     
                
                results.append((season, week, team1, teams[team1], team1score, team2, teams[team2], team2score, outcome(team1score, team2score)))
                results.append((season, week, team2, teams[team2], team2score, team1, teams[team1], team1score, outcome(team2score, team1score)))


# In[119]:

with open('data/matchup_results_2015f_thru_2016w2.txt', 'w', newline = '\n') as f:
        writer = csv.writer(f)
        writer.writerows(results)


# In[ ]:

import pandas as pd
import numpy as np


# In[ ]:

df = pd.DataFrame.from_records(results[1:], columns = results[0])
print(df)


# In[ ]:

h2h = df.groupby(['TEAMNAME','OPPONENTNAME', 'OUTCOME'])['OUTCOME'].count().unstack().fillna(0)


# In[ ]:

h2h.L


# In[ ]:

h2h.columns


# In[ ]:

type(h2h['W'])

