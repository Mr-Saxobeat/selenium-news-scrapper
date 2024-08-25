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
    def __init__(self):
        self.browser = None
        self.search_phrase = "dollars"
        self.months = int(os.getenv('MONTHS_RANGE', 1)) or 1
        self.next_page = True

    def process(self):
        self.clear_output_dir()
        self.open_browser()
        self.search_news(self.search_phrase)
        self.sort_by_newest()
        news_infos = self.get_news_infos()
        self.create_excel(news_infos)
        self.download_all_images(news_infos)
        print(news_infos)

    def clear_output_dir(self):
        output_dir = './output'
        shutil.rmtree(output_dir, ignore_errors=True)
        os.makedirs(output_dir)
        os.makedirs('./output/images')

    def open_browser(self):
        options = Options()
        options.page_load_strategy = 'eager'
        self.browser: Selenium = Selenium()
        self.browser.set_selenium_speed(1)
        self.browser.open_available_browser("https://www.latimes.com/", options=options, maximized=True)

    def close_popup(self):
        popup_locator = '//a[@class="met-flyout-close"]'
        self.browser.wait_until_page_contains(popup_locator, 30)
        close_button = self.browser.find_element(popup_locator)
        close_button.click()

    def search_news(self, search_phrase):
        self.click_search_icon()
        self.insert_search_phrase_and_enter(search_phrase)

    def click_search_icon(self):
        locator = '//button[@data-element="search-button"]'
        self.browser.wait_until_page_contains_element(locator)
        search_button = self.browser.find_element(locator)
        search_button.click()

    def insert_search_phrase_and_enter(self, search_phrase):
        locator = '//input[@data-element="search-form-input"]'
        self.browser.wait_until_page_contains_element(locator)
        search_input = self.browser.find_element(locator)
        search_input.send_keys(search_phrase)
        submit_button_locator = '//button[@data-element="search-submit-button"]'
        submit_button = self.browser.find_element(submit_button_locator)
        submit_button.click()

    def sort_by_newest(self):
        locator = '//div[@class="search-results-module-sorts"]//select[@class="select-input"]'
        self.browser.wait_until_page_contains_element(locator)
        sort_dropdown = self.browser.find_element(locator)
        sort_dropdown.click()

        newest_option_locator = f'{locator}//option[text()="Newest"]'
        newest_option = self.browser.find_element(newest_option_locator)
        newest_option.click()

    def get_news_infos(self):
        all_news_infos = []

        while self.next_page:
            news_list = self.get_news_list()
            news_infos = self.extract_news_infos(news_list)
            all_news_infos.extend(news_infos)

            self.click_next_page(self.next_page)

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
            self.browser.scroll_element_into_view(article)

            try:
                date_locator = '//p[@class="promo-timestamp"]'
                self.browser.wait_until_page_contains_element(date_locator)
                timestamp_str = self.browser.find_element(date_locator, article).get_attribute('data-timestamp')
            except StaleElementReferenceException as e:
                date_locator = '//p[@class="promo-timestamp"]'
                self.browser.wait_until_page_contains_element(date_locator)
                timestamp_str = self.browser.find_element(date_locator, article).get_attribute('data-timestamp')

            timestamp_int = float(timestamp_str)/1000
            date = datetime.fromtimestamp(timestamp_int, None)
            article_is_in_range = self.check_date_is_inside_range(date)
            if not article_is_in_range:
                self.next_page = False
                break

            title_locator = '//h3/a'
            self.browser.wait_until_page_contains_element(title_locator)
            title = self.browser.find_element(title_locator, article).text
            search_phrase_count = len(title.split(' '))

            image_src = self.extract_image_src(article)
            image_name = image_src.split('/')[-1]

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
    
    def extract_image_src(self, article):
        image_src = ''
        try:
            # self.browser.execute_script("arguments[0].scrollIntoView();", article)
            # self.browser.execute_javascript("arguments[0].scrollIntoView();", article)
            image_locator = '//div[@class="promo-media"]/a/picture/img'
            # self.browser.wait_until_page_contains_element(image_locator)
            
            self.browser.wait_until_page_contains_element(image_locator)
            
            image_element = self.browser.find_element(image_locator, parent=article)
            
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
        image_path = f'./output/images/{image_name}'
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

    def click_next_page(self, next_page):
        if next_page:
            # self.close_popup()
            footer_locator = '//footer'
            self.browser.wait_until_page_contains_element(footer_locator)
            self.browser.scroll_element_into_view(footer_locator)
            next_page_locator = '//div[@class="search-results-module-next-page"]/a'
            self.browser.wait_until_page_contains_element(next_page_locator)
            next_page_button = self.browser.find_element(next_page_locator)
            next_page_button.click()

    def create_excel(self, news_infos):
        excel = Excel()
        excel.create_excel_file('./output/reuters_news.xlsx', news_infos)