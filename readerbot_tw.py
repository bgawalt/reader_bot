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


# TODO: Move to `posting_timer` library.
def get_previous_update(db_filename):
    conn = sqlite3.connect(db_filename)
    curr = conn.cursor()
    curr.execute("""
        SELECT BookTitle, Progress, FullMessage, TimestampSec
        FROM posts
        ORDER BY TimestampSec DESC
        LIMIT 1;
    """)
    update = reading_list.Update.FromTuple(curr.fetchone())
    conn.close()
    return update


# TODO: Move to `posting_timer` library.
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
        save_update(update, db_filename)
    else:
        print(update.ToTuple())


if __name__ == "__main__":
    main()
