import selenium as selenium
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotVisibleException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException

import numpy as np
import configparser
import time
import os
import urllib.request
import datetime

import psycopg2 as pg2

class WebInterface:

    def __init__(self):

        self.category_index = 0
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.whitelist = config.get('WebInterface', 'Whitelist').split('//')
        self.load_insist_limit = int(config.get('WebInterface', 'Load Insist Limit'))
        self.image_location = config.get('WebInterface', 'Image Location')

        self.user= config.get('Database', 'User')
        self.password = config.get('Database', 'Password')
        self.database = config.get('Database', 'Database')
        
    def get_driver(self):

        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        # options.add_argument("--headless")
        options.add_experimental_option("useAutomationExtension",False)
        options.add_experimental_option("prefs", {"profile.default_content_settings.cookies": 2})
        options.add_argument("--test-type")
        options.add_argument("--start-maximized")
        options.add_argument("--no-first-run")
        options.binary_location = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"

        self.driver = webdriver.Chrome(chrome_options=options)

    def go_to(self, link):

        if link != self.driver.current_url:
            self.driver.get(link)

    def enter_text(self, x_path, value, submit=False):

        input_element = self.driver.find_element_by_xpath(x_path)
        input_element.send_keys(value)
        if submit:
            input_element.submit()

    def xpath_click(self, x_path):

        input_element = self.driver.find_element_by_xpath(x_path)
        input_element.click()

    def text_click(self, text):

        input_element = self.driver.find_element_by_link_text(text)
        input_element.click()

    def load_insist(self, x_path, value=''):

        refresh = False
        refreshed = False
        element_match = False
        start_time = time.time()
        while not element_match:
            refresh = self.should_browser_refresh(start_time, self.load_insist_limit,refreshed)
            if refresh == True and refreshed == False:
                self.print_branch(branch, "Load insist failed looking for '"+value+"' on '" + x_path +
                                  "'. Refreshing browser and trying again")
                start_time = time.time()
                self.driver.refresh()
                refresh = False
                refreshed = True
            try:
                target_element = self.driver.find_element_by_xpath(x_path)
                if value in target_element.text:
                    element_match = True
            except NoSuchElementException:
                pass
            time.sleep(0.1)

    def should_browser_refresh(self, start, limit, refreshed):

        if time.time()-start>limit:
            if refreshed:
                raise TimeoutException("Timeout Occured")
            return True
        else:
            return False

    def click_view_more_options(self):

        CATEGORY_XPATH = '//*[@id="mainPageContent"]/div[2]/div[1]/div[1]/div/ul[1]'
        VMO = 'View more options...'

        category_text = self.driver.find_element_by_xpath(CATEGORY_XPATH).get_attribute('textContent')

        if VMO in category_text:
            element = self.driver.find_element_by_link_text(VMO)
            element.click()
        else:
            raise NoSuchElementException("\t'"+VMO+"' was not found")

    def on_whitelist(self, branch):

        return any(x in branch[:, 0].tolist() for x in self.whitelist)

    def print_branch(self, branch, message):
        print('\t'*len(branch)+message)

    def save_image(self,id,branch_str):

        src = self.driver.find_element_by_xpath('//*[@id="mainHeroImage"]/img').get_attribute('src')
        if not os.path.exists(self.image_location + "//" + branch_str):
            os.makedirs(self.image_location + "//" + branch_str)
        image_loc=self.image_location + "//" + branch_str + "//" + id + ".png"
        if not os.path.exists(image_loc):
            urllib.request.urlretrieve(src, image_loc)

        return image_loc

    def save_ad(self,branch):

        ad_id=self.driver.find_element_by_xpath("//ul[contains(@class,'crumbList')]"
                            "//*[contains(@class,'currentCrumb')]/span").get_attribute('textContent')
        title=self.driver.find_element_by_xpath("//div[@itemtype='http://schema.org/Product']"
                            "//div[contains(@class,'itemTitleWrapper')]"
                            "//div[contains(@class,'mainColumn')]"
                            "//h1[@itemprop='name']").get_attribute('textContent')
        price=self.driver.find_element_by_xpath("//div[@itemtype='http://schema.org/Product']/"
                                                "div[contains(@class,'itemTitleWrapper')]//"
                                                "div[contains(@class,'mainColumn')]//"
                                                "div[contains(@class,'priceContainer')]").get_attribute('textContent')
        try:
            loc=self.driver.find_element_by_xpath("//div[@itemtype='http://schema.org/Place']"
                                "//*[contains(@itemprop,'address')]").get_attribute('textContent')
        except NoSuchElementException:
            loc=''
        desc=self.driver.find_element_by_xpath("//div[@itemtype='http://schema.org/Product']"
                            "//div[contains(@class,'itemInfo')]"
                            "//div[contains(@class,'showMoreWrapper')]"
                            "//div[contains(@class,'showMoreChild')]"
                            "//div[contains(@class,'descriptionContainer')]"
                            "//div[@itemprop='description']").get_attribute('textContent')
        try:
            date_posted=self.driver.find_element_by_xpath("//div[@itemtype='http://schema.org/Product']"
                                     "/div[contains(@class,'itemTitleWrapper')]"
                                    "//div[contains(@class,'sidebarColumn')]"
                                    "//div[contains(@class,'itemMeta')]"
                                    "//div[@itemprop='datePosted']").get_attribute('content')
        except NoSuchElementException:
            # Sometimes they don't expose the posting date...
            date_posted=None
        branch_str = '//'.join(branch[:, 0].astype(str).tolist())

        self.print_branch(branch, "Saving Ad image locally...")
        image_loc = self.save_image(ad_id,branch_str)

        self.print_branch(branch,"Saving Ad to SQL...")
        self.save_ad_to_sql(title, price, loc, desc, ad_id, image_loc, self.driver.current_url, branch_str, date_posted)

    def save_ad_to_sql(self, title, price, location, description, ad_id, image_loc, url, branch_str, date_posted=None):

        conn = pg2.connect(database=self.database, user=self.user, password=self.password)
        cur = conn.cursor()
        dt = str(datetime.datetime.now())
        sql = "INSERT INTO kijiji_ads (title, price, location, description, " \
            "ad_id, image_loc, url, date_posted, branch, last_updated) " \
            "VALUES " \
            "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) " \
            "ON CONFLICT (ad_id) " \
            "DO UPDATE " \
            "SET title = EXCLUDED.title, " \
            "price = EXCLUDED.price, " \
            "description = EXCLUDED.description, " \
            "last_updated = EXCLUDED.last_updated;"
        data = (title, price, location, description, ad_id, image_loc, url, date_posted, branch_str, dt)
        cur.execute(sql, data)
        conn.commit()
        cur.close()
        conn.close()

    def get_ads(self, branch):

        START_URL = self.driver.current_url
        LAST_URL = START_URL

        counter = 0
        div_buffer = 0
        while(True):

            try:
                counter += 1
                time.sleep(1)
                x_path = '//*[@id="mainPageContent"]/div[2]/div[3]/div/div['+str(counter)+']/div/div[2]/div/div[2]/a'
                self.xpath_click(x_path)
                self.load_insist('//*[@id="ViewItemPage"]/div[5]/div[1]/div[1]/div/h1')
                title = self.driver.find_element_by_xpath('//*[@id="ViewItemPage"]/div[5]/div[1]/div[1]/div/h1').get_attribute('textContent')

            except NoSuchElementException as error:
                div_buffer += 1
                if div_buffer > 10:
                    div_buffer = 0
                    counter = 0
                    self.print_branch(branch, "Trying to click next...")
                    self.text_click('Next >')
                    self.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]')
                    self.print_branch(branch, "I clicked next...")
                    LAST_URL = self.driver.current_url
                continue

            except Exception as error:
                self.print_branch(branch,str(error))
                raise Exception(str(error))

            print("\n")
            self.print_branch(branch, str(counter)+" Ad: "+title)

            try:
                self.save_ad(branch)
            except Exception as error:
                raise AdError(str(error))

            self.go_to(LAST_URL)
            div_buffer = 0

        self.go_to(START_URL)

    def next_category(self,branch):

        self.print_branch(branch, "Category: "+str(np.flipud(branch[:, 0])))

        # Store the local category url for later navigation
        START_URL = self.driver.current_url

        # Determine if we are on a leaf level
        try:
            dummy = self.driver.find_element_by_xpath(branch[-1][1]+'/ul/li[1]/a')
            leaf = False
        except NoSuchElementException:
            self.print_branch(branch, "We are in a leaf level")
            leaf = True

        if leaf == True:

            # Check if this leaf is on the white list
            if self.on_whitelist(branch):
                self.print_branch(branch, "Start looking through ads")

                self.get_ads(branch)

                self.print_branch(branch, "Continue along the branch to find the next leaf...")
            else:
                self.print_branch(branch, "Element not on whitelist. Start looking for next leaf...")
            self.go_to(branch[-1][3])

        else:

            # We are not on a leaf level
            # Iterate through category indexes until NoSuchElementException
            next_category_index = 0
            while True:

                next_category_index += 1

                # Keep retrying entering the category. Break if successful.
                while True:

                    self.go_to(START_URL)
                    self.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span['+str(branch[-1][2])+']/h1',
                                     str(branch[-1][0]))
                    
                    try:

                        next_category_xpath = branch[-1][1]+'/ul/li['+str(next_category_index)+']/a'
                        next_category_name = self.driver.find_element_by_xpath(next_category_xpath)\
                            .get_attribute('textContent').strip()

                        # Throw error if the next element is Fewer Elements
                        # (reached the end of the local sub-tree category index)
                        if next_category_name == 'Fewer Options':
                            return
                        
                        # Navigate to the new sub-category
                        self.print_branch(branch, "Navigating to: "+next_category_name)
                        self.xpath_click(next_category_xpath)
                        cat_header_index = '//*[@id="mainPageContent"]/div[1]/div[1]/span['+str(int(branch[-1][2])+1) +\
                                           ']/h1'
                        self.load_insist(cat_header_index, next_category_name)

                        # Pass this sub-category recursively as the new main category level
                        next_branch=np.append(branch, [[next_category_name, branch[-1][1]+'/ul',
                                                       int(branch[-1][2])+1, START_URL]], axis=0)
                        self.next_category(next_branch)

                        break
                        
                    except ElementNotVisibleException:
                        self.print_branch(branch,'Trying to click view more options...')
                        self.click_view_more_options()
                    except TimeoutException:
                        self.print_branch(branch,
                                          "Browser refresh failed. Trying to locate element from the beginning...")
                    except NoSuchElementException:
                        self.print_branch(branch, "Scraping process complete for this branch. Going up a level.")
                        return


