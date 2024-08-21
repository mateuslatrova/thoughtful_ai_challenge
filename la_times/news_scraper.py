import datetime
import re
from functools import lru_cache
from typing import List, Tuple

from dateutil.relativedelta import relativedelta
from RPA.Browser.Selenium import Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from la_times.news import Image, News
from la_times.utils import get_stdout_logger

MILISSECONDS_TO_SECONDS_FACTOR = 1 / 1000


class NewsScraper:

    SEARCH_BUTTON_XPATH = '//button[@data-element="search-button"]'
    SEARCH_BAR_XPATH = '//input[@data-element="search-form-input"]'

    TOPIC_FILTER_MENU_LOCATOR = 'xpath://ul[@data-name="Topics"]'

    SORT_BY_OPTIONS_LOCATOR = 'xpath://select[@class="select-input"]'

    NEWS_ELEMENTS_LOCATOR = (
        "//li/ps-promo[@class='promo promo-position-large promo-medium']"
    )
    NEWS_IMAGES_LOCATOR = (
        NEWS_ELEMENTS_LOCATOR + "//div[@class='promo-media']//img"
    )

    DOWNLOAD_DIRECTORY = "output/images"

    def __init__(
        self,
        search_phrase: str,
        news_topic: str,
        number_of_months_behind: int,
        wait_time_in_seconds: int,
        max_tries: int,
    ) -> None:
        self.search_phrase = search_phrase
        self.news_topic = news_topic
        self.number_of_months_behind = number_of_months_behind
        self.wait_time_in_seconds = wait_time_in_seconds
        self.max_tries = max_tries
        self.all_news: List[News] = []
        self.current_date_is_gte_minimum_date = True
        self.logger = get_stdout_logger(__file__)

        self.browser = Selenium()
        self.browser.set_download_directory(self.DOWNLOAD_DIRECTORY)

    def try_to_get_news_until_success(self) -> None:
        for try_number in range(1, self.max_tries + 1):
            try:
                self.logger.info(
                    f"Running NewsScraper for the {try_number} time..."
                )
                return self.get_news()

            except Exception:
                self._save_data_for_debugging_later()
                self.logger.exception("Exception: ")

            finally:
                self.logger.info("Closing browser...")
                self.close_browser()

    def get_news(self) -> List[News]:
        self.logger.info("Opening browser...")
        self._open_browser()

        self.logger.info("Configuring browser waiter...")
        self._configure_browser_waiter()

        self.logger.info(
            f"Searching for news with phrase '{self.search_phrase}'..."
        )
        self._search_news_with_phrase()

        self.logger.info(f"Filtering news for topic {self.news_topic}...")
        self._filter_news_for_selected_topic()

        self.logger.info("Sorting news by newest...")
        self._sort_news_in_decreasing_order_of_date()

        self.logger.info("Scraping news in defined time period...")
        self._scrape_news_in_defined_time_period()

        self.logger.info("Closing browser...")
        self.close_browser()

        return self.all_news

    def _open_browser(self) -> None:
        options = self._get_browser_options()

        self.browser.open_available_browser(
            url="https://www.latimes.com/",
            headless=True,
            # because there were bot detection issues when using Chrome.
            browser_selection="Firefox",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/113.0.0.0 Safari/537.36",
            options=options,
            preferences={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
            },
        )

    def _get_browser_options(self) -> webdriver.FirefoxOptions:
        options = webdriver.FirefoxOptions()

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")

        return options

    def _configure_browser_waiter(self) -> None:
        self.wait = WebDriverWait(
            self.browser.driver, self.wait_time_in_seconds
        )

    def _search_news_with_phrase(self) -> None:
        self.browser.wait_until_element_is_visible(
            self.SEARCH_BUTTON_XPATH, self.wait_time_in_seconds
        )
        self.browser.click_element_when_clickable(self.SEARCH_BUTTON_XPATH)

        self.browser.wait_until_element_is_visible(
            self.SEARCH_BAR_XPATH, self.wait_time_in_seconds
        )
        self.browser.input_text(self.SEARCH_BAR_XPATH, self.search_phrase)
        self.browser.press_keys(self.SEARCH_BAR_XPATH, "ENTER")

    def _filter_news_for_selected_topic(self) -> None:
        self.browser.wait_until_element_is_visible(
            self.TOPIC_FILTER_MENU_LOCATOR
        )
        topic_filter_menu = self.browser.find_element(
            self.TOPIC_FILTER_MENU_LOCATOR
        )

        selected_topic_element = topic_filter_menu.find_element(
            By.XPATH, f".//li[contains(., '{self.news_topic}')]"
        )

        checkbox = selected_topic_element.find_element(
            By.XPATH, ".//input[@type='checkbox']"
        )
        checkbox.click()

    def _sort_news_in_decreasing_order_of_date(self) -> None:
        self.browser.wait_until_element_is_visible(
            self.SORT_BY_OPTIONS_LOCATOR
        )
        select_element = self.browser.find_element(
            self.SORT_BY_OPTIONS_LOCATOR
        )

        select = Select(select_element)
        select.select_by_visible_text("Newest")

    def _scrape_news_in_defined_time_period(self) -> None:
        while self.current_date_is_gte_minimum_date:
            self._scrape_news_in_current_page()

            if self._there_are_more_pages_to_scrape():
                # This is necessary in the case where the defined time period
                # is greater than the period inside of which there are news in
                # the website, because when this happens
                # current_date_is_gte_minimum_date would never be set to False,
                # and this would become an infinite loop.
                self._go_to_next_news_page()

    def _scrape_news_in_current_page(self) -> None:
        news_elements = self._find_all_news_elements_in_current_page()

        for news_element in news_elements:

            news = self._extract_news_from_element(news_element)

            if news.date < self.minimum_date_for_news:
                self.current_date_is_gte_minimum_date = False
                break

            self.logger.info(f"Extracted news successfully: {news}")
            self.all_news.append(news)

    def _find_all_news_elements_in_current_page(self) -> List[WebElement]:
        self.wait.until(
            EC.visibility_of_all_elements_located(
                (By.XPATH, self.NEWS_ELEMENTS_LOCATOR)
            )
        )

        self.wait.until(
            EC.visibility_of_all_elements_located(
                (By.XPATH, self.NEWS_IMAGES_LOCATOR)
            )
        )

        news_elements = self.browser.find_elements(self.NEWS_ELEMENTS_LOCATOR)

        return news_elements

    def _extract_news_from_element(self, news_element: WebElement) -> News:
        title = self._extract_title_from_news_element(news_element)

        description = self._extract_description_from_news_element(news_element)

        date = self._extract_date_from_news_element(news_element)

        image = self._extract_image_from_news_element(news_element)

        news = News(title, description, date, image)

        return news

    def _extract_title_from_news_element(
        self, news_element: WebElement
    ) -> str:
        return news_element.find_element(
            By.XPATH, ".//h3[@class='promo-title']/a"
        ).text

    def _extract_description_from_news_element(
        self, news_element: WebElement
    ) -> str:
        description_element = news_element.find_element(
            By.XPATH, ".//p[@class='promo-description']"
        )

        return description_element.text

    def _extract_date_from_news_element(
        self, news_element: WebElement
    ) -> datetime.date:
        timestamp_in_milisseconds = news_element.find_element(
            By.XPATH, ".//p[@class='promo-timestamp']"
        ).get_attribute("data-timestamp")

        timestamp_in_seconds = (
            int(timestamp_in_milisseconds) * MILISSECONDS_TO_SECONDS_FACTOR
        )

        date = datetime.datetime.fromtimestamp(timestamp_in_seconds).date()

        return date

    def _extract_image_from_news_element(
        self, news_element: WebElement
    ) -> Image:
        image_element = news_element.find_element(
            By.XPATH, ".//div[@class='promo-media']//img"
        )

        image_url = image_element.get_attribute("src")

        image_binary_data = self._get_image_binary_data(image_url)

        return Image(image_binary_data)

    def _get_image_binary_data(self, image_url: str) -> bytes:
        original_window, _ = self._open_image_in_new_window(image_url)

        self._wait_until_image_is_fully_loaded()
        image_binary_data = self.browser.driver.get_screenshot_as_png()

        self.browser.close_window()
        self.browser.switch_window(original_window)

        return image_binary_data

    def _open_image_in_new_window(self, image_url: str) -> Tuple[str, str]:
        self.browser.execute_javascript(
            f"window.open('{image_url}', '_blank');"
        )

        all_windows = self.browser.get_window_handles()

        new_window = all_windows[-1]
        original_window = all_windows[0]

        self.browser.switch_window(new_window)

        return original_window, new_window

    def _wait_until_image_is_fully_loaded(self) -> None:
        image_locator = "xpath://img"
        self.browser.wait_until_element_is_visible(image_locator)
        image_element = self.browser.find_element(image_locator)
        self.wait.until(
            lambda d: d.execute_script(
                "return arguments[0].complete &&"
                " arguments[0].naturalWidth > 0",
                image_element,
            )
        )

    @property
    @lru_cache
    def minimum_date_for_news(self) -> datetime.date:
        number_of_months_behind = max(1, self.number_of_months_behind)

        minimum_date = datetime.date.today().replace(day=1)
        minimum_date -= relativedelta(months=number_of_months_behind - 1)

        return minimum_date

    def _there_are_more_pages_to_scrape(self) -> bool:
        pagination_element_xpath = (
            'xpath://div[@class="search-results-module-page-counts"]'
        )
        self.browser.wait_until_element_is_visible(pagination_element_xpath)
        pagination_element = self.browser.find_element(
            pagination_element_xpath
        )

        pagination_text = pagination_element.text

        pagination_numbers = re.findall(r"\d+", pagination_text)
        pagination_numbers = tuple(
            [int(number) for number in pagination_numbers]
        )

        current_page, total_number_of_pages = pagination_numbers

        return current_page < total_number_of_pages

    def _go_to_next_news_page(self) -> None:
        next_page_button_xpath = (
            "xpath://div[@class='search-results-module-next-page']/a"
        )

        self.browser.wait_until_element_is_visible(next_page_button_xpath)

        self.browser.find_element(next_page_button_xpath).click()

    def _save_data_for_debugging_later(self) -> None:
        page_html_content = self.browser.driver.page_source
        with open("output/page_source.html", "w", encoding="utf-8") as f:
            f.write(page_html_content)
        self.logger.info("Page HTML content saved to output/page_source.html")

        filename = self.browser.screenshot(filename="output/screenshot.png")
        self.logger.info(f"Screenshot saved in path: {filename}")

    def close_browser(self) -> None:
        self.browser.close_browser()
