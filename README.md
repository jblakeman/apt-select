apt-select
========

Select a fast, up to date Ubuntu apt mirror.

Features
-----------

- Tests latency to mirrors in [mirrors.txt](http://mirrors.ubuntu.com/mirrors.txt).
    - Each mirror is sent 3 TCP connection requests (on port 80) to gauge round trip time.

- Prints latency, status, and bandwidth capacity of the fastest mirrors in a ranked list.
    - Minimum round trip times determine rank.
    - Status and bandwidth are scraped from [launchpad](https://launchpad.net/ubuntu/+archivemirrors).

- Generates `sources.list` file using new mirror.
    - New mirror can either be chosen from a list or generated automatically (default).
    - Selected mirror is used to search `/etc/apt/sources.list` and replace all instances of the first urls labeled as the `main`/`security` repositories.

Dependencies
------------

Python HTML parser, BeautifulSoup

    sudo apt-get install 'python(3?)-bs4$'

Usage
-----

List arguments and options:

    ./apt-select.py -h

Choose from the top 5 mirrors, including those last updated a week ago:

    ./apt-select.py -c -t 3 -m one-week-behind

Find the top 10 mirrors, output latency info only, and don't generate new config file:

    ./apt-select.py -t 10 -p -l

[`update.sh`](https://github.com/jblakeman/apt-select/blob/master/update.sh) can be used to backup and replace `/etc/apt/sources.list` with the newly generated config file, but it might be better (safer) to examine, backup and replace it manually.
