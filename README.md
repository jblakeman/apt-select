apt-select
========

Speeds up updates and upgrades by selecting a mirror with the lowest latency.

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

Update `apt`
---------------
After the new `sources.list` file is generated, the current file should be copied to another location before being replaced:

    sudo mv /etc/apt/sources.list /etc/apt/sources.list.backup && sudo mv sources.list /etc/apt/sources.list

Note
------
Although the script does its best to not replace any third party `apt` repositories that may have been manually added, there's a chance it could happen if the third white space delimited field has the release's codename (ie: trusty) in it.  This will most likely not be the case, but it still might be a good idea to double check the new file.
