"""Post about the reading list to BlueSky (or maybe some other AT Proto outlet).

Much thanks to Ian Klatz's ATProtoTools:
    https://klatz.co
    https://github.com/ianklatzco/atprototools/

Basic usage:
  python readerbot_atp.py account.config.json db_file

These two positional arguments are:

*  `account.config.json`, accepted by `bgsky.py`
*  `db_file`, a SQLite3 database with a table called `posts`; see schema below.
    This is used to coarsely rate limit posts.

Add arguments `test` to block any posting, and `force_run` to prevent deciding
not to post, e.g.:

  python readerbot_atp.py account.config.json db_file db_file test
  python readerbot_atp.py account.config.json db_file db_file force_run
  python readerbot_atp.py account.config.json db_file db_file test force_run


DB schema:

    CREATE TABLE IF NOT EXISTS posts(
        BookTitle text,
        Progress text,
        FullMessage text,
        TimestampSec integer
    );)

Dependencies needed:
  pip3 install requests
"""


import sys

from datetime import datetime, timezone

import bgsky_oct26
import posting_history
import reading_list


def main():
    creds = bgsky_oct26.Credentials.from_jsonfile(sys.argv[1])
    db_filename = sys.argv[2]

    dtime_now = datetime.now(timezone.utc)
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
        print("Found 'test' in cmd line arguments; exiting now.")
        return

    print("READERBOT_POSTING")
    builder = bgsky_oct26.PostBuilder(creds)
    builder.add_hashtag(tag="ReaderBot")
    builder.add_text(": ")
    builder.add_text(next_post.message)
    builder.add_text(" [")
    builder.add_link(
        link_text="Brian's Reading List",
        url="https://goo.gl/pEH6yP",
    )
    builder.add_text("]")
    builder.post()    
    posting_history.save_update(next_post, db_filename)


if __name__ == "__main__":
    main()