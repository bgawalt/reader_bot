"""Post about the reading list to BlueSky (or maybe some other AT Proto outlet).

Much thanks to Ian Klatz's ATProtoTools:
    https://klatz.co
    https://github.com/ianklatzco/atprototools/

Basic usage:
  python readerbot_atp.py account.config db_file

These two positional arguments are:

*  `account.config`, a custom format "KEY + value\n" text file featuing server,
    username, and password details for posting to BlueSky. Expects KV pairs for:
    *  `ATP_HOST = `: the server hosting your PDS (https://bsky.social works)
    *  `ATP_USERNAME = `: your username on that server -- whatever string
        appears after "@" on your profile, use that.  I use "brian.gawalt.com".
    *  `ATP_PASSWORD = `: a password for that username on that server;
        app-specific passwords work here and are encouraged
*  `db_file`, a SQLite3 database with a table called `posts`; see schema below.
    This is used to coarsely rate limit posts.

Add arguments `test` to block any posting, and `force_run` to prevent deciding
not to post, e.g.:

  python readerbot_atp.py account.config db_file db_file test
  python readerbot_atp.py account.config db_file db_file force_run
  python readerbot_atp.py account.config db_file db_file test force_run


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


import dataclasses
import pprint
import requests
import sys

from collections.abc import Sequence
from datetime import datetime, timezone

import posting_history
import reading_list


def get_config(filename: str) -> dict[str, str]:
    with open(filename, 'r') as infile:
        config = {}
        for line in infile:
            spline = line.split(" = ")
            config[spline[0]] = spline[1].strip()
    return config


def get_auth_token_and_did(
    host: str, username: str, password: str) -> tuple[str, str]:
    """Returns (auth token, dist user id) pair for BSky server, user, pword."""
    token_request_params = {"identifier": username, "password": password}
    resp = requests.post(
        f"{host}/xrpc/com.atproto.server.createSession",
        json=token_request_params
    )
    auth_token = resp.json().get("accessJwt")
    if auth_token is None:
        raise ValueError("Whoopsie doodle, bad response:" + str(resp.json()))
    did = resp.json().get("did")
    return (auth_token, did)


@dataclasses.dataclass
class RichTextLink:
    url: str
    byte_start: int
    byte_end: int

    def __post_init__(self):
        if self.byte_end <= self.byte_start:
            raise ValueError(
                f"byte_end ({self.byte_end}) must be greater than "
                f"byte_start ({self.byte_start})")
    
    def to_json(self):
        # TODO uhhhh unclear how to type annotate this
        return {
            "index": {
                "byteStart": self.byte_start,
                "byteEnd": self.byte_end
            },
            "features": [
                {            
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": self.url
                }
            ]
        }


@dataclasses.dataclass
class RichTextMessage:
    message_text: str
    links: Sequence[RichTextLink]

    def to_json(self, timestamp_iso: str):
        # TODO type annotation
        return {
            "$type": "app.bsky.feed.post",
            "createdAt": timestamp_iso,
            "text": self.message_text,
            "facets": [link.to_json() for link in self.links]
        }


# Test run produced, July 1 2023:
# {'uri': 'at://did:plc:43nhmzgiugf65gwskj3kpfj5/app.bsky.feed.post/3jzi3r7uirc2d',
#  'cid': 'bafyreid4tnueqsgcg2meqq5cut4bf5vkyhqgdiwxl737coajkfzyo3wuke'}
def enrich_message(message: str) -> RichTextMessage:
    """Adds hyperlinks as rich text (#ReaderBot hashtag and the sheets URL)."""
    if not message.startswith("#ReaderBot"):
        raise ValueError(f"message must start with '#ReaderBot': {message}")
    hashtag_link = RichTextLink(
        # TODO: Make this URL depend on the actual ATProto host.
        url="https://bsky.app/search?q=%23ReaderBot",
        byte_start=0,
        byte_end=len("#ReaderBot".encode("UTF-8"))
    )
    # TODO: Make shortlink a constant, or better yet, a config param
    if not message.endswith("https://goo.gl/pEH6yP"):
        raise ValueError(
            f"message must end with 'https://goo.gl/pEH6yP': {message}")
    # TODO: cmon what's the actual str method for chopping off K chars
    msg_open_brace = message[:(-1 * len("https://goo.gl/pEH6yP"))] + "["
    sheet_start = len(msg_open_brace.encode("UTF-8"))
    msg_unclosed = msg_open_brace + "Brian's Reading List"
    sheet_end = len(msg_unclosed.encode("UTF-8"))
    sheet_link = RichTextLink(
        url="https://goo.gl/pEH6yP",
        byte_start=sheet_start,
        byte_end=sheet_end
    )
    return RichTextMessage(
        message_text=(msg_unclosed + "]"),
        links=(hashtag_link, sheet_link)
    )


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
        print("Found 'test' in cmd line arguments; exiting now.")
        return

    print("READERBOT_POSTING")
    config_kv = get_config(user_cred_filename)
    host = config_kv["ATP_HOST"]
    username = config_kv["ATP_USERNAME"]
    pword = config_kv["ATP_PASSWORD"]

    auth_token, did = get_auth_token_and_did(
        host=host, username=username, password=pword)

    timestamp_iso = dtime_now.isoformat().replace('+00:00', 'Z')
    headers = {"Authorization": f"Bearer {auth_token}"}
    post_params = {
        "collection": "app.bsky.feed.post",
        "$type": "app.bsky.feed.post",
        "repo": "{}".format(did),
        "record": enrich_message(next_post.message).to_json(timestamp_iso)
    }
    resp = requests.post(
        f"{host}/xrpc/com.atproto.repo.createRecord",
        json=post_params,
        headers=headers
    )
    print(resp.status_code)
    print(pprint.pprint(resp.json()))
    if resp.status_code != 200:
        raise RuntimeError("Posting failed!! POST_FAIL")
    posting_history.save_update(next_post, db_filename)


if __name__ == "__main__":
    main()

