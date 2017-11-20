from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from datetime import datetime
import requests

def getdriver_v1():
	driver = webdriver.Chrome(r'C:\Users\PM186016\Dropbox\Python\selenium\webdriver\chrome2.33\chromedriver')
	
	driver.get("http://games.espn.com/ffl/leagueoffice?leagueId=111414&seasonId=2016")
	
	input("Press Enter to continue...")

	return driver
	

def getdriver(leagueId=None,season=None):
    if leagueId is None:
        leagueId = '111414'	#todo config
    if season is None:
        season = datetime.now().year - 1		#todo config/current year
    
    
    driver = webdriver.Chrome(r'C:\Users\PM186016\Dropbox\Python\selenium\webdriver\chrome2.33\chromedriver') #todo config rel path

    leagueUrl = "http://games.espn.com/ffl/leagueoffice?leagueId="+str(leagueId)+"&seasonId="+str(season)
    
    driver.get(leagueUrl)

    input("Press Enter to continue...")

    s = requests.Session()
    cookies = driver.get_cookies()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])

    return driver, s
	
	
def class_not_spacer(tag):
	return not tag.has_attr('class') or (tag.has_attr('class') and not re.match("sectionLeadingSpacer", ' '.join(tag['class'])))  # have to use the ' '.join() syntax because tag['class'] is actually a list

