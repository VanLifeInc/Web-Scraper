import selenium as selenium
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotVisibleException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException

import time

class WebInterface:

    def __init__(self):

        self.category_index=0

    def get_driver(self):

        options=webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_experimental_option("useAutomationExtension",False)
        options.add_experimental_option("prefs", {"profile.default_content_settings.cookies": 2})
        options.add_argument("--test-type")
        options.binary_location="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"

        self.driver=webdriver.Chrome(chrome_options=options)

    def go_to(self,link):

        self.driver.get(link)

    def enter_text(self,x_path,value,submit=False):

        input_element=self.driver.find_element_by_xpath(x_path)
        input_element.send_keys(value)
        if submit==True:
            input_element.submit()

    def xpath_click(self,x_path):

        input_element=self.driver.find_element_by_xpath(x_path)
        input_element.click()

    def text_click(self,text):
        
        input_element=self.driver.find_element_by_link_text(text)
        input_element.click()

    def load_insist(self,x_path,value):

        refresh=False
        refreshed=False
        elementMatch=False
        start_time=time.time()
        buffer=20
        while(elementMatch==False):
            refresh=self.should_browser_refresh(start_time,20,refreshed)
            if refresh==True and refreshed==False:
                start_time=time.time()
                print("\tCould not load the element. Refreshing the browser and trying again...")
                self.driver.refresh()
                refresh=False
                refreshed=True
            try:
                target_element=self.driver.find_element_by_xpath(x_path)
                if target_element.text==value:
                    elementMatch=True
            except NoSuchElementException:
                pass
            time.sleep(0.1)

    def should_browser_refresh(self,start,limit,refreshed):
        #print('\t','\t',str(time.time()-start))
        if time.time()-start>limit:
            if refreshed==True:
                raise TimeoutException("Timeout Occured")
            return True
        else:
            return False

    def next_category(self):

        self.category_index=self.category_index+1
        cat_xpath='//*[@id="mainPageContent"]/div[2]/div[1]/div[1]/div/ul[1]/ul/ul/li['+str(self.category_index)+']/a'

        self.go_to(self.cat_url)
        self.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span[4]/h1','Buy & Sell in City of Toronto')
        cat_content=self.driver.find_element_by_xpath(cat_xpath).get_attribute('textContent').strip()

        if cat_content=='Fewer Options':
            raise IndexError("Finished iterating through all categories")
        
        print("Current Category: ",cat_content)

        while(True):
            try:
                print("\tEnter the category...")
                self.xpath_click(cat_xpath)
                print("\tLoad the category...")
                self.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span[5]/h1',cat_content+' in City of Toronto')
                print("\tDone.")
                break
            except ElementNotVisibleException:
                print("\tTrying to click view more options...")
                self.text_click('View more options...')
            except TimeoutException:
                print("\tBrowser refresh failed. Trying to locate element from the beginning...")
                self.go_to(self.cat_url)
                self.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span[4]/h1','Buy & Sell in City of Toronto')
            except WebDriverException:
                print("\tUnknown web driver exception. Trying to locate element from the beginning...")
                self.go_to(self.cat_url)
                self.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span[4]/h1','Buy & Sell in City of Toronto')


if __name__ == "__main__":

    #Instantiate Web Interface
    WI=WebInterface()

    print("Instantiating the web driver...")

    #Instantiate the web driver
    WI.get_driver()

    #Maximize chrome window
    WI.driver.maximize_window()

    print("Navigating to the first category...")

    #Navigate to Kijiji
    WI.go_to('https://www.kijiji.ca/')

    #Go to Toronto in Kijiji
    WI.xpath_click('//*[@id="SearchLocationPicker"]')
    WI.text_click('Ontario (M - Z)')
    WI.text_click('Toronto (GTA)')
    WI.text_click('City of Toronto')
    
    #Wait untill City of Toronto is loaded
    WI.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span[3]/h1','City of Toronto')

    #Go to buy/sell
    WI.xpath_click('//*[@id="SearchCategory"]')
    WI.text_click('Buy & Sell')

    #Wait untill Buy & Sell in City of Toronto is loaded
    WI.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span[4]/h1','Buy & Sell in City of Toronto')

    #Iterate through all buy & sell categories
    WI.cat_url=WI.driver.current_url

    while(True):
        try:
            WI.next_category()
        except IndexError:
            print("Done iterating all categories. The webdriver will now shut down.")
            break

    #Close/kill the driver
    WI.driver.quit()
