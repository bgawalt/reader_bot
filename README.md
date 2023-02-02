# ReaderBot

A bot that posts about my reading habit to my Mastodon (or Twitter).


### Quickstart

First, find the field `READ_DATA_SHEET_ID` in `reading_list.py` and make sure it
points to your properly-formatted, world-readable Google Sheet book list.

To post to Mastodon:

```
$ python3 readerbot_mdn.py user_cred.secret my_posts.db
```

To post to Twitter:

```
$ python3 readerbot_tw.py tw_oauth.secret my_posts.db
```

Where:

*  `user_cred.secret` are a credential file for posting to your Mastodon
    account, created with `Mastodon.py`.
*  `tw_oauth.secret` is a manually-crafted text file with four OAuth values
    used to post to your Twitter account.
*  `my_posts.db` is a SQLite3 database file containing a particular table called
    `posts`.

Read on to learn mandatory details about all of these!

## TODO

(I'm in the process of letting this post to Mastodon, so there's some 
refactoring going on right now.)

*  Document `reading_list` vs. `readerbot_tw` vs. `posting_history`
*  Pass in `READ_DATA_SHEET_ID`, the Google Sheets identifier, at run time
*  Type annotations
*  Use dataclasses annotations
*  Remove Tweepy dependency


## Casual Description

This is a utility that updates my social feeds (Twitter or Mastodon) with what
I'm currently reading, with
[posts like these](https://twitter.com/search?q=from%3Abgawalt%20%23ReaderBot).

For the purposes of this bot, I keep a publicly-readable spreadsheet up to date
with progress through my reading list.  You can view the spreadsheet
[here](https://docs.google.com/spreadsheets/d/193ip3sbePZb1kLdFA60VzbpeCzSwX7BD5dzPxsfM28Q/edit#gid=0);
it's just a Google Sheets set to "Anybody With The Link Can View."

The bot then is able to read and parse that sheet as a CSV doc.  I've set it up
to mostly just report what book I'm reading right now and how much longer I'll
be reading it (based on an extremely crude average-pages-per-day metric).
But sometimes it also just reports the total amount of reading I've signed 
myself up for, or the total amount of reading I've done since I started
keeping track.

I've set this script up to run automatically once per hour, though most hours it
just decides not to send a tweet and exits immediately.  I've set the operating
parameters so that there's around 6 days on average between each "#ReaderBot"
post, with a guaranteed rate limit of at least two days between each update.

If you'd like to also start using this, it should be pretty easy!  Just copy
the above spreadsheet's layout in your own Google sheet.  The dumbest part is
just getting the OAuth credentials in place, but if you tweet at, or email me
(bgawalt at gmail), I could help you make it through that.


## Detailed description

TK!

## Dependencies

This bot uses the [Tweepy library](http://www.tweepy.org/) and
[Mastodon.py](https://github.com/halcy/Mastodon.py) modules, which I installed
with:

```
$ pip install tweepy
$ pip3 install Mastodon.py
```

The Twitter routine in `readerbot_tw.py` depends on you providing a text file
which lays out the Twitter OAuth configuration.  It should look like:

```
CONSUMER_KEY = [app key]
CONSUMER_SECRET = [app secret]
ACCESS_SECRET = [account secret]
ACCESS_KEY = [account key]
```

where everything outside the brackets is repeated verbatim.

To post to Mastodon with `readerbot_mdn.py`, you'll need to set up 

You'll also need to specify, in `reading_list.py`, the data sheet ID for the
reading list CSV.  It's the big long alphanumeric string from the Google Sheets
URL, and it's stored as the constant `READ_DATA_SHEET_ID`.

OH! And the messages themselves -- `num_to_go_msg()`, `current_read_msg()`,
`page_rate_msg()` -- currently hardcode a shortlink to my own spreadsheet.
