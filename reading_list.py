"""Library for fetching and representing the reading list."""


from __future__ import annotations

import csv
import dataclasses
import random

from urllib import request

import posting_history


# Spreadsheet read in one row as a time, as tuples.
# TODO: Move sheet ID to the config file
READ_DATA_SHEET_ID = "193ip3sbePZb1kLdFA60VzbpeCzSwX7BD5dzPxsfM28Q"
READ_DATA_SHEET_URL = (
    "https://spreadsheets.google.com/feeds/download/spreadsheets/"
    f"Export?key={READ_DATA_SHEET_ID}&exportFormat=csv")


@dataclasses.dataclass(frozen=True)
class Book:
    """One book from the reading list: title, total pages, and read pages."""
    title: str  # (BGawalt sneaks both author and title into this field.)
    pages_total: int
    pages_read: int

    @staticmethod
    def from_csv_row(row: tuple[str, ...]) -> Book:
        if len(row) < 3:
            raise ValueError(f"Invalid row: {row}")
        title = row[0]
        total = int(row[1].replace(",", ""))
        read = int(row[2].replace(",", ""))
        return Book(title=title, pages_total=total, pages_read=read)

    def __post_init__(self):
        if self.pages_read > self.pages_total:
            raise ValueError(
                "Mismatch in Read and Total: " +
                f"{self.pages_read} vs. {self.pages_total}")

    @property
    def pages_to_go(self) -> int:
        return max([self.pages_total - self.pages_read, 0])

    @property
    def done(self) -> bool:
        return self.pages_total == self.pages_read

    @property
    def rounded_ratio(self) -> str:
        """The string that fills in the blank: 'Brian is ____ [book title].'"""
        ratio = float(self.pages_read) / self.pages_total
        if ratio == 0:
            return "not yet reading"
        elif ratio < 0.125:
            return "just starting"
        elif ratio < 0.375:
            return "a quarter through"
        elif ratio < 0.625:
            return "halfway done with"
        elif ratio < 0.875:
            return "three-quarters into"
        elif ratio < 1:
            return "almost done with"
        return "done with"


class BookCollection:

    def __init__(self, tuples, timestamp_sec):
        self._books = []
        self._in_progress = []
        self._num_done = 0
        self._pages_read = 0
        self._pages_total = 0
        self._time = timestamp_sec
        for tid, t in enumerate(tuples):
            # Parse the derived values from Column E
            if tid == 0:
                # The first line is empty
                continue
            elif tid == 1:
                self._total = int(t[4].replace(",", ""))
            elif tid == 2:
                self._read = int(t[4].replace(",", ""))
            elif tid == 3:
                self._num_days = int(t[4].replace(",", ""))
            elif tid == 4:
                self._page_rate = float(t[4])
            elif tid == 5:
                self._days_left = float(t[4])
            elif tid == 6:
                self._years_left = float(t[4])
            elif tid == 7:
                self._finish_date = t[4]
            book = Book.from_csv_row(t)
            if book.done:
                self._num_done += 1
            if book.pages_read > 0 and not book.done:
                self._in_progress.append(book)
            self._pages_read += book.pages_read
            self._pages_total += book.pages_total
            self._books.append(book)

    def books(self):
        return self._books

    def num_to_go_msg(self):
        msg = (
            f"#ReaderBot: Brian has {len(self._books) - self._num_done} books "
            "left on his reading list. He should finish them all by "
            f"{self._finish_date}. https://goo.gl/pEH6yP")
        return posting_history.Post("num_to_go", "num_to_go", msg, self._time)

    def current_read_msg(self):
        if not len(self._in_progress):
            print("Empty in-progress list!")
            return None
        book = self._in_progress[random.randint(0, len(self._in_progress) - 1)]
        days_left = int(book.pages_to_go / self._page_rate) + 1
        msg = (
            f"#ReaderBot: Brian is {book.rounded_ratio} {book.title} and "
            f"should finish in around {days_left} days. https://goo.gl/pEH6yP")
        return posting_history.Post(
            book.title, book.rounded_ratio, msg, self._time)

    def page_rate_msg(self):
        books_per_month = float(30 * self._num_done) / (self._num_days)
        msg = (
            f"#ReaderBot: Brian has read {self._pages_read:,} pages across "
            f"{self._num_done + len(self._in_progress)} books since "
            f"Nov 12, 2016. That's {self._page_rate:0.0} pages per day "
            f"({books_per_month:0.1} books per month). https://goo.gl/pEH6yP")
        return posting_history.Post("page_rate", "page_rate", msg, self._time)


def get_csv_tuples() -> list[tuple[str, ...]]:
    """Loads the Google Sheets sheet as a list of tuples of strings."""
    sheet_response = request.urlopen(READ_DATA_SHEET_URL)
    encoding = sheet_response.headers.get_content_charset('utf-8')
    sheet_lines = sheet_response.read().decode(encoding).split("\n")
    return [t for t in csv.reader(sheet_lines)]
