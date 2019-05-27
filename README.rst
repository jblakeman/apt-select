apt-select
==========

Find a fast, up-to-date Ubuntu Archive Mirror.

Features
--------

* Tests latency to mirrors in a given country's mirror list at `mirrors.ubuntu.com <http://mirrors.ubuntu.com>`_.
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
    usage: apt-select [-h] [-C [COUNTRY]] [-t [NUMBER]] [-m [STATUS] | -p]
                      [-c | -l]

    Find the fastest Ubuntu apt mirrors.
    Generate new sources.list file.

    optional arguments:
      -h, --help            show this help message and exit
      -C [COUNTRY], --country [COUNTRY]
                            specify a country to test its list of mirrors
                            used to match country list file names found at mirrors.ubuntu.com
                            COUNTRY should follow ISO 3166-1 alpha-2 format
                            default: US
      -t [NUMBER], --top-number [NUMBER]
                            specify number of mirrors to return
                            default: 1
      -m [STATUS], --min-status [STATUS]
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

    The exit code is 0 on success, 1 on error, and 4 if sources.list already has the chosen
    mirror and a new one was not generated.

Examples
--------

Get the top mirror from the United Kingdom to generate a new `sources.list`:::

    apt-select --country GB

Choose from the top 3 mirrors, including those last updated a week ago:::

    apt-select -c -t 3 -m one-week-behind

Find the top 10 mirrors, output latency info only, and don't generate new `sources.list`:::

    apt-select -t 10 -p -l

After new sources.list is generated in current working directory, backup and replace to update apt:::

    sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup && \
    sudo mv sources.list /etc/apt/

Supported URI Types
-------------------

Currently, `http`, `https` and `ftp` are supported.

`/etc/apt/sources.list` should contain sources in the following format:::

    [deb|deb-src] [http|https|ftp]://mirror.example.com/path [component1] [component2] [...]

Dependencies
------------

Python HTML parser, `BeautifulSoup <https://www.crummy.com/software/BeautifulSoup/>`_.

HTTP Requests library, `requests <http://docs.python-requests.org/en/master/>`_.
