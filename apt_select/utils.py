#!/usr/bin/env python
"""Collection of module neutral utility functions"""
from subprocess import check_output
from sys import stderr
from typing import Tuple

import requests

from apt_select.config import *

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


def get_distribution_info() -> Tuple[str, str]:
    dist, codename = "", ""
    try:
        dist, codename = tuple(
            utf8_decode(s).strip()
            for s in check_output(RELEASE_COMMAND).split()
        )
    except OSError:
        # Fall back to using lsb-release info file if lsb_release command
        # is not available. e.g. Ubuntu minimal (core, docker image).
        try:
            with open(RELEASE_FILE, 'rU') as release_file:
                try:
                    lsb_info = dict(
                        line.strip().split('=')
                        for line in release_file.readlines()
                    )
                except ValueError:
                    raise OSError(
                        "Unexpected release file format found in %s." % RELEASE_FILE
                    )

                try:
                    dist = lsb_info['DISTRIB_ID']
                    codename = lsb_info['DISTRIB_CODENAME']
                except KeyError:
                    raise OSError(
                        "Expected distribution keys missing from %s." % RELEASE_FILE
                    )

        except (IOError, OSError):
            raise OSError((
                    "Unable to determine system distribution. "
                    "%s is required." % SUPPORTED_DISTRIBUTION_TYPE
            ))
    return dist, codename
