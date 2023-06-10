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


import requests
import sys

from datetime import datetime, timezone

#import posting_history
#import reading_list


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


def main():
    user_cred_filename = sys.argv[1]
    db_filename = sys.argv[2]

    config_kv = get_config(user_cred_filename)
    host = config_kv["ATP_HOST"]
    username = config_kv["ATP_USERNAME"]
    pword = config_kv["ATP_PASSWORD"]

    auth_token, did = get_auth_token_and_did(
        host=host, username=username, password=pword)

    dtime_now = datetime.now(timezone.utc)
    timestamp = dtime_now.isoformat().replace('+00:00', 'Z')
    headers = {"Authorization": f"Bearer {auth_token}"}
    post_contents = (
        f"I'm posting this from python and it's {timestamp} in Greenwich")
    post_params = {
        "collection": "app.bsky.feed.post",
        "$type": "app.bsky.feed.post",
        "repo": "{}".format(did),
        "record": {
            "$type": "app.bsky.feed.post",
            "createdAt": timestamp,
            "text": post_contents
        }
    }
    resp = requests.post(
        f"{host}/xrpc/com.atproto.repo.createRecord",
        json=post_params,
        headers=headers
    )
    print(resp.status_code)
    print(resp)

if __name__ == "__main__":
    main()
