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

config = configparser.ConfigParser()
config.read_file(open('fantasyfb.ini'))

#Use Selenium ChromeDriver to login to ESPN angular-js form buried in an iframe.  
#Then move logged in cookies to a requests session and return both handles.
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


