#!/usr/bin/env python
"""Collection of module netural utility functions"""

from sys import exit, stderr
try:
    from urllib.request import urlopen, HTTPError, URLError
except ImportError:
    from urllib2 import urlopen, HTTPError, URLError


def get_html(url):
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


def progress_msg(processed, total):
    """Update user on percent done"""
    if total > 1:
        percent = int((float(processed) / total) * 100)
        stderr.write(
            "\r[%d/%d] %d%%" % (processed, total, percent)
        )
        stderr.flush()

