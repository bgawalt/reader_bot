"""Post about the reading list to Mastodon.

Basic usage:
  python readerbot_tw.py user_cred.secret db_file

These two positional arguments are:

*  `user_cred.secret`, the account's credentials file generated using
    `Mastodon.log_in`. 
*  `db_file`, a SQLite3 database with a table called `posts`; see schema below.
    This is used to coarsely rate limit posts.

Add arguments `test` to block any posting, and `force_run` to prevent deciding
not to post, e.g.:

  python readerbot_tw.py user_cred.secret db_file test
  python readerbot_tw.py user_cred.secret db_file force_run
  python readerbot_tw.py user_cred.secret db_file test force_run


DB schema:

    CREATE TABLE IF NOT EXISTS posts(
        BookTitle text,
        Progress text,
        FullMessage text,
        TimestampSec integer
    );)

Dependencies needed:
  pip3 install Mastodon.py
"""


import random
import sys
import time

from datetime import datetime, timedelta

import mastodon

import posting_history
import reading_list


def block_long_posts(update):
    if update is None:
        return None
    if len(update.message) > 270:
        return None
    return update


def block_duplicate_posts(curr_update, prev_update):
    if curr_update is None:
        return None
    if (curr_update.book_title == prev_update.book_title and
        curr_update.progress == prev_update.progress):
        return None
    return curr_update


def main():
    user_cred_filename = sys.argv[1]
    db_filename = sys.argv[2]

    one_hour = timedelta(hours=1)
    dtime = datetime.now()

    mdn = mastodon.Mastodon(access_token=user_cred_filename)

    prev_update = posting_history.get_previous_update(db_filename)

    if (not posting_history.decide_to_post(dtime, prev_update.timestamp_sec)
        and "force_run" not in sys.argv):
        print("READERBOT_DECLINE Decided not to post.")
        dt = dtime
        for _ in range(500):
            if posting_history.decide_to_post(dt, prev_update.timestamp_sec):
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
        print("Attempting 'current read' post")
        update = block_long_posts(library.current_read_msg())
        if update is None:
            print("  Too long!")
        update = block_duplicate_posts(update, prev_update)
        if update is None:
            print("  READERBOT_DUPE Exiting without posting.", update.message)
            sys.exit(0)
    if update is None and r < 0.9:
        print("Attempting 'page rate' post")
        update = block_long_posts(library.page_rate_msg())
    if update is None:
        print("Attempting 'num to go' post")
        update = block_long_posts(library.num_to_go_msg())
    if update is None:
        raise ValueError("No valid messages found in book collection")
    print(update.message)
    print(len(update.message))

    if "test" not in sys.argv:
        print("READERBOT_POSTING")
        mdn.status_post(status=update.message, visibility='public')
        posting_history.save_update(update, db_filename)
    else:
        print(update.to_tuple())


if __name__ == "__main__":
    main()
