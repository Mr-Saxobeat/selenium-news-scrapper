import re
import time
from typing import Tuple
from RPA.Browser.Selenium import Selenium
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support import expected_conditions

class Reuters:
    def __init__(self):
        self.browser = None
        self.search_phrase = "dollars"
        self.category = "test"

    def process(self):
        self.open_browser()
        self.search_news(self.search_phrase)
        # self.sort_by_newest()
        news_list = self.get_news_list()
        news_infos = self.extract_news_infos(news_list)
        print(news_infos)

    def open_browser(self):
        options = Options()
        options.page_load_strategy = 'eager'
        options.add_argument("--start-maximized")
        self.browser = Chrome(options=options)

        errors = [StaleElementReferenceException, NoSuchElementException]
        self.wait = WebDriverWait(self.browser, 30, ignored_exceptions=errors)

        self.browser.get("https://www.reuters.com/")

    def search_news(self, search_phrase):
        self.click_search_icon()
        self.insert_search_phrase_and_enter(search_phrase)

    def click_search_icon(self):
        locator = '//button[@aria-label="Open search bar"]'
        search_button = self.browser.find_element(By.XPATH, locator)
        self.wait.until(lambda d: search_button.is_displayed())
        search_button.click()

    def insert_search_phrase_and_enter(self, search_phrase):
        locator = '//input[@data-testid="FormField:input"]'
        search_input = self.browser.find_element(By.XPATH, locator)
        search_input.send_keys(search_phrase)
        submit_button_locator = '//button[@aria-label="Search"]'
        submit_button = self.browser.find_element(By.XPATH, submit_button_locator)
        submit_button.click()

    def sort_by_newest(self):
        locator = '//select[@class="Select-input"]'
        sort_dropdown = self.browser.get_webelement(locator)
        sort_dropdown.click()

        newest_option_locator = '//option[text()="Newest"]'
        newest_option = self.browser.get_webelement(newest_option_locator)
        newest_option.click()

    def get_news_list(self):
        result_list_locator = '//ul[@class="search-results__list__2SxSK"]'
        self.wait.until(expected_conditions.presence_of_element_located((By.XPATH, result_list_locator)))

        articles_locator = f'{result_list_locator}/li'
        articles_list = self.browser.find_elements(By.XPATH, articles_locator)

        return articles_list


    def extract_news_infos(self, news_list):
        news_infos = []
        for article in news_list:
            self.wait.until(lambda d: article.is_displayed())

            title_locator = './/header/a/span'
            title = article.find_element(By.XPATH, title_locator).text
            search_phrase_count = len(title.split(' '))

            date_locator = './/time'
            date = article.find_element(By.XPATH, date_locator).get_attribute('datetime')

            image_locator = '//img'
            image_element = article.find_element(By.XPATH, image_locator)
            self.wait.until(lambda d: image_element.is_displayed())
            image_src = image_element.get_attribute('src')
            image_name = self.extract_image_name(image_src)

            title_contains_money = self.check_title_contains_money(title)

            news_infos.append(
                {
                    "title": title,
                    "date": date,
                    "image_name": image_name,
                    "search_phrase_count": search_phrase_count,
                    "title_contains_money": title_contains_money
                }
            )

        return news_infos
    
    def extract_image_name(self, image_src):
        return image_src.split('/')[-1]
    
    def check_title_contains_money(self, title):
        money_regex = re.compile('|'.join([
                r'\$\d*\.\d{1,2}',
                r'\$\d+',
                r'\$\d+\.?',
                r'\d*\.\d{1,2} dollars',
                r'\d+ dollars',
                r'\d+\.? dollars',
                r'\d*\.\d{1,2} USD',
                r'\d+ USD',
                r'\d+\.? USD',
            ]))

        return money_regex.search(title) is not None