class EndOfBranch(Exception):
    """Basic exception for reaching the end of a branch during recursion"""
    def __init__(self, branch, msg=None):
        if msg is None:
            msg = "End of branch exception caught at " + str(branch)
        super(EndOfBranch, self).__init__(msg)
        self.branch = branch

class AdError(Exception):
    """Basic exception for an error occuring on the ad level"""
    def __init__(self, branch, msg=None):
        if msg is None:
            msg = "Error extracting ad at: " + str(branch)
        super(EndOfBranch, self).__init__(msg)
        self.branch = branch

if __name__ == "__main__":

    # Instantiate Web Interface
    WI = WebInterface()

    print("Instantiating the web driver...")

    # Instantiate the web driver
    WI.get_driver()

    print("Navigating to the first category...")

    # Navigate to Kijiji
    WI.go_to('https://www.kijiji.ca/')

    # Go to Toronto in Kijiji
    WI.xpath_click('//*[@id="SearchLocationPicker"]')
    WI.text_click('Ontario (M - Z)')
    WI.text_click('Toronto (GTA)')
    WI.text_click('City of Toronto')
    
    # Wait untill City of Toronto is loaded
    WI.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span[3]/h1','City of Toronto')

    # Go to buy/sell
    WI.xpath_click('//*[@id="SearchCategory"]')
    WI.text_click('Buy & Sell')

    # Wait untill Buy & Sell in City of Toronto is loaded
    WI.load_insist('//*[@id="mainPageContent"]/div[1]/div[1]/span[4]/h1','Buy & Sell in City of Toronto')

    branch=np.array([['Buy & Sell','//*[@id="mainPageContent"]/div[2]/div[1]/div[1]/div/ul[1]/ul', 4,
                      WI.driver.current_url]])
    try:
        WI.next_category(branch)
    except IndexError:
        print("Done iterating all categories. The webdriver will now shut down.")

    # Close/kill the driver
    WI.driver.quit()
