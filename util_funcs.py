#!/usr/bin/env python

from __future__ import print_function
from sys import exit, stderr
try:
    from urllib.request import urlopen, HTTPError, URLError
except ImportError:
    from urllib2 import urlopen, HTTPError, URLError

def errorExit(err, status):
    print(err, file=stderr)
    exit(status)

def getHTML(url):
    try:
        html = urlopen(url)
    except HTTPError as err:
        print("\n" + err)
        return
    except URLError as err:
        errorExit(
                (
                    "Unable to connect to %s\n"
                    "%s\n" % (url, err)
                ),
                1
        )

    return html.read().decode('utf-8')

