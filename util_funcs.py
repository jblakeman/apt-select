#!/usr/bin/env python
"""Collection of module netural utility functions"""

from sys import stderr
from ssl import SSLError
from socket import timeout
try:
    from urllib.request import urlopen, HTTPError, URLError
except ImportError:
    from urllib2 import urlopen, HTTPError, URLError

class HTMLGetError(Exception):
    """Error class for HTML Gets"""
    pass

def get_html(url):
    """Retrieve and read HTML from URL"""
    try:
        html = urlopen(url)
    except (HTTPError, URLError, SSLError, timeout) as err:
        raise HTMLGetError(err)

    return html.read().decode('utf-8')


def progress_msg(processed, total):
    """Update user on percent done"""
    if total > 1:
        percent = int((float(processed) / total) * 100)
        stderr.write(
            "\r[%d/%d] %d%%" % (processed, total, percent)
        )
        stderr.flush()

