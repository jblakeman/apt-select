apt-select
==========

Find a fast, up-to-date Ubuntu Archive Mirror.

Features
--------

* Tests latency to mirrors in `mirrors.txt <http://mirrors.ubuntu.com/mirrors.txt>`_.
    - 3 requests are sent to each mirror, minumum round trip time being used for rank.

* Reports latency, status, and bandwidth capacity of the fastest mirrors in a ranked list.
    - Status and bandwidth are scraped from `launchpad <https://launchpad.net/ubuntu/+archivemirrors/>`_.

* Generates `sources.list` file using new mirror.
    - New mirror can be chosen from a list or selected automatically using the top ranked mirror (default).

Installation
------------

Target most recent release::

    pip install apt-select

or::

    pip3 install apt-select

Target project master branch::

    pip install git+https://github.com/jblakeman/apt-select.git

or::

    git clone https://github.com/jblakeman/apt-select
    python apt-select/setup.py install

Invocation
----------
::

    $ apt-select --help
    usage: apt-select [-h] [-t NUMBER] [-m STATUS | -p] [-c | -l]

    Find the fastest Ubuntu apt mirrors.
    Generate new sources.list file.

    optional arguments:
      -h, --help            show this help message and exit
      -t NUMBER, --top-number NUMBER
                            specify number of mirrors to return
                            default: 1
      -m STATUS, --min-status STATUS
                            return mirrors with minimum status
                            choices:
                               up-to-date
                               one-day-behind
                               two-days-behind
                               one-week-behind
                               unknown
                            default: up-to-date
      -p, --ping-only       rank mirror(s) by latency only, disregard status(es)
                            cannot be used with -m/--min-status
      -c, --choose          choose mirror from a list
                            requires -t/--top-num NUMBER where NUMBER > 1
      -l, --list            print list of mirrors only, don't generate file
                        cannot be used with -c/--choose

Examples
--------

Choose from the top 3 mirrors, including those last updated a week ago:::

    apt-select -c -t 3 -m one-week-behind

Find the top 10 mirrors, output latency info only, and don't generate new config file:::

    apt-select -t 10 -p -l

After new sources.list is generated in current working directory, backup and replace to update apt:::

    sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup && \
    sudo mv sources.list /etc/apt/

Supported URI Types
-------------------

Currently, `http` and `ftp` are supported.

`/etc/apt/sources.list` should contain sources in the following format:::

    [deb|deb-src] [http|ftp]://mirror.example.com/path [component1] [component2] [...]

Dependencies
------------

Python HTML parser, `BeautifulSoup <https://www.crummy.com/software/BeautifulSoup/>`_.

HTTP Requests library, `requests <http://docs.python-requests.org/en/master/>`_.
