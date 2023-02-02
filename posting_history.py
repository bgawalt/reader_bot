"""A library to track the posts the bot has already published.

This requires a SQLite3 database with a table called `posts`.

Its schema should be:

    CREATE TABLE IF NOT EXISTS posts(
        BookTitle text,
        Progress text,
        FullMessage text,
        TimestampSec integer
    );)
"""


from __future__ import annotations

import dataclasses
import hashlib
import sqlite3
import time

from datetime import datetime


@dataclasses.dataclass(frozen=True)
class Post:
    """A post published by ReaderBot."""
    book_title: str
    progress: str
    message: str
    timestamp_sec: int

    @staticmethod
    def from_tuple(db_tuple: tuple[str, str, str, str]) -> Post:
        """Parse a tuple from the SQLite table as a Post."""
        title, prog, msg, time = db_tuple
        return Post(title, prog, msg, int(time))

    def to_tuple(self) -> tuple[str, str, str, int]:
        """(Title, progress, message, posting time)."""
        return (
            self.book_title, self.progress, self.message, self.timestamp_sec)


def is_lucky_hour(dt: datetime, threshold: float) -> bool:
    """Is the modulo-hash of the given datetime's YYYYMMDDHH low enough?"""
    denom = (2 ** 20)
    dt_str = dt.strftime("%Y%m%d%H")
    hash_val = int(hashlib.sha1(dt_str.encode('utf-8')).hexdigest(), 16)
    mod_hash_val = hash_val % denom
    return mod_hash_val < (threshold * denom)


def decide_to_post(now: datetime, prev_ts_sec: int) -> bool:
    """Is this currently a lucky hour?  Have we posted recently?"""
    thresh = 0.012
    now_ts_sec = time.mktime(now.timetuple())
    too_recent = (now_ts_sec - prev_ts_sec) < (3600 * 24 * 2.5)
    return not too_recent and is_lucky_hour(now, threshold=thresh)


def get_previous_update(db_filename: str) -> Post:
    conn = sqlite3.connect(db_filename)
    curr = conn.cursor()
    curr.execute("""
        SELECT BookTitle, Progress, FullMessage, TimestampSec
        FROM posts
        ORDER BY TimestampSec DESC
        LIMIT 1;
    """)
    post = Post.from_tuple(curr.fetchone())
    conn.close()
    return post


def save_update(post: Post, db_filename: str):
    """Put the given Post's details into the posting history table."""
    conn = sqlite3.connect(db_filename)
    curr = conn.cursor()
    curr.execute("""
        INSERT INTO posts VALUES (?, ?, ?, ?)
    """, post.to_tuple())
    conn.commit()
    conn.close()
