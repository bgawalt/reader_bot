# ReaderBot

A bot that posts about my reading habit to my Mastodon (or Twitter).


## Quickstart

First, find the field `READ_DATA_SHEET_ID` in `reading_list.py` and make sure it
points to your properly-formatted, world-readable Google Sheet book list.

Second, install the module dependencies, [Tweepy](http://www.tweepy.org/) and
[Mastodon.py](https://github.com/halcy/Mastodon.py):

```
$ pip3 install tweepy
$ pip3 install Mastodon.py
```

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

Read the in-depth description to learn mandatory details about all of these!


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


## In-depth description

This bot

1. reads a *spreadsheet*, 
2. summarizes the state of the spreadsheet with a *candidate post*,
3. compares the candidate post to *a history of previous posts*,
4. if the candidate seems novel and interesting compared to the most recent
    previous post, *posts* its message to Mastodon or Twitter,
5. and finally saves the post's detail as the latest entry in the history.

Each of those emphasized terms gets its own subsection here:

### The spreadsheet (`reading_list.py`)

The spreadsheet is the heart of this whole operation.

My situation, in late 2016, was that I'd bought a bunch of books and had no idea
when I'd actually finish reading them. So I started tracking my reading list in
a spreadsheet:
[this one](https://docs.google.com/spreadsheets/d/193ip3sbePZb1kLdFA60VzbpeCzSwX7BD5dzPxsfM28Q/edit#gid=0).
This was just supposed to give me a rough idea of when I could start buying more
books again, by tracking the rate I actually progressed through them.

The structure of the sheet has been mostly fixed since day one:

*  One row per book
    *  Row 1 has headers for each column
    *  Books start from Row 2 on
*  Column A stores the book's title
*  Column B stores the book's page count
*  Column C stores the number of pages I've read in the book
*  Columns D and E stored some derived statistics in rows 2 though 7, all of
   which lead to a "if I keep reading at the same average rate each day,
   the list will conclude by Date X" conclusion.

I just manually updated that every day or two as I worked through books.
It's easy!  I can do it from my phone, even.

(In 2022, I started also tracking dates I finished each book, usually in
Column D. That's been the only structural change.)

Only later did I get the idea that I could have a bot post updates about this
spreadsheet to my Twitter account.  It felt like an extremely minimalist DIY
Goodreads!

To this purpose, I made the Google Sheet world readable: "Anyone with the link
can: View."

The library `reading_list.py` in this repo downloads the CSV view of that
spreadsheet and parses it into nice Python objects:

*  The global string variable `READ_DATA_SHEET_ID` and its derived partner
    `READ_DATA_SHEET_URL` are hard-coded to point to my reading list
    spreadsheet.
*  The function `get_csv_tuples` downloads the sheet from that URL and parses it
    into  tuples of strings, one per Column.
*  Each tuple gets converted into a `Book` object; just the book's title and
    "progress meter" stats for how much of it I've read.
*  The sheet overall is represented as a single `BookCollection` object, which
    generates the messages that get posted to Mastodon/Twitter.  Note that these
    messages all include more hardcoded links to my spreadsheet, in `"goo.gl"`
    short form. More about these messages in the next subsection!
*  The most helpful entry in this module is `get_next_post`, which stitches
    together everything we're about to discuss to just hand you a post to
    publish (or an explanation for why no post is available).

**Note:** ReaderBot is extremely tightly coupled to this spreadsheet format!
It's not smart at all! It's just referencing and parsing these fields by rote 
instruction!

I have a standing TODO to breakout that hardcoding of my spreadsheet into
values you can pass in at runtime.  You never know when someone'll decide to
run their own version of this!

### The candidate posts

The class `reading_list.BookCollection` has three methods, which each generate
a candidate post as a function of the current state of the spreadsheet:

*  `num_to_go_msg` is in the original vision for this spreadsheet.  How long
    till I run out of books on my reading list?
*  `current_read_msg` is the most interesting of the three messages, in that it
    changes with greatest frequency.  What is a book I'm reading right now, and
    for how much longer will I be reading it before I'm done?
*  `page_rate_msg` is a backwards-looking summary: how many books and pages have
    I read since I started tracking all this?

These candidate posts are represented as objects of type `posting_history.Post`.

In terms of what makes for a successful candidate, there are three main
constraints on how this bot posts:

1.  The bot is not a long-lived process; it should turn up, decide whether or
    not to post, then exit, all in under a minute. (I don't have an always-on
    server where I can run a 24/7 Python job, even one that's mostly
    `time.sleep`ing.)
2.  It should always be a surprise to see a post from this bot (i.e., no fixed
    schedule like "every Tuesday at noon").
3.  It should always wait at least a couple days in between posts.
4.  It should never post two too-similar messages back-to-back.

For the first two and a half years of its life, this bot only explicitly handled
Constraints 1 and 2, and tried to satisfy 2 and 3 with just good luck.

Specifically, an hourly Cron job would start a new version of the job.
It would then calculate the SHA-1 value of a string representation of the
current system time, truncated to the current hour.  If that hash value was low
enough -- hooray! Time to post!

By tweaking that "low enough" threshold, I could *mostly* see the bot posting
once or twice a week.  *Usually,* there was enough time between posts that
the consecutive message contents would be meaningfully different, and that it
wouldn't seem too spammy.

But I got unlucky often enough that I decided to explicitly handle Constraints 2
and 4.

### The history of previous posts (`posting_history.py`)

In
[July 2019](https://github.com/bgawalt/reader_bot/commit/029719ebe532b19ce13b5b7383ad228b688c12d5) 
I introduced statefulness to ReaderBot. By keeping a local file of all posts
emitted, ReaderBot could reference the most recent post to make sure it wasn't
saying the same thing twice, or posting too frequently.

This posting history is implemented with a SQLite3 file, which contains a 
table named `posts`.  That table was created as:

```
CREATE TABLE IF NOT EXISTS posts(
    BookTitle text,
    Progress text,
    FullMessage text,
    TimestampSec integer
);
```

The semantics of these rows are:

*  `BookTitle`: A string found in Column A of the spreadsheet.
*  `Progress`: A string returned by `Book.rounded_ratio`
*  `FullMessage`: A string that would actually be posted to Mastodon/Twitter
*  `TimestampSec`: The time the post was published, as seconds since Jan 1 1970

ReaderBot interacts with this DB file via the `posting_history.py` library.
Rows of that table are represented with the class `posting_history.Post`,
with fields matching the name and type of these four columns.
(Note that `BookCollection.{num_to_go_msg, page_rate_msg}` use dummy placeholder
values for `book_title` and `progress` when generating their `Post`s.)

That class, `Post`, also defines the two-parameter `next_post_timestamp_sec`
method which takes in requirements on (a) how many days the bot *must* stay
silent after posting, via the `min_gap_days` parameter, and (b) the desired
typical interarrival gap between posts, via the `mean_gap_days` parameter.
The method hashes the four fields of `Post` to deterministically arrive at
a timestamp when the next post should appear.

The library functions `get_previous_update` and `save_update` perform the
actual DB query operations. (Each function pulls up its own local connection
and cursor on each call -- that's fine, since ReaderBot only calls each once
per run.  It just doesn't need to use the DB file all that often that it's
worth passing around a live conn/cursor pair.)

### Posting (`readerbot_{mdn, tw}.py`)

These two files, `readerbot_{mdn, tw}.py`, have genuine `main()` routines and
are what you actually call when you want to run ReaderBot.
Each has a hard-coded 80% chance of picking `current_read_msg` as its candidate
post for this run, with 10% chances each for the other two slower-evolving
messages.  They both rely simply on `reading_list.get_next_post` to abstract
away all the above detail and just retrieve something to post, or an error
message to forward to the human in charge.

They're both invoked from the command line with the same pair of required
positional arguments, plus two optional ones:

```
$ python3 readerbot_{venue}.py cred_file.secret post_history.db [test] [force_run]
```

`post_history.db` is just the SQLite3 DB file described earlier. You can use
the same history for both, or keep two separate -- it'll work okay either way.

But `cred_file.secret`'s contents depend on whether you're posting to Mastodon
or Twitter.  They both work on the principal that an *app* is posting on behalf
of a *user* to the social media *server*.  You need public-private keys to
establish both the app and user identities when authenticating with the server.

The two optional arguments are:

*  `test`: If you add this, everything runs *except* for actually posting to the
    social media account and saving a new entry in the posting history.
*  `force_run`: If you add this, the script ignores how long it's been since
    the last post on file was published.

#### Mastodon creds

`readerbot_mdn.py` relies on [Mastodon.py](https://github.com/halcy/Mastodon.py)
to handle API handshaking.

You can follow this example on how to establish an app, and give that app
permissions to post on behalf of your account, with the example I lifted from
[their README](https://github.com/halcy/Mastodon.py/blob/master/README.rst):

```
    from mastodon import Mastodon

    # Register your app! This only needs to be done once (per server, or when 
    # distributing rather than hosting an application, most likely per device and server). 
    # Uncomment the code and substitute in your information:
    '''
    Mastodon.create_app(
        'pytooterapp',
        api_base_url = 'https://mastodon.social',
        to_file = 'pytooter_clientcred.secret'
    )
    '''

    # Then, log in. This can be done every time your application starts (e.g. when writing a 
    # simple bot), or you can use the persisted information:
    mastodon = Mastodon(client_id = 'pytooter_clientcred.secret',)
    mastodon.log_in(
        username='my_login_email@example.com', 
        password='incrediblygoodpassword',
        scopes=['read', 'write'],  # bgawalt added this line
        to_file = 'pytooter_usercred.secret'
    )
```

Just a heads up, you need to pass *the email you used to register your account
with the Mastodon instance* in the `username` field there.  That confused me!
It's *not* your username on the instance itself!

Once this is done, use the `pytooter_usercred.secret` file generated by `log_in`
as the credential-file positional argument you give to ReaderBot.

#### Twitter creds

`readerbot_tw.py` uses Twitter's
[OAuth 1.0a flow](https://developer.twitter.com/en/docs/authentication/oauth-1-0a)
for getting permission to post to a Twitter account.  This means you have
"key" and "secret" values for both the "consumer" (the app you're posting with)
and "access" (the account you're posting to) roles.

I set up my app in like 2010 and I don't know how to set up a new one these
days!  Also they've just been yanking API keys away from apps over there now
that it's 2023, it's a nightmare.  Mine still works, though.

I use, for all my Twitter bots, this janky format for writing these values in
a file.  You need to paste the :

```
CONSUMER_KEY = [app key]
CONSUMER_SECRET = [app secret]
ACCESS_SECRET = [account secret]
ACCESS_KEY = [account key]
```

Write a text file with these four lines and pass it as the credential-file
positional argument you give to ReaderBot.

I have a TODO to move this to JSON.

This all depends on having the [Tweepy library](http://www.tweepy.org/) handle
the API interactions, so make sure you've run:

```
$ pip3 install tweepy
```

though I can migrate off of that library, someday.  TODO!


## TODO

*  Pass in `READ_DATA_SHEET_ID`, the Google Sheets identifier, at run time
*  Type annotations
*  Add dummy cold-start DB creator script
*  Use dataclasses annotations
*  Remove Tweepy dependency
*  Use JSON for Twitter cred file