#!/usr/bin/env python

from sys import exit, stderr
try:
    from urllib.request import urlopen, HTTPError, URLError
except ImportError:
    from urllib2 import urlopen, HTTPError, URLError


def getHTML(url):
    try:
        html = urlopen(url)
    except HTTPError as err:
        stderr.write("\n%s\n" % err)
        return None
    except URLError as err:
        exit((
            "Unable to connect to %s\n"
            "%s\n" % (url, err)
        ))

    return html.read().decode('utf-8')
