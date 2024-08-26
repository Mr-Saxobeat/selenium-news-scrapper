import time
import os, shutil
import urllib
import re
from datetime import datetime
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from RPA.Browser.Selenium import Selenium
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
from common.excel import Excel

class LATimes:
    BASE_URL = 'https://www.latimes.com/'
    SPREADSHEET_NAME = 'latimes_news.xlsx'
    DEFAULT_IMAGE_TIMEOUT_SRC = 'image loading timed_out'

    def __init__(self):
        self.browser = None
        self.search_phrase = os.getenv('SEARCH_PHRASE', 'billion')
        self.months = int(os.getenv('MONTHS_RANGE', 1)) or 1
        self.next_page = True
        self.ignored_exceptions = (NoSuchElementException, StaleElementReferenceException)

    def process(self):
        self.clear_output_dir()
        self.open_browser()
        self.search_news(self.search_phrase)
        self.sort_by_newest()
        news_infos = self.get_news_infos()
        self.create_excel(news_infos)
        self.download_all_images(news_infos)

    def clear_output_dir(self):
        shutil.rmtree('./output', ignore_errors=True)
        os.makedirs('./output')

    def open_browser(self):
        options = Options()
        options.page_load_strategy = 'eager'
        options.add_argument('--window-size=1920,1080')
        self.browser = Selenium()
        self.browser.open_available_browser(self.BASE_URL, options=options, maximized=True)

    def search_news(self, search_phrase):
        self.click_search_icon()
        self.insert_search_phrase_and_submit(search_phrase)

    def click_search_icon(self):
        locator = '//button[@data-element="search-button"]'
        self.browser.wait_until_page_contains_element(locator)
        search_button = self.browser.find_element(locator)
        search_button.click()

    def insert_search_phrase_and_submit(self, search_phrase):
        input_locator = '//input[@data-element="search-form-input"]'
        self.browser.wait_until_page_contains_element(input_locator)
        search_input = self.browser.find_element(input_locator)
        search_input.send_keys(search_phrase)
        submit_button_locator = '//button[@data-element="search-submit-button"]'
        submit_button = self.browser.find_element(submit_button_locator)
        submit_button.click()

    def sort_by_newest(self):
        dropdown_locator = '//div[@class="search-results-module-sorts"]//select[@class="select-input"]'
        self.browser.wait_until_page_contains_element(dropdown_locator)
        sort_dropdown = self.browser.find_element(dropdown_locator)
        sort_dropdown.click()

        newest_option_locator = f'{dropdown_locator}//option[text()="Newest"]'
        newest_option = self.browser.find_element(newest_option_locator)
        newest_option.click()

    def get_news_infos(self):
        all_news_infos = []

        while self.next_page:
            time.sleep(2)
            news_list = self.get_news_list()
            news_infos = self.extract_news_infos(news_list)
            all_news_infos.extend(news_infos)

            self.goto_next_page(self.next_page)

        return all_news_infos

    def get_news_list(self):
        result_list_locator = '//ul[@class="search-results-module-results-menu"]'
        self.browser.wait_until_page_contains_element(result_list_locator)
        result_list = self.browser.find_element(result_list_locator)

        articles_locator = f'{result_list_locator}//li'
        self.browser.wait_until_page_contains_element(articles_locator)
        articles_list = self.browser.find_elements(articles_locator)

        return articles_list

    def extract_news_infos(self, news_list):
        news_infos = []
        for article in news_list:

            self.browser.wait_until_page_contains_element(article)
            self.browser.scroll_element_into_view(article)


            wait = WebDriverWait(article, 10, ignored_exceptions=self.ignored_exceptions)
            date_locator = './/p[@class="promo-timestamp"]'
            wait.until(expected_conditions.presence_of_element_located((By.XPATH, date_locator)))
            timestamp_str = article.find_element(By.XPATH, date_locator).get_attribute('data-timestamp')
            timestamp_int = float(timestamp_str)/1000
            date = datetime.fromtimestamp(timestamp_int, None)
            article_is_in_range = self.check_date_is_inside_range(date)
            if not article_is_in_range:
                self.next_page = False
                break

            title_locator = './/h3[@class="promo-title"]/a'
            wait.until(expected_conditions.presence_of_element_located((By.XPATH, title_locator)))
            title = article.find_element(By.XPATH, title_locator).text
            search_phrase_count = len(title.split(' '))

            image_src = self.extract_image_src(article, wait)
            image_name = image_src.split('/')[-1].replace('?url=', '')

            title_contains_money = self.check_title_contains_money(title)

            news_infos.append(
                {
                    "title": title,
                    "date": date,
                    "image_src": image_src,
                    "image_name": image_name,
                    "search_phrase_count": search_phrase_count,
                    "title_contains_money": title_contains_money
                }
            )

        return news_infos
    
    def extract_image_src(self, article, wait):
        image_src = ''
        try:
            image_locator = './/div[@class="promo-media"]/a/picture/img'
            wait.until(expected_conditions.presence_of_element_located((By.XPATH, image_locator)))
            image_element = article.find_element(By.XPATH, image_locator)
            image_src = image_element.get_attribute('src')
        except TimeoutException as e:
            image_src = 'image loading timed_out'
            
        return image_src

    def download_all_images(self, news_infos):
        for news_info in news_infos:
            image_url = news_info['image_src']
            image_name = news_info['image_name']
            self.download_image(image_url, image_name)

    def download_image(self, image_url, image_name):
        if image_url != self.DEFAULT_IMAGE_TIMEOUT_SRC:
            image_path = f'./output/{image_name}'
            urllib.request.urlretrieve(image_url, image_path)

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

        title_contains_money = money_regex.search(title) is not None
        return str(title_contains_money)

    def check_date_is_inside_range(self, date):
        current_date = datetime.now()
        month_diff = current_date.month - date.month
        date_is_inside_range = month_diff < self.months
        return date_is_inside_range

    def goto_next_page(self, next_page):
        if next_page:
            try:
                paginator_locator = '//div[@class="search-results-module-pagination"]'
                self.browser.wait_until_page_contains_element(paginator_locator)
                self.browser.scroll_element_into_view(paginator_locator)
                next_page_locator = '//div[@class="search-results-module-next-page"]/a'
                self.browser.wait_until_page_contains_element(next_page_locator, 10)

                url = self.browser.get_location()
                next_url = self.get_next_url(url)
                self.browser.go_to(next_url)
            except AssertionError as e:
                self.next_page = False

    def get_next_url(self, url: str):
        if 'p=' in url:
            splited_url = url.split('&')
            p_parameter = splited_url[2]
            current_page = int(p_parameter[2])
            new_p_parameter = f'{p_parameter[0:2]}{current_page + 1}'
            next_url = f'{splited_url[0]}&{splited_url[1]}&{new_p_parameter}'
        else:
            next_url = f'{url}&p=2'
        return next_url

    def create_excel(self, news_infos):
        excel = Excel()
        filename = f'./output/{self.SPREADSHEET_NAME}'
        excel.create_excel_file(filename, news_infos)