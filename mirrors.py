#!/usr/bin/env python

from sys import exit
from socket import (socket, AF_INET, SOCK_STREAM,
                    gethostbyname, setdefaulttimeout)
from time import time
from re import search
try:
    from urllib.request import urlopen, HTTPError, URLError
except ImportError:
    from urllib2 import urlopen, HTTPError, URLError

try:
    from bs4 import BeautifulSoup
except ImportError as err:
    print((
        "%s\n"
        "Try 'sudo apt-get install python-bs4' "
        "or 'sudo apt-get install python3-bs4'" % err
    ))
    exit(1)

class RoundTrip:
    def __init__(self, url):
        self.url = url
        try:
            self.addr = gethostbyname(self.url)
        except IOError as err:
            print("Could not resolve hostname\n%s" % err)
            return

    def __tcpPing(self):
        """Return latency to url's resolved IP address"""
        port = 80
        setdefaulttimeout(2.5)
        s = socket(AF_INET, SOCK_STREAM)
        send_tstamp = time()*1000
        try:
            s.connect((self.addr, port))
        except IOError:
            return

        recv_tstamp = time()*1000
        rtt = recv_tstamp - send_tstamp
        s.close()
        return rtt

    def minRTT(self):
        """Return lowest rtt"""
        rtts = []
        for i in range(3):
            rtt = self.__tcpPing()
            if rtt:
                rtts.append(rtt)
            else:
                rtts = None
                break

        if rtts:
            return round(min(rtts))
        else:
            return

# Possible statuses from mirror launchpad sites
statuses = (
    "unknown",
    "One week behind",
    "Two days behind",
    "One day behind",
    "Up to date"
)

class Data:
    def __init__(self, url, codename, hardware, min_status=None):
        self.url = url
        self.codename = codename
        self.hardware = hardware
        global statuses

        if min_status:
            min_index = statuses.index(min_status)
            statuses = statuses[min_index:]

        self.regex = (
            (
                r'Version\nArchitecture\nStatus\n[\w\s]+'
                'The\s%s\s\w+\n%s\n(.*)\n' % (self.codename, self.hardware)
            ),
            r'Speed:\n([0-9]{1,3}\s\w+)'
        )

    def __reFind(self, regex, string):
        """Find and return regex match"""
        match = search(regex, string)
        try:
            match = match.group(1)
        except AttributeError:
            pass

        return match

    def getInfo(self):
        """Return mirror status and bandwidth"""
        archive = "https://launchpad.net/ubuntu/+mirror/%s-archive" % self.url
        try:
            launch_html = urlopen(archive)
        except HTTPError as err:
            print("\n" + err)
            return
        except URLError as err:
            print(("Unable to connect to %s\n"
                   "Launchpad may be down or refusing connections\n%s" %
                   (archive, err)
            ))
            exit(1)

        launch_html = launch_html.read().decode('utf-8')
        text = BeautifulSoup(launch_html).get_text()
        status = self.__reFind(self.regex[0], text)
        if "unknown" in status:
            status = "unknown"

        if not status or status not in statuses:
            return

        speed = self.__reFind(self.regex[1], text)
        if not speed:
            return
        else:
            return (self.url, (status, speed))

