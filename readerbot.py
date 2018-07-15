import tweepy
import urllib2
import csv
import sys
import random

# INSTALLED:
# pip install tweepy

# TODO: Move sheet ID to the config file
READ_DATA_SHEET_ID = "193ip3sbePZb1kLdFA60VzbpeCzSwX7BD5dzPxsfM28Q"
READ_DATA_SHEET_URL = "https://spreadsheets.google.com/feeds/download/spreadsheets/Export?key=%s&exportFormat=csv" % READ_DATA_SHEET_ID


class Book(object):

    def __init__(self, row):
        if len(row) < 3:
            raise ValueError("Invalid row: %s" + str(row),)
        self._title = row[0]
        self._total = int(row[1])
        self._read = int(row[2])
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

    def __init__(self, tuples):
        self._books = []
        self._in_progress = []
        self._num_done = 0
        self._pages_read = 0
        self._pages_total = 0
        for tid, t in enumerate(tuples):
            if tid == 0:
                continue
            elif tid == 1:
                self._total = int(t[4])
            elif tid == 2:
                self._read = int(t[4])
            elif tid == 3:
                self._num_days = int(t[4])
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
        return ("#ReaderBot: Brian has %d books left on his reading list. " +
                "He should finish them all by %s https://goo.gl/pEH6yP") % (
                    len(self._books) - self._num_done, self._finish_date)

    def current_read_msg(self):
        if not len(self._in_progress):
            raise ValueError("Empty in-progress list!")
        book = self._in_progress[random.randint(0, len(self._in_progress) -1)]
        days_left = int(book.pages_to_go()/self._page_rate) + 1
        return ("#ReaderBot: Brian is %s '%s' and should " +
                "finish in around %d days https://goo.gl/pEH6yP") % (
                    book.rounded_ratio(), book.title(), days_left)

    def page_rate_msg(self):
        return ("#ReaderBot: Brian has read %d pages since " +
                "Nov 12, 2016, or %0.0f pages per day " +
                "(%0.1f books per month) "
                "https://goo.gl/pEH6yP") % (
                    self._pages_read, self._page_rate,
                    float(30 * self._num_done) / (self._num_days))

    def messages(self):
        return (self.num_to_go_msg(), self.current_read_msg(),
                self.page_rate_msg())


def get_csv_tuples():
    csv_file = urllib2.urlopen(urllib2.Request(READ_DATA_SHEET_URL))
    return [t for t in csv.reader(csv_file)]


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


def main():
    # Let's have this trigger 12 times per day, seven days per week,
    # but only tweet like twice per week.  12*7 = 72; ~1/36
    if "force_run" not in sys.argv and random.random() > 0.03:
        print "No need to do anything this time."
        sys.exit(0)

    tuples = get_csv_tuples()
    library = BookCollection(tuples)
    msg = None
    r = 1
    for candidate in library.messages():
        new_r = random.random()
        if len(candidate) < 140 and new_r < r:
            r = new_r
            msg = candidate
    if msg is None:
        raise ValueError("No valid messages found in candidate set %s" % (
                         str(library.messages()),))

    print msg
    print len(msg)
    auth = get_auth(sys.argv[1])
    api = tweepy.API(auth)
    if "test" not in sys.argv:
        api.update_status(msg)


if __name__ == "__main__":
    main()
