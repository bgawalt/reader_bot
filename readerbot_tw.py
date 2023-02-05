"""Post about the reading list to Twitter.

Basic usage:
  python readerbot_tw.py config_file db_file

See README for all details.

Add arguments `test` to block any posting, and `force_run` to prevent deciding
not to post, e.g.:

  python readerbot_tw.py config_file db_file test
  python readerbot_tw.py config_file db_file force_run
  python readerbot_tw.py config_file db_file test force_run

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


import random
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


def main():
    config_filename = sys.argv[1]
    db_filename = sys.argv[2]

    dtime_now = datetime.now()
    # Either get something to post, or an error message:
    next_post, err_msg = reading_list.get_next_post(
        current_time=dtime_now, db_filename=db_filename,
        skip_gap_check=("force_run" in sys.argv)
    )

    if next_post is None:
        print("READERBOT_DECLINE", err_msg, sep="\n")
        return
    print(next_post.to_tuple())
    if "test"  in sys.argv:
        return

    auth = get_auth(config_filename)
    api = tweepy.API(auth)
    print("READERBOT_POSTING")
    api.update_status(update.message)
    posting_history.save_update(update, db_filename)


if __name__ == "__main__":
    main()
