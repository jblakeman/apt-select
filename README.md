apt-select
========

Select a fast, up to date Ubuntu apt mirror.

Features
-----------

- Tests latency to each mirror found in [mirrors.txt](http://mirrors.ubuntu.com/mirrors.txt).
    - Each mirror is sent 3 TCP connection requests on port 80 to gauge round trip time.

- Prints latency, status, and bandwidth of the fastest mirrors in a ranked list.
    - Minimum round trip times determine rank.
    - Status and bandwidth is scraped from [launchpad](https://launchpad.net/ubuntu/+archivemirrors).

- Generates new `sources.list` file.
    - New mirror can either be chosen or generated automatically (default).
    - Selected mirror is used to search `/etc/apt/sources.list` and replace all instances of the first urls labeled as the `main` and `security` repositories.

Dependencies
------------

- Python HTML parser, BeautifulSoup

Usage
-----

For a list of arguments and options:

    ./apt-select.py -h

####Examples####
Choose from the top 5 mirrors, including those last updated a week ago:

    ./apt-select -c -t 3 -m one-week-behind

Find the top 10 mirrors, output latency info only, and don't generate new config file:

    ./apt-select -t 10 -p -l

[`update.sh`](https://github.com/jblakeman/apt-select/blob/master/update.sh) can be used to backup and replace `/etc/apt/sources.list` with the newly generated config file, but it might be better (safer) to examine, backup and replace it manually.

