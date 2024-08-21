from robocorp import workitems
from robocorp.tasks import task

from la_times.allowed_topics import ALLOWED_TOPICS
from la_times.news_processor import NewsProcessor
from la_times.news_scraper import NewsScraper


@task
def main():
    LATimesNewsTask().run()


class LATimesNewsTask:

    def __init__(self):
        self.input_payload = workitems.inputs.current.payload
        self.search_phrase = self.input_payload["search_phrase"]
        self.news_topic = self.input_payload["news_topic"]
        self.number_of_months_behind = self.input_payload[
            "number_of_months_behind"
        ]
        self.wait_time_in_seconds = self.input_payload.get(
            "wait_time_in_seconds", 20
        )
        self.spreadsheet_path = self.input_payload.get(
            "spreadsheet_path", "output/data.xlsx"
        )
        self.images_directory = self.input_payload.get(
            "images_directory", "output"
        )
        self.max_tries = self.input_payload.get("max_tries", 2)

    def run(self):
        self._validate_inputs()

        scraped_news = NewsScraper(
            self.search_phrase,
            self.news_topic,
            self.number_of_months_behind,
            self.wait_time_in_seconds,
            self.max_tries,
        ).try_to_get_news_until_success()

        NewsProcessor(
            scraped_news, self.spreadsheet_path, self.images_directory
        ).process_news()

    def _validate_inputs(self):
        assert self.number_of_months_behind >= 0
        assert self.max_tries >= 1
        assert self.news_topic in ALLOWED_TOPICS


if __name__ == "__main__":
    main()
