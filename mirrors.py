#!/usr/bin/env python
"""The mirrors module defines classes and methods for Ubuntu archive mirrors.

   Provides latency testing and mirror attribute getting from Launchpad."""

from sys import stderr
from socket import (socket, AF_INET, SOCK_STREAM,
                    gethostbyname, setdefaulttimeout,
                    error, timeout, gaierror)
from time import time
from util_funcs import get_html, HTMLGetError, progress_msg
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from threading import Thread

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

try:
    from bs4 import BeautifulSoup, FeatureNotFound
except ImportError as err:
    exit((
        "%s\n"
        "Try 'sudo apt-get install python-bs4' "
        "or 'pip install beautifulsoup4'" % err
    ))
else:
    PARSER = "lxml"
    try:
        BeautifulSoup("", PARSER)
    except FeatureNotFound:
        PARSER = "html.PARSER"


class ConnectError(Exception):
    """Socket connection errors"""
    pass


class Mirrors(object):
    """Base for collection of archive mirrors"""

    def __init__(self, url_list, flag_ping, flag_status):
        self.ranked = []
        self.urls = {}
        self.url_list = url_list
        self.num_trips = 0
        self.got = {"ping": 0, "data": 0}
        self.ranked = []
        self.top_list = []
        self.trip_queue = Queue()
        if not flag_ping:
            self.abort_launch = False
            self.status_opts = (
                "unknown",
                "One week behind",
                "Two days behind",
                "One day behind",
                "Up to date"
            )
            index = self.status_opts.index(flag_status)
            self.status_opts = self.status_opts[index:]
            # Default to top
            self.status_num = 1

    def get_launchpad_urls(self):
        """Obtain mirrors' corresponding launchpad URLs"""
        launchpad_base = "https://launchpad.net"
        launchpad_url = launchpad_base + "/ubuntu/+archivemirrors"
        stderr.write("Getting list of launchpad URLs...")
        try:
            launchpad_html = get_html(launchpad_url)
        except HTMLGetError as err:
            stderr.write((
                "%s: %s\nUnable to retrieve list of launchpad sites\n"
                "Reverting to latency only" % (launchpad_url, err)
            ))
            self.abort_launch = True
        else:
            stderr.write("done.\n")
            soup = BeautifulSoup(launchpad_html, PARSER)
            prev = ""
            for element in soup.table.descendants:
                try:
                    url = element.a
                except AttributeError:
                    pass
                else:
                    try:
                        url = url["href"]
                    except TypeError:
                        pass
                    else:
                        if url in self.urls:
                            self.urls[url]["Launchpad"] = launchpad_base + prev

                        if url.startswith("/ubuntu/+mirror/"):
                            prev = url

    def __kickoff_trips(self):
        """Instantiate round trips class for all, initiating queued threads"""

        for url in self.url_list:
            host = urlparse(url).netloc
            try:
                thread = Thread(
                    target=_RoundTrip(url, host, self.trip_queue).min_rtt
                )
            except gaierror as err:
                stderr.write("%s: %s ignored\n" % (err, url))
            else:
                self.urls[url] = {"Host": host}
                thread.daemon = True
                thread.start()
                self.num_trips += 1

    def get_rtts(self):
        """Test latency to all mirrors"""

        self.__kickoff_trips()

        processed = 0
        stderr.write("Testing %d mirror(s)\n" % self.num_trips)
        progress_msg(processed, self.num_trips)
        for _ in range(self.num_trips):
            try:
                min_rtt = self.trip_queue.get(block=True)
            except Empty:
                pass
            else:
                # we can ignore empty rtt results (None) from the queue
                # as in this case ConnectError was already raised
                if min_rtt:
                    self.trip_queue.task_done()
                    self.urls[min_rtt[0]].update({"Latency": min_rtt[1]})
                    self.got["ping"] += 1

            processed += 1
            progress_msg(processed, self.num_trips)

        stderr.write('\n')
        # Mirrors without latency info are removed
        self.urls = {
            key: val for key, val in self.urls.items() if "Latency" in val
        }

        self.ranked = sorted(
            self.urls, key=lambda x: self.urls[x]["Latency"]
        )

    def __queue_lookups(self, codename, hardware, data_queue):
        """Queue threads for data retrieval from launchpad.net

           Returns number of threads started to fulfill number of
           requested statuses"""
        num_threads = 0
        for url in (x for x in self.ranked
                    if "Status" not in self.urls[x]):
            try:
                launch_url = self.urls[url]["Launchpad"]
            except KeyError:
                pass
            else:
                thread = Thread(
                    target=_LaunchData(
                        url, launch_url, codename, hardware, data_queue
                    ).get_info
                )
                thread.daemon = True
                thread.start()

                num_threads += 1
            # We expect number of retrieved status requests may already
            # be greater than 0.  This would be the case anytime an initial
            # pass ran into errors.
            if num_threads == (self.status_num - self.got["data"]):
                break

        return num_threads

    def lookup_statuses(self, min_status, codename, hardware):
        """Scrape statuses/info in from launchpad.net mirror pages"""
        while (self.got["data"] < self.status_num) and self.ranked:
            data_queue = Queue()
            num_threads = self.__queue_lookups(codename, hardware, data_queue)
            if num_threads == 0:
                break
            # Get output of all started thread methods from queue
            progress_msg(self.got["data"], self.status_num)
            for _ in range(num_threads):
                try:
                    # We don't care about timeouts longer than 7 seconds as
                    # we're only getting 16 KB
                    info = data_queue.get(block=True, timeout=7)
                except Empty:
                    pass
                else:
                    data_queue.task_done()
                    if (info[0] and info[1] and
                            info[1]["Status"] in self.status_opts):
                        self.urls[info[0]].update(info[1])
                        self.got["data"] += 1
                        self.top_list.append(info[0])
                    else:
                        # Remove unqualified results from ranked list so
                        # queueing can use it to populate the right threads
                        self.ranked.remove(info[0])

                progress_msg(self.got["data"], self.status_num)
                if (self.got["data"] == self.status_num):
                    break

            data_queue.join()


