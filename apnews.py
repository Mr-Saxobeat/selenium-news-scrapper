from RPA.Browser.Selenium import Selenium
from selenium.webdriver.chrome.options import Options

class APNews:
    def __init__(self):
        self.browser = None
        self.search_phrase = "coronavirus"
        self.category = "test"

    def process(self):
        self.open_browser()
        self.search_news(self.search_phrase)
        self.select_category(self.category)
        print("oi")

    def open_browser(self):
        self.browser = Selenium()
        options = Options()
        options.page_load_strategy = 'eager'
        self.browser.open_available_browser("https://apnews.com/", maximized=True, options=options)

    def search_news(self, search_phrase):
        self.click_search_icon()
        self.insert_search_phrase_and_enter(search_phrase)

    def click_search_icon(self):
        locator = '//button[@class="SearchOverlay-search-button"]'
        search_button = self.browser.get_webelement(locator)
        search_button.click()

    def insert_search_phrase_and_enter(self, search_phrase):
        locator = '//input[@class="SearchOverlay-search-input"]'
        search_input = self.browser.get_webelement(locator)
        search_input.send_keys(search_phrase)
        submit_button_locator = '//button[@class="SearchOverlay-search-submit"]'
        submit_button = self.browser.get_webelement(submit_button_locator)
        submit_button.click()

    def select_category(self, category):
        locator = '//bsp-toggler[@class="SearchFilter-content"]'
        category_dropdown = self.browser.get_webelement(locator)
        category_dropdown.click()