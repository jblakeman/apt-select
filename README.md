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

    sudo apt-get install python-bf4

Python 3

    sudo apt-get install python3-bf4


Usage
-----

From inside the directory, run:

    ./apt-select.py

####Update `apt`

After the new `sources.list` file is generated, the current file should be copied to another location before being replaced:

    sudo mv /etc/apt/sources.list /etc/apt/sources.list.backup && sudo mv sources.list /etc/apt/sources.list

