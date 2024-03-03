#!/usr/bin/env python
"""The mirrors module defines classes and methods for Ubuntu archive mirrors.

Provides latency testing and mirror attribute getting from Launchpad."""

import sys
from queue import Queue, Empty
from socket import socket, AF_INET, SOCK_STREAM, gethostbyname, error, timeout, gaierror
from threading import Thread
from time import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup, FeatureNotFound

from apt_select import utility

PARSER = "lxml"
try:
    BeautifulSoup("", PARSER)
except FeatureNotFound:
    PARSER = "html.parser"


class ConnectError(Exception):
    """Socket connection errors"""


class Mirrors:
    """Base for collection of archive mirrors"""

    def __init__(
        self, url_list: list[str], min_status: int, ping_only: bool | None = None
    ) -> None:
        if ping_only is None:
            ping_only = False
        self.urls: dict[str, dict[str, float | int | str]] = {}
        self._url_list = url_list
        self._num_trips = 0
        self.got = {"ping": 0, "data": 0}
        self.ranked: list[str] = []
        self.top_list: list[str] = []
        self._trip_queue: Queue[tuple[str, float] | None] = Queue()
        if not ping_only:
            self._launchpad_base = "https://launchpad.net"
            self._launchpad_url = self._launchpad_base + "/ubuntu/+archivemirrors"
            self._launchpad_html = ""
            self.abort_launch = False
            self._status_opts: tuple[str, ...] = (
                "unknown",
                "One week behind",
                "Two days behind",
                "One day behind",
                "Up to date",
            )
            index = self._status_opts.index(min_status)
            self._status_opts = self._status_opts[index:]
            # Default to top
            self.status_num = 1

    def fetch_launchpad_urls(self) -> None:
        """Obtain mirrors' corresponding launchpad URLs"""
        sys.stderr.write("Getting list of launchpad URLs...")
        try:
            self._launchpad_html = utility.get_text(self._launchpad_url)
        except utility.URLGetTextError as err:
            sys.stderr.write(
                (
                    f"{self._launchpad_url}: {err}\nUnable to retrieve list of launchpad sites\n"
                    "Reverting to latency only\n"
                )
            )
            self.abort_launch = True
        else:
            sys.stderr.write("done.\n")
            self.__parse_launchpad_list()

    def __parse_launchpad_list(self) -> None:
        """Parse Launchpad's list page to find each mirror's
        Official page"""
        soup = BeautifulSoup(self._launchpad_html, PARSER)
        prev = ""
        if soup.table is not None:
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
                            self.urls[url][
                                "Launchpad"
                            ] = f"{self._launchpad_base}{prev}"

                        if url.startswith("/ubuntu/+mirror/"):
                            prev = url

    def __kickoff_trips(self) -> None:
        """Instantiate round trips class for all, initiating queued threads"""

        for url in self._url_list:
            host = urlparse(url).netloc
            try:
                round_trip = _RoundTrip(url=url, host=host, trip_queue=self._trip_queue)
                thread = Thread(target=round_trip.min_rtt)
            except gaierror as err:
                sys.stderr.write(f"{err}: {url} ignored\n")
            else:
                self.urls[url] = {"Host": host}
                thread.daemon = True
                thread.start()
                self._num_trips += 1

    def measure_rtts(self) -> None:
        """Test latency to all mirrors"""

        sys.stderr.write("Testing latency to mirror(s)\n")
        self.__kickoff_trips()

        processed = 0
        utility.progress_msg(processed=processed, total=self._num_trips)
        for _ in range(self._num_trips):
            try:
                min_rtt: tuple[str, float] | None = self._trip_queue.get(block=True)
            except Empty:
                pass
            else:
                # we can ignore empty rtt results (None) from the queue
                # as in this case ConnectError was already raised
                if min_rtt:
                    self._trip_queue.task_done()
                    self.urls[min_rtt[0]].update({"Latency": min_rtt[1]})
                    self.got["ping"] += 1

            processed += 1
            utility.progress_msg(processed=processed, total=self._num_trips)

        sys.stderr.write("\n")
        # Mirrors without latency info are removed
        self.urls = {key: val for key, val in self.urls.items() if "Latency" in val}

        self.ranked = sorted(self.urls, key=lambda x: self.urls[x]["Latency"])

    def __queue_lookups(
        self,
        codename: str,
        arch: str,
        data_queue: Queue[tuple[str, dict[str, str] | None]],
    ) -> int:
        """Queue threads for data retrieval from launchpad.net

        Returns number of threads started to fulfill number of
        requested statuses"""
        num_threads = 0
        for url in self.ranked:
            launch_url: float | str | None = None
            try:
                launch_url = self.urls[url]["Launchpad"]
            except KeyError:
                pass
            else:
                if launch_url is not None and isinstance(launch_url, str):
                    thread = Thread(
                        target=_LaunchData(
                            url=url,
                            launch_url=launch_url,
                            codename=codename,
                            arch=arch,
                            data_queue=data_queue,
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

    def lookup_statuses(self, codename: str, arch: str) -> None:
        """Scrape statuses/info in from launchpad.net mirror pages"""
        while (self.got["data"] < self.status_num) and self.ranked:
            data_queue: Queue[tuple[str, dict[str, str] | None]] = Queue()
            num_threads = self.__queue_lookups(
                codename=codename, arch=arch, data_queue=data_queue
            )
            if num_threads == 0:
                break
            # Get output of all started thread methods from queue
            utility.progress_msg(processed=self.got["data"], total=self.status_num)
            for _ in range(num_threads):
                try:
                    # We don't care about timeouts longer than 7 seconds as
                    # we're only getting 16 KB
                    info = data_queue.get(block=True, timeout=7)
                except Empty:
                    pass
                else:
                    data_queue.task_done()
                    if info[1] and info[1]["Status"] in self._status_opts:
                        self.urls[info[0]].update(info[1])
                        self.got["data"] += 1
                        self.top_list.append(info[0])
                        utility.progress_msg(self.got["data"], self.status_num)

                    # Eliminate the url from the ranked list as long as
                    # something is received from the queue (for selective
                    # iteration if another queue needs to be built)
                    self.ranked.remove(info[0])

                if self.got["data"] == self.status_num:
                    break

            # Reorder by latency as queue returns vary building final list
            self.top_list.sort(key=lambda x: self.urls[x]["Latency"])

            data_queue.join()


class _RoundTrip:
    """Socket connections for latency reporting"""

    def __init__(
        self, url: str, host: str, trip_queue: Queue[tuple[str, float] | None]
    ) -> None:
        self._url = url
        self._host = host
        self._trip_queue: Queue[tuple[str, float] | None] = trip_queue
        self._addr = gethostbyname(host)

    def __tcp_ping(self) -> float:
        """Return socket latency to host's resolved IP address"""
        port = 80
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(2.5)
        send_tstamp = time() * 1000
        try:
            sock.connect((self._addr, port))
        except (timeout, error) as err:
            raise ConnectError(err) from err

        recv_tstamp = time() * 1000
        rtt = recv_tstamp - send_tstamp
        sock.close()
        return rtt

    def min_rtt(self) -> None:
        """Return lowest rtt"""
        rtts = []
        for _ in range(3):
            try:
                rtt = self.__tcp_ping()
            except ConnectError as err:
                sys.stderr.write(f"\tconnection to {self._host}: {err}\n")
                self._trip_queue.put_nowait(None)
                return
            rtts.append(rtt)

        self._trip_queue.put((self._url, min(rtts)))


class _LaunchData:
    def __init__(
        self,
        url: str,
        launch_url: str,
        codename: str,
        arch: str,
        data_queue: Queue[tuple[str, dict[str, str] | None]],
    ) -> None:
        self._url = url
        self._launch_url = launch_url
        self._codename = codename
        self._arch = arch
        self._data_queue = data_queue

    def __parse_mirror_html(self, launch_html: str) -> dict[str, str]:
        info: dict[str, str] = {}
        soup = BeautifulSoup(launch_html, PARSER)
        # Find elements of the ids we need
        for line in soup.find_all(id=["arches", "speed", "organisation"]):
            if line.name == "table":
                # Status information lives in a table column alongside
                # series name and machine architecture
                for tr in line.find("tbody").find_all("tr"):
                    arches = [x.get_text() for x in tr.find_all("td")]
                    if self._codename in arches[0] and arches[1] == self._arch:
                        info.update({"Status": arches[2]})
            else:
                # "Speed" lives in a dl, and we use the key -> value as such
                info.update({line.dt.get_text().strip(":"): line.dd.get_text()})

        return info

    def get_info(self) -> None:
        """Parse launchpad page HTML for mirror information

        Ideally, launchpadlib would be used to get mirror information, but the
        Launchpad API doesn't support access to archivemirror statuses."""

        try:
            launch_html = utility.get_text(self._launch_url)
        except utility.URLGetTextError as err:
            sys.stderr.write(f"connection to {self._launch_url}: {err}\n")
            self._data_queue.put_nowait((self._url, None))
        else:
            info = self.__parse_mirror_html(launch_html=launch_html)
            if "Status" not in info:
                sys.stderr.write(
                    f"Unable to parse status info from {self._launch_url}\n"
                )
                self._data_queue.put_nowait((self._url, None))
                return

            # Launchpad has more descriptive "unknown" status.
            # It's trimmed here to match statuses list
            if "unknown" in info["Status"]:
                info["Status"] = "unknown"

            self._data_queue.put((self._url, info))
