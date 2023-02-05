"""A library to track the posts the bot has already published.

This requires a SQLite3 database with a table called `posts`.

Its schema should be:

    CREATE TABLE IF NOT EXISTS posts(
        BookTitle text,
        Progress text,
        FullMessage text,
        TimestampSec integer
    );
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

    def is_duplicate(self, other: Post) -> bool:
        """Does this Post match the other Post?"""
        return (self.book_title == other.book_title
                and self.progress == other.progress)

    def next_posting_timestamp_sec(
        self, min_gap_days: float, mean_gap_days: float) -> int:
        """When (seconds since epoch) should we allow the next post?"""
        if mean_gap_days <= min_gap_days:
            raise ValueError('mean gap must exceed min gap; '
                             f'{mean_gap_days} vs. {min_gap_days}')
        # Use this SHA-1 on this post's contents to pseudorandomly sample
        # a value between zero and one; store it as `frac`:
        hash_target = (self.book_title + self.progress
                       + self.message + str(self.timestamp_sec))
        hash_val = int(
            hashlib.sha1(hash_target.encode('utf-8')).hexdigest(), 16)
        denom = 1024  # ten bits is plenty of precision here
        frac = float(hash_val % denom) / denom
        # We want a pseudo-sample uniformly over a range that starts at
        # `min_gap_days` and whose midpoint is `mean_gap_days`.
        # That makes the width of that range is 2 * (`mean` - `min`).
        width_days = 2 * (mean_gap_days - min_gap_days)
        gap_days = min_gap_days + (frac * width_days)
        sec_per_day = 24 * 3600
        gap_sec = gap_days * sec_per_day
        return int(self.timestamp_sec + gap_sec)


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
