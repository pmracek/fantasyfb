from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

def getdriver():
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
			driver.find_element_by_xpath('(//input[@type="email"])').send_keys("pmracek@gmail.com")
			driver.find_element_by_xpath('(//input[@type="password"])').send_keys("aissaj")
			driver.find_element_by_xpath("//button").click()
			break
		except:
			pass
	return driver

def class_not_spacer(tag):
	return not tag.has_attr('class') or (tag.has_attr('class') and not re.match("sectionLeadingSpacer", ' '.join(tag['class'])))  # have to use the ' '.join() syntax because tag['class'] is actually a list

