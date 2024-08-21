import datetime
import re


class Image:

    def __init__(self, binary_data: bytes) -> None:
        self.binary_data = binary_data

    def save_to_file(self, filepath: str) -> None:
        with open(filepath, "wb") as file:
            file.write(self.binary_data)


class News:

    AMOUNT_OF_MONEY_PATTERN = re.compile(
        r"(\$\d{1,3}(,\d{3})*(\.\d{2})?)|"
        r"(\d{1,3}(,\d{3})*(\.\d{2})?\s?(USD|dollars))",
        re.IGNORECASE,
    )

    def __init__(
        self, title: str, description: str, date: datetime.date, image: Image
    ) -> None:
        self.title = title
        self.description = description
        self.date = date
        self.image = image
        self.has_amount_of_money = (
            False
            if self.AMOUNT_OF_MONEY_PATTERN.search(self.title) is None
            else True
        )

    def __str__(self) -> str:
        return (
            f"\nTitle - '{self.title}'"
            f"\nDescription - '{self.description}'"
            f"\nDate: {self.date}"
            f"\nImage file name: {self.get_news_image_file_name()}"
        )

    def get_news_image_file_name(self) -> str:
        formatted_title = self.title.lower().replace(" ", "_")

        image_file_name = f"{formatted_title}_{self.date}.jpg"

        return image_file_name
