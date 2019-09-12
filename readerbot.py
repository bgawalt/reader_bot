"""
Basic usage:
  python readerbot.py config_file

Add arguments `test` to block any posting, and `force_run` to prevent deciding
not to post, e.g.:

  python readerbot.py config_file db_file test
  python readerbot.py config_file db_file force_run
  python readerbot.py config_file db_file test force_run

If you just want to know when to expect more posts, use the flag `timetable`

  python readerbot.py timetable | grep POST

DB schema:

    CREATE TABLE IF NOT EXISTS posts(
        BookTitle text,
        Progress text,
        FullMessage text,
        TimestampSec integer
    );)

Dependencies needed:
  pip install tweepy
"""

from __future__ import print_function

import csv
import hashlib
import random
import sqlite3
import sys
import time
import tweepy

from urllib import request

from datetime import datetime, timedelta


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


def get_config(filename):
    with open(filename, 'r') as infile:
        config = {}
        for line in infile:
            spline = line.split(" = ")
            config[spline[0]] = spline[1].strip()
    return config


def get_auth(config_file):
    config = get_config(config_file)

    ckey = config["CONSUMER_KEY"]
    csec = config["CONSUMER_SECRET"]
    akey = config["ACCESS_KEY"]
    asec = config["ACCESS_SECRET"]

    auth = tweepy.OAuthHandler(ckey, csec)
    auth.set_access_token(akey, asec)
    return auth


def is_lucky_hour(dt, threshold):
    "Is the modulo-hash of the given datetime's YYYYMMDDHH string low enough?"
    denom = (2 ** 20)
    dt_str = dt.strftime("%Y%m%d%H")
    hash_val = int(hashlib.sha1(dt_str.encode('utf-8')).hexdigest(), 16)
    mod_hash_val = hash_val % denom
    return mod_hash_val < (threshold * denom)


def decide_to_post(dtime, prev_ts):
    "Is this currently a lucky hour?  Have we posted recently?"
    thresh = 0.012
    curr_time = time.mktime(dtime.timetuple())
    too_recent = (curr_time - prev_ts) < (3600 * 24 * 2.5)
    return not too_recent and is_lucky_hour(dtime, threshold=thresh)


def block_long_tweets(update):
    if update is None:
        return None
    if len(update.message) > 270:
        return None
    return update


def block_duplicate_tweets(curr_update, prev_update):
    if curr_update is None:
        return None
    if (curr_update.book_title == prev_update.book_title and
        curr_update.progress == prev_update.progress):
        return None
    return curr_update


def get_previous_update(db_filename):
    conn = sqlite3.connect(db_filename)
    curr = conn.cursor()
    curr.execute("""
        SELECT BookTitle, Progress, FullMessage, TimestampSec
        FROM posts
        ORDER BY TimestampSec DESC
        LIMIT 1;
    """)
    update = Update.FromTuple(curr.fetchone())
    conn.close()
    return update


def save_update(update, db_filename):
    conn = sqlite3.connect(db_filename)
    curr = conn.cursor()
    curr.execute("""
        INSERT INTO posts VALUES (?, ?, ?, ?)
    """, update.ToTuple())
    conn.commit()
    conn.close()


def main():
    config_filename = sys.argv[1]
    db_filename = sys.argv[2]

    one_hour = timedelta(hours=1)
    dtime = datetime.now()

    prev_update = get_previous_update(db_filename)

    if (not decide_to_post(dtime, prev_update.time) and
        "force_run" not in sys.argv):
        print("READERBOT_DECLINE Decided not to post.")
        dt = dtime
        for _ in range(500):
            if decide_to_post(dt, prev_update.time):
                print("NEXT POST AT:", dt)
                break
            dt += one_hour
        sys.exit(0)

    tuples = get_csv_tuples()
    library = BookCollection(tuples, int(time.mktime(dtime.timetuple())))
    update = None
    r = random.random()
    print("Random draw: %0.3f" % (r,))
    if r < 0.8:
        print("Attempting 'current read' tweet")
        update = block_long_tweets(library.current_read_msg())
        if update is None:
            print("  Too long!")
        update = block_duplicate_tweets(update, prev_update)
        if update is None:
            print("  A dupe!")
    if update is None and r < 0.9:
        print("Attempting 'page rate' tweet")
        update = block_long_tweets(library.page_rate_msg())
    if update is None:
        print("Attempting 'num to go' tweet")
        update = block_long_tweets(library.num_to_go_msg())
    if update is None:
        raise ValueError("No valid messages found in book collection")
    print(update.message)
    print(len(update.message))
    auth = get_auth(config_filename)
    api = tweepy.API(auth)
    if "test" not in sys.argv:
        print("READERBOT_POSTING")
        api.update_status(update.message)
        save_update(update, db_filename)
    else:
        print(update.ToTuple())


if __name__ == "__main__":
    main()
