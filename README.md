# ReaderBot

This is a utility that updates my Twitter feed with what I'm currently reading,
with
[tweets like these](https://twitter.com/search?q=from%3Abgawalt%20%23ReaderBot).

For the purposes of this bot, I keep a publicly-readable spreadsheet up to date
with progress through my reading list.  You can view the spreadsheet
[here](https://docs.google.com/spreadsheets/d/193ip3sbePZb1kLdFA60VzbpeCzSwX7BD5dzPxsfM28Q/edit#gid=0);
it's just a Google Sheets set to "Anybody With The Link Can View."

The bot then is able to read and parse that sheet as a CSV doc.  I've set it up
to mostly just report what book I'm reading right now and how much longer I'll
be reading it (based on an extremely crude average-pages-per-day metric).
But sometimes it also just reports the total amount of reading I have planned
for the near future, or the total amount of reading I've done since I started
keeping track like this.

## Dependencies

This bot uses the [Tweepy library](http://www.tweepy.org/), which I installed
with:

```
$ pip install tweepy
```

The routine also depends on you providing a text file which lays out the
Twitter OAuth configuration.  It should look like:

```
CONSUMER_KEY = [app key]
CONSUMER_SECRET = [app secret]
ACCESS_SECRET = [account secret]
ACCESS_KEY = [account key]
```

where everything outside the brackets is repeated verbatim.

You'll also need to specify, in `readerbot.py` itself, the path to the reading
list CSV.  It's the big long alphanumeric string from the Google Sheets URL.
