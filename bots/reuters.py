import os, shutil
import urllib
import re
from datetime import datetime
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
from common.excel import Excel

class Reuters:
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
        options.add_argument("--start-maximized")
        self.browser = Chrome(options=options)

        self.errors = [StaleElementReferenceException, NoSuchElementException]
        self.wait = WebDriverWait(self.browser, 30, ignored_exceptions=self.errors)

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
        locator = '//button[@id="sortby"]'
        self.wait.until(expected_conditions.presence_of_element_located((By.XPATH, locator)))
        sort_dropdown = self.browser.find_element(By.XPATH, locator)
        sort_dropdown.click()

        newest_option_locator = '//div[@data-testid="Select-Popup"]/ul/li[@data-key="Newest"]'
        newest_option = self.browser.find_element(By.XPATH, newest_option_locator)
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
        result_list_locator = '//ul[@class="search-results__list__2SxSK"]'
        self.wait.until(expected_conditions.presence_of_element_located((By.XPATH, result_list_locator)))

        articles_locator = f'{result_list_locator}/li'
        articles_list = self.browser.find_elements(By.XPATH, articles_locator)

        return articles_list

    def extract_news_infos(self, news_list):
        news_infos = []
        for article in news_list:
            self.wait.until(lambda d: article.is_displayed())

            date_locator = './/time'
            date_str = article.find_element(By.XPATH, date_locator).get_attribute('datetime')
            date = datetime.strptime(date_str.split('T')[0], "%Y-%m-%d")
            article_is_in_range = self.check_date_is_inside_range(date)
            if not article_is_in_range:
                self.next_page = False
                break

            title_locator = './/header/a/span'
            title = article.find_element(By.XPATH, title_locator).text
            search_phrase_count = len(title.split(' '))

            image_name = self.extract_image_name(article)

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
    
    def extract_image_name(self, article):
        image_name = ''
        try:
            self.browser.execute_script("arguments[0].scrollIntoView();", article)
            image_locator = './/img'
            wait = WebDriverWait(article, 10, ignored_exceptions=self.errors)
            wait.until(expected_conditions.presence_of_element_located((By.XPATH, image_locator)))
            image_element = article.find_element(By.XPATH, image_locator)
            wait.until(lambda d: image_element.is_displayed())
            image_src = image_element.get_attribute('src')
            image_name = image_src.split('/')[-1]
        except TimeoutException as e:
            image_name = 'image loading timed_out'
            

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
            next_page_locator = '//button[contains(@aria-label, "Next stories")]'
            self.wait.until(expected_conditions.presence_of_element_located((By.XPATH, next_page_locator)))
            next_page_button = self.browser.find_element(By.XPATH, next_page_locator)
            next_page_button.click()

    def create_excel(self, news_infos):
        excel = Excel()
        excel.create_excel_file('./outputs/reuters_news.xlsx', news_infos)