import selenium as selenium
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotVisibleException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException

import numpy as np

import configparser
import time

class WebInterface:

    def __init__(self):

        self.category_index=0
        self.load_config()

    def load_config(self):
        
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.whitelist=config.get('WebInterface', 'Whitelist').split('//')
        self.load_insist_limit=int(config.get('WebInterface', 'Load Insist Limit'))
        
    def get_driver(self):

        options=webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_experimental_option("useAutomationExtension",False)
        options.add_experimental_option("prefs", {"profile.default_content_settings.cookies": 2})
        options.add_argument("--test-type")
        options.binary_location="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"

        self.driver=webdriver.Chrome(chrome_options=options)

    def go_to(self,link):

        if link!=self.driver.current_url:
            self.driver.get(link)

    def enter_text(self,x_path,value,submit=False):

        input_element=self.driver.find_element_by_xpath(x_path)
        input_element.send_keys(value)
        if submit==True:
            input_element.submit()

    def xpath_click(self,x_path):

        #print("\tClicking on: " + str(x_path))
        input_element=self.driver.find_element_by_xpath(x_path)
        input_element.click()

    def text_click(self,text):

        #print("\tClicking on: " + str(text))
        input_element=self.driver.find_element_by_link_text(text)
        input_element.click()

    def load_insist(self,x_path,value):

        #print("\tLooking for '"+value+"' on '"+x_path+"'.")
        refresh=False
        refreshed=False
        elementMatch=False
        start_time=time.time()
        while(elementMatch==False):
            refresh=self.should_browser_refresh(start_time,self.load_insist_limit,refreshed)
            if refresh==True and refreshed==False:
                print("Load insist failed looking for '"+value+"' on '"+x_path+"'. Refreshing browser and trying again")
                start_time=time.time()
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

    def click_view_more_options(self):

        CATEGORY_XPATH='//*[@id="mainPageContent"]/div[2]/div[1]/div[1]/div/ul[1]'
        VMO='View more options...'

        category_text=self.driver.find_element_by_xpath(CATEGORY_XPATH).get_attribute('textContent')

        #print("\tShould I click view more options?")
        if VMO in category_text:
            #print("\tYes.")
            element=self.driver.find_element_by_link_text(VMO)
            element.click()
        else:
            #print("\tNo.")
            raise NoSuchElementException("\t'"+VMO+"' was not found")

    def on_whitelist(self,branch):

        return any(x in branch[:,0].tolist() for x in self.whitelist)

    def next_category(self,branch):

        print("Category:",np.flipud(branch[:,0]))

        #Store the local category url for later navigation
        cat_url=self.driver.current_url
        #Store location of parent header on this category level
        parent_header_xpath='//*[@id="mainPageContent"]/div[1]/div[1]/span['+str(branch[len(branch)-1][2])+']/h1'

        #Determine if we are on a leaf level
        try:
            dummy=self.driver.find_element_by_xpath(branch[len(branch)-1][1]+'/ul/li[1]/a')
            leaf=False
        except NoSuchElementException:
            print("\tWe are in a leaf level")
            leaf=True

        if leaf==True:

            #Check if this leaf is on the white list
            if self.on_whitelist(branch):
                print("\tStart looking through ads")
                '''
                PUT THE SUB TO PARSE ADS RIGHT HERE
                '''
                print("\tContinue along the branch to find the next leaf...")
            else:
                print("\tElement not on whitelist. Start looking for next leaf...")
            self.go_to(branch[len(branch)-1][3])

        else:

            #We are not on a leaf level
            #Iterate through category indexes until NoSuchElementException
            next_category_index=0
            while(True):

                next_category_index=next_category_index+1

                #Keep retrying entering the category. Break if successful.
                while(True):

                    self.go_to(cat_url)
                    self.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span['+str(branch[len(branch)-1][2])+']/h1',str(branch[len(branch)-1][0])+' in City of Toronto')
                    
                    try:

                        next_category_xpath=branch[len(branch)-1][1]+'/ul/li['+str(next_category_index)+']/a'
                        next_category_name=self.driver.find_element_by_xpath(next_category_xpath).get_attribute('textContent').strip()

                        #Throw error if the next element is Fewer Elements (reached the end of the local sub-tree category index)
                        if next_category_name=='Fewer Options':
                            return
                        
                        #Navigate to the new sub-category
                        print("\tNavigating to: ",next_category_name)
                        self.xpath_click(next_category_xpath)
                        cat_header_index='//*[@id="mainPageContent"]/div[1]/div[1]/span['+str(int(branch[len(branch)-1][2])+1)+']/h1'
                        self.load_insist(cat_header_index,next_category_name+' in City of Toronto')

                        #Pass this sub-category recursively as the new main category level
                        next_branch=np.append(branch,[[next_category_name,branch[len(branch)-1][1]+'/ul',int(branch[len(branch)-1][2])+1,cat_url]],axis=0)
                        self.next_category(next_branch)

                        break
                        
                    except ElementNotVisibleException:
                        print('\tTrying to click view more options...')
                        self.click_view_more_options()
                    except TimeoutException:
                        print("\tBrowser refresh failed. Trying to locate element from the beginning...")
                    #except WebDriverException:
                    #    print("\tUnknown web driver exception. Trying to locate element from the beginning...")
                    #    self.driver.refresh()
                    except NoSuchElementException:
                        print("\tScraping process complete for this branch. Going up a level.")
                        return

class EndOfBranch(Exception):
    """Basic exception for reaching the end of a branch during recursion"""
    def __init__(self,branch, msg=None):
        if msg is None:
            msg="End of branch exception caught at " + str(branch)
        super(EndOfBranch, self).__init__(msg)
        self.branch=branch

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

    #try:
    branch=np.array([['Buy & Sell','//*[@id="mainPageContent"]/div[2]/div[1]/div[1]/div/ul[1]/ul',4,WI.driver.current_url]])
    try:
        WI.next_category(branch)
    except IndexError:
        print("Done iterating all categories. The webdriver will now shut down.")

    #Close/kill the driver
    WI.driver.quit()
