apt-select
========

Speed up updates and upgrades by selecting a mirror with the lowest latency.

Features
-----------

- Tests TCP latency to Ubuntu mirrors
- Prints round trip time, status, and bandwidth of the fastest mirrors in a ranked list
- Generates new `sources.list` file automatically or with user chosen mirror

Dependencies
------------

- Python HTML parser, BeautifulSoup

####Install BeautifulSoup

Python 2

    sudo apt-get install python-bs4

Python 3

    sudo apt-get install python3-bs4


Usage
-----

    ./apt-select.py

For a list of arguments and options:

    ./apt-select.py --help

####Update `apt`

After the new `sources.list` file is generated, the update script can be used to backup and replace the current file:

    ./update.sh

