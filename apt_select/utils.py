#!/usr/bin/env python
"""Collection of module neutral utility functions"""

from sys import stderr

import requests

DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'apt-select'
}


def utf8_decode(encoded):
    return encoded.decode('utf-8')


class URLGetTextError(Exception):
    """Error class for fetching text from a URL"""
    pass


def get_text(url):
    """Return text from GET request response content"""
    try:
        result = requests.get(url, headers=DEFAULT_REQUEST_HEADERS)
        result.raise_for_status()
    except requests.HTTPError as err:
        raise URLGetTextError(err)

    return result.text


def progress_msg(processed, total):
    """Update user on percent done"""
    if total > 1:
        percent = int((float(processed) / total) * 100)
        stderr.write("\r[%d/%d] %d%%" % (processed, total, percent))
        stderr.flush()
