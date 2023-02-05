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


import sys

from datetime import datetime

import mastodon

import posting_history
import reading_list


def main():
    user_cred_filename = sys.argv[1]
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

    print("READERBOT_POSTING")
    mdn = mastodon.Mastodon(access_token=user_cred_filename)
    mdn.status_post(status=next_post.message, visibility='public')
    posting_history.save_update(next_post, db_filename)


if __name__ == "__main__":
    main()
