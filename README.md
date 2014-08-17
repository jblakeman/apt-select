apt-select
========

Speed up updates and upgrades by selecting a mirror with the lowest latency.

Features
-----------

- Gets list of Ubuntu mirrors
- Tests TCP latency to each mirror
- Prints rank, round trip time, status, and bandwidth of the 5 fastest mirrors
- Generates new `sources.list` file with user chosen mirror

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

From inside the directory, run:

    ./apt-select.py

####Update `apt`

After the new `sources.list` file is generated, use the update script to backup and replace the current file:

    ./update.sh

