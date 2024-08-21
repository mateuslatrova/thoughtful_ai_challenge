from typing import Any, Dict, List

import pandas as pd

from la_times.news import News
from la_times.utils import get_stdout_logger


class NewsProcessor:

    def __init__(
        self,
        all_news: List[News],
        spreadsheet_path: str,
        images_directory: str,
    ) -> None:
        self.all_news = all_news
        self.spreadsheet_path = spreadsheet_path
        self.images_directory = images_directory
        self.logger = get_stdout_logger(__file__)

    def process_news(self):
        self.logger.info("Saving news images to local files...")
        self._save_news_images_locally()

        self.logger.info(
            f"Saving news data to spreadsheet '{self.spreadsheet_path}'..."
        )
        self._save_news_data_to_spreadsheet()

    def _save_news_images_locally(self) -> None:
        for news in self.all_news:
            image_filename = news.get_news_image_file_name()

            image_filepath = f"{self.images_directory}/{image_filename}"

            news.image.save_to_file(image_filepath)

            self.logger.info(f"Saved image to {image_filepath}.")

    def _save_news_data_to_spreadsheet(self) -> None:
        news_data_as_dict = self._get_news_data_as_dict()

        news_df = pd.DataFrame(news_data_as_dict)

        news_df.to_excel(self.spreadsheet_path, index=False)

    def _get_news_data_as_dict(self) -> Dict[str, List[Any]]:
        return {
            "title": [news.title for news in self.all_news],
            "description": [news.description for news in self.all_news],
            "date": [news.date for news in self.all_news],
            "image_filename": [
                news.get_news_image_file_name() for news in self.all_news
            ],
            "has_amount_of_money": [
                news.has_amount_of_money for news in self.all_news
            ],
        }
