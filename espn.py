from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from datetime import datetime
import configparser
import requests
import re
import csv

config = configparser.ConfigParser()
config.read_file(open('fantasyfb.ini'))

#Use Selenium ChromeDriver to login to ESPN angular-js form buried in an iframe.  
#Then move logged in cookies to a requests session and return both handles.
def getdriver(leagueId=None,season=None):
    
    if leagueId is None:
        leagueId = config.get('main', 'leagueId') if config.has_option('main', 'leagueId') else '111414'
        
    if season is None:
        season = config.get('main', 'season') if config.has_option('main', 'season') else datetime.now().year - 1          
    
    #driver = webdriver.Chrome(config['main']['chromedriverexe'])
    driver = webdriver.Safari()

    driver.get("http://games.espn.go.com/ffl/signin")
    #implement wait it is mandatory in this case
    WebDriverWait(driver,1000).until(EC.presence_of_all_elements_located((By.XPATH,"(//iframe)")))
    frms = driver.find_elements_by_tag_name("iframe")

    
    for i in range(len(frms)):
        driver.switch_to.default_content()
        #time.sleep(1)
        
        try:
            driver.switch_to.frame(frms[i])            
            driver.find_element_by_xpath('(//input[@type="email"])').send_keys(config['main']['username'])
            driver.find_element_by_xpath('(//input[@type="password"])').send_keys(config['main']['password'])            
            driver.find_element_by_class_name("btn-submit").click()            
            break
        except:
            pass
        
    s = requests.Session()
    cookies = driver.get_cookies()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])

    return driver, s



def getsession(leagueId=None,season=None):
	if leagueId is None:
		leagueId = config.get('main', 'leagueId') if config.has_option('main', 'leagueId') else '111414'        
	if season is None:
		season = config.get('main', 'season') if config.has_option('main', 'season') else datetime.now().year - 1          
	d,s = getdriver(leagueId,season)
	d.quit()
	return s
	
	
def class_not_spacer(tag):
	return not tag.has_attr('class') or (tag.has_attr('class') and not re.match("sectionLeadingSpacer", ' '.join(tag['class'])))  # have to use the ' '.join() syntax because tag['class'] is actually a list

def get_week_formatted(wk):
    weekpattern = re.compile('(?P<wktype>(WEEK|ROUND))\s(?P<wknum>\d+)', flags=re.IGNORECASE)
    wktype = weekpattern.search(wk).group('wktype')
    wknum = weekpattern.search(wk).group('wknum')
    return wknum if wktype.upper() == "WEEK" else "P"+wknum

def outcome(score1, score2):
        if score1 > score2:
                outcome = 'W'
        elif score1 < score2:
                outcome = 'L'
        else:
                outcome = 'T'
        return outcome
    
def save_file(season,wk,file,data):
    import csv
    with open('data/'+str(season)+'_'+str(wk)+'_'+str(file)+'.txt', 'w', newline = '\n') as f:
            writer = csv.writer(f)
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
       }

def week_of_season(d):
    import math
    s = datetime.strptime(d,'%Y%m%d').year
    dt = datetime.strptime(d,'%Y%m%d').date()

    return math.ceil((dt - nfl_start_dt[s]).days/7)

#todo figure out how to load teams / years dynamically
pre2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell'}
t2010 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Doogs'}
t2011 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'JonBurriss'}
t2012 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Blackwell', '11':'Tony', '12':'Paul'}
t2016 = {'1':'Scott', '2':'Brent', '3':'JMT', '4':'JJ', '5':'Tim', '6':'Jeremy', '7':'Kyle', '8':'Thomas', '9':'Schwartz', '10':'Goss', '11':'Tony', '12':'Paul'}

teams = {2008:pre2010, 2009:pre2010, 2010:t2010, 2011:t2011, 2012:t2012, 2013:t2012, 2014:t2012, 2015:t2012, 2016:t2016, 2017:t2016, 2018:t2016}
