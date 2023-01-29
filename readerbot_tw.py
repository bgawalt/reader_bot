"""
Basic usage:
  python readerbot_tw.py config_file

Add arguments `test` to block any posting, and `force_run` to prevent deciding
not to post, e.g.:

  python readerbot_tw.py config_file db_file test
  python readerbot_tw.py config_file db_file force_run
  python readerbot_tw.py config_file db_file test force_run

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


import hashlib
import random
import sqlite3
import sys
import time

from datetime import datetime, timedelta

import tweepy

import posting_history
import reading_list


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


def main():
    config_filename = sys.argv[1]
    db_filename = sys.argv[2]

    one_hour = timedelta(hours=1)
    dtime = datetime.now()

    prev_update = posting_history.get_previous_update(db_filename)

    if (not posting_history.decide_to_post(dtime, prev_update.timestamp_sec)
        and "force_run" not in sys.argv):
        print("READERBOT_DECLINE Decided not to post.")
        dt = dtime
        for _ in range(500):
            if decide_to_post(dt, prev_update.time):
                print("NEXT POST AT:", dt)
                break
            dt += one_hour
        sys.exit(0)

    tuples = reading_list.get_csv_tuples()
    library = reading_list.BookCollection(
        tuples, int(time.mktime(dtime.timetuple())))
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
            print("  READERBOT_DUPE Exiting without tweeting.", update.message)
            sys.exit(0)
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
        posting_history.save_update(update, db_filename)
    else:
        print(update.to_tuple())


if __name__ == "__main__":
    main()
