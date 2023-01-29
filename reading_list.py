"""Library for fetching and representing the reading list."""


from __future__ import print_function

import csv
import random

from urllib import request


# Spreadsheet read in one row as a time, as tuples.
# TODO: Move sheet ID to the config file
READ_DATA_SHEET_ID = "193ip3sbePZb1kLdFA60VzbpeCzSwX7BD5dzPxsfM28Q"
READ_DATA_SHEET_URL = "https://spreadsheets.google.com/feeds/download/spreadsheets/Export?key=%s&exportFormat=csv" % READ_DATA_SHEET_ID


class Book(object):
    "Turns a row-tuple into a single book: title, total pages, and read pages."

    def __init__(self, row):
        if len(row) < 3:
            raise ValueError("Invalid row: %s" + str(row),)
        self._title = row[0]
        self._total = int(row[1].replace(",", ""))
        self._read = int(row[2].replace(",", ""))
        if self._read > self._total:
            raise ValueError("Mismatch in Read and Total for row: %s" %
                             (str(row),))

    def title(self):
        return self._title

    def pages_to_go(self):
        return max([self.pages_total() - self.pages_read(), 0])

    def done(self):
        return self.pages_total() == self.pages_read()

    def pages_total(self):
        return self._total

    def pages_read(self):
        return self._read

    def rounded_ratio(self):
        # Fill in the blank: "Brian is ____ [book title]"
        ratio = float(self.pages_read())/self.pages_total()
        if ratio == 0:
            return "not yet reading"
        elif ratio < 0.125:
            return "just starting"
        elif ratio < 0.375:
            return "about a quarter through"
        elif ratio < 0.625:
            return "around halfway done with"
        elif ratio < 0.875:
            return "like three-quarters into"
        elif ratio < 1:
            return "almost done with"
        return "done with"


class BookCollection(object):

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
            book = Book(t)
            if book.done():
                self._num_done += 1
            if book.pages_read() > 0 and not book.done():
                self._in_progress.append(book)
            self._pages_read += book.pages_read()
            self._pages_total += book.pages_total()
            self._books.append(book)

    def books(self):
        return self._books

    def num_to_go_msg(self):
        msg = ("#ReaderBot: Brian has %d books left on his reading list. " +
               "He should finish them all by %s. https://goo.gl/pEH6yP") % (
                 len(self._books) - self._num_done, self._finish_date)
        return Update("num_to_go", "num_to_go", msg, self._time)

    def current_read_msg(self):
        if not len(self._in_progress):
            print("Empty in-progress list!")
            return None
        book = self._in_progress[random.randint(0, len(self._in_progress) - 1)]
        days_left = int(book.pages_to_go()/self._page_rate) + 1
        msg = ("#ReaderBot: Brian is %s %s and should " +
               "finish in around %d days. https://goo.gl/pEH6yP") % (
                    book.rounded_ratio(), book.title(), days_left)
        return Update(book.title(), book.rounded_ratio(), msg, self._time)

    def page_rate_msg(self):
        msg = ("#ReaderBot: Brian has read %s pages across %d books since " +
                "Nov 12, 2016. That's %0.0f pages per day " +
                "(%0.1f books per month). https://goo.gl/pEH6yP") % (
                    "{:,}".format(self._pages_read),
                    self._num_done + len(self._in_progress), self._page_rate,
                    float(30 * self._num_done) / (self._num_days))
        return Update("page_rate", "page_rate", msg, self._time)


# TODO: Move to `posting_timer` library.
class Update(object):

    def __init__(self, book_title, progress, message, timestamp_sec):
        self.book_title = book_title
        self.progress = progress
        self.message = message
        self.time = int(timestamp_sec)

    def ToTuple(self):
        return (self.book_title, self.progress, self.message, self.time)

    @staticmethod
    def FromTuple(db_tuple):
        title, prog, msg, time = db_tuple
        return Update(title, prog, msg, time)


def get_csv_tuples():
    sheet_response = request.urlopen(READ_DATA_SHEET_URL)
    encoding = sheet_response.headers.get_content_charset('utf-8')
    sheet_lines = sheet_response.read().decode(encoding).split("\n")
    return [t for t in csv.reader(sheet_lines)]