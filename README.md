# foxtail

CLI program to print recent firefox bookmarks to stdout using base Python library.

Simply searches the `firefoix_dir` (by default `~/.mozilla/firefox`) for `places.sqlite`, queries
the database for recent bookmarks added within the specified window (by default 7 days).

Requires Python 3.10 or higher.


## Installation:

Download this directory/zip file to execute in current directory, or make an alias/link to this
executable in your `PATH`.

For example (assuming `./local/bin` is in `PATH`),

    $ curl https://raw.githubusercontent.com/BlakeJC94/scratchpad/main/bookmarks/foxtail/__main__.py > ~/.local/bin/foxtail
    $ chmod a+x ~/.local/bin/foxtail

So now this can be called with

    $ foxtail [firefox_dir] [--hours <HH>] [--days <DD>]