class _RoundTrip(object):
    """Socket connections for latency reporting"""

    def __init__(self, url, host, trip_queue):
        self.url = url
        self.host = host
        self.trip_queue = trip_queue
        try:
            self.addr = gethostbyname(host)
        except gaierror as err:
            raise gaierror(err)

    def __tcp_ping(self):
        """Return socket latency to host's resolved IP address"""
        port = 80
        setdefaulttimeout(2.5)
        sock = socket(AF_INET, SOCK_STREAM)
        send_tstamp = time()*1000
        try:
            sock.connect((self.addr, port))
        except (timeout, error) as err:
            raise ConnectError(err)

        recv_tstamp = time()*1000
        rtt = recv_tstamp - send_tstamp
        sock.close()
        return rtt

    def min_rtt(self):
        """Return lowest rtt"""
        rtts = []
        for _ in range(3):
            try:
                rtt = self.__tcp_ping()
            except ConnectError as err:
                stderr.write("\n\tconnection to %s: %s\n" % (self.host, err))
                self.trip_queue.put_nowait(None)
                return
            else:
                rtts.append(rtt)

        self.trip_queue.put((self.url, round(min(rtts))))


class _LaunchData(object):
    def __init__(self, url, launch_url, codename, hardware, data_queue):
        self.url = url
        self.launch_url = launch_url
        self.codename = codename
        self.hardware = hardware
        self.data_queue = data_queue

    def __parse_mirror_html(self, launch_html):
        info = {}
        soup = BeautifulSoup(launch_html, PARSER)
        # Find elements of the ids we need
        for line in soup.find_all(id=['arches', 'speed', 'organisation']):
            if line.name == 'table':
                # Status information lives in a table column alongside
                # series name and machine architecture
                for tr in line.find('tbody').find_all('tr'):
                    arches = [x.get_text() for x in tr.find_all('td')]
                    if (self.codename in arches[0] and
                            arches[1] == self.hardware):
                        info.update({"Status": arches[2]})
            else:
                # "Speed" lives in a dl, and we use the key -> value as such
                info.update({
                    line.dt.get_text().strip(':'): line.dd.get_text()
                })

        return info

    def get_info(self):
        """Parse launchpad page HTML for mirror information

        Ideally, launchpadlib would be used to get mirror information, but the
        Launchpad API doesn't support access to archivemirror statuses."""

        try:
            launch_html = get_html(self.launch_url)
        except HTMLGetError as err:
            stderr.write("connection to %s: %s" % (self.launch_url, err))
            self.data_queue.put_nowait(None)
        else:
            info = self.__parse_mirror_html(launch_html)
            if "Status" not in info:
                stderr.write((
                    "Unable to parse status info from %s" % self.launch_url
                ))
                self.data_queue.put_nowait(None)
                return

            # Launchpad has more descriptive "unknown" status.
            # It's trimmed here to match statuses list
            if "unknown" in info["Status"]:
                info["Status"] = "unknown"

            self.data_queue.put((self.url, info))
