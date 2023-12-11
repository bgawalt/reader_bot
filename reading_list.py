"""Library for fetching, representing, and summarizing the reading list.

The main attractions here are `get_next_post` and `READ_DATA_SHEET_ID`.
"""


from __future__ import annotations

import csv
import dataclasses
import datetime
import random

from typing import Optional
from urllib import request

import posting_history


# Spreadsheet read in one row as a time, as tuples.
# TODO: Move sheet ID to the config file
READ_DATA_SHEET_ID = "193ip3sbePZb1kLdFA60VzbpeCzSwX7BD5dzPxsfM28Q"
READ_DATA_SHEET_URL = (
    "https://spreadsheets.google.com/feeds/download/spreadsheets/"
    f"Export?key={READ_DATA_SHEET_ID}&exportFormat=csv")


def get_csv_tuples() -> list[tuple[str, ...]]:
    """Loads the Google Sheets sheet as a list of tuples of strings."""
    sheet_response = request.urlopen(READ_DATA_SHEET_URL)
    encoding = sheet_response.headers.get_content_charset('utf-8')
    sheet_lines = sheet_response.read().decode(encoding).split("\n")
    return [tuple(t) for t in csv.reader(sheet_lines)]


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
        return max(self.pages_total - self.pages_read, 0)

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
        self._time = timestamp_sec
        # Parse the spreadsheet's formula-derived values in Column E:
        self._total, self._read, self._num_days = (
            int(t[4].replace(",", "")) for t in tuples[1:4])
        self._page_rate, self._days_left, self._years_left = (
            float(t[4]) for t in tuples[4:7])
        self._finish_date = tuples[7][4]
        # Parse the rest of the sheet:
        self._books = tuple(Book.from_csv_row(t) for t in tuples[1:])
        self._in_progress = tuple(
            book for book in self._books
            if (book.pages_read > 0 and not book.done))
        self._num_done = sum(1 if book.done else 0 for book in self._books)
        self._pages_read = sum(book.pages_read for book in self._books)
        self._pages_total = sum(book.pages_total for book in self._books)

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
            f"Nov 12, 2016. That's {self._page_rate:0.1f} pages per day "
            f"({books_per_month:0.1f} books per month). https://goo.gl/pEH6yP")
        return posting_history.Post("page_rate", "page_rate", msg, self._time)


def get_next_post(
    current_time: datetime.datetime, db_filename: str,
    min_gap_days: int = 2, mean_gap_days: int = 6, skip_gap_check: bool=False
    ) -> tuple[Optional[posting_history.Post], str]:
    """Either returns a post to publish, or an explanation for why not.

    Args:
        current_time: What time is it, right now, when we're trying to post?
        db_filename: Path to the SQLite3 file containing posting history.
        min_gap_days: Never return a post to publish if it's been fewer than
            this many days since the last post was published.
        mean_gap_days: The target interarrival time for posts, in days.
        skip_gap_check: If True, ignore how long it's been since the last post
            when trying to return a post for this run.
    
    Returns:
        - First element is either a `posting_history.Post` to publish
            immediately, or is `None`.
        - Second element is a non-empty string iff the first element is `None`,
            this string explaining why there's no post to publish right now.
    """
    prev_post = posting_history.get_previous_update(db_filename)
    next_post_timestamp = prev_post.next_posting_timestamp_sec(
        min_gap_days=min_gap_days, mean_gap_days=mean_gap_days)
    if not skip_gap_check and (current_time.timestamp() < next_post_timestamp):
        prev_datetime = datetime.datetime.fromtimestamp(prev_post.timestamp_sec)
        next_datetime = datetime.datetime.fromtimestamp(next_post_timestamp)
        too_soon_msg = (
            "Too soon to post again.\n"
            f"Previous post: {prev_datetime}\n"
            f"Next post after: {next_datetime}")
        return (None, too_soon_msg)
    # Cool -- it's an acceptable time to post.
    # Let's see what's going on in the reading list:
    tuples = get_csv_tuples()
    library = BookCollection(tuples, int(current_time.timestamp()))
    candidate_post = None
    r = random.random()
    print(f"Rolled a {r:0.4f}")
    if r < 0.96:
        candidate_post = library.current_read_msg()
        if candidate_post is None:
            print("No currently-reading book to post!")
            r = 0.96 + 0.04 * random.random()
            print(f"Re-rolled a {r:0.4f}")
    if candidate_post is None and r < 0.95:
        candidate_post = library.page_rate_msg()
    if candidate_post is None:
        candidate_post = library.num_to_go_msg()
    # Check for dups:
    if candidate_post.is_duplicate(prev_post):
        dup_msg = (
            "Duplicate message attempt:\n"
            f"Prev post: {prev_post.message}\n"
            f"Attempted post: {candidate_post.message}"
        )
        return (None, dup_msg)
    return candidate_post, ""