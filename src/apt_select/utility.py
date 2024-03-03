#!/usr/bin/env python
"""Collection of module neutral utility functions"""

import sys

import requests
from apt_select import constant


def utf8_decode(encoded: bytes) -> str:
    return encoded.decode(constant.ENCODING_UTF_8)


class URLGetTextError(Exception):
    """Error class for fetching text from a URL"""


def get_text(
    url: str, timeout_sec: float = constant.DEFAULT_REQUEST_TIMEOUT_SEC
) -> str:
    """Return text from GET request response content"""
    try:
        result = requests.get(
            url, headers=constant.DEFAULT_REQUEST_HEADERS, timeout=timeout_sec
        )
        result.raise_for_status()
    except requests.HTTPError as err:
        raise URLGetTextError(err) from err

    return result.text


def progress_msg(processed: float | int, total: float | int) -> None:
    """Update user on percent done"""
    if total > 1:
        percent = int((float(processed) / total) * 100)
        sys.stderr.write(f"\r[{processed}/{total}] {percent}%")
        sys.stderr.flush()
