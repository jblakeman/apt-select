#!/usr/bin/env python

import sys, socket
import time
import re
try:
    from urllib.request import urlopen, HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

try:
    from bs4 import BeautifulSoup
except ImportError as err:
    print(("%s\n"
           "Try 'sudo apt-get install python-bs4' "
           "or 'sudo apt-get install python3-bs4'" % err))
    sys.exit(1)

class RoundTrip:
	def __init__(self, url):
		self.url = url

	def __tcpPing(self):
		"""Return latency to hostname"""
		port = 80
		socket.setdefaulttimeout(2.5)
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			addr = socket.gethostbyname(self.url)
		except IOError as err:
			print("Could not resolve hostname\n%s" % err)
			return False

		send_tstamp = time.time()*1000
		try:
			s.connect((addr, port))
		except IOError as err:
			print(err)
			return False

		recv_tstamp = time.time()*1000
		rtt = recv_tstamp - send_tstamp
		s.close()
		return rtt

	def avgRTT(self):
		"""Return average ping (rtt) of 3 if all true"""
		rtt = []
		for i in range(3):
			x = self.__tcpPing()
			if x is not False:
				rtt += [x]
			else:
				rtt = []
				break

		if rtt:
			avg = round(sum(rtt) / len(rtt))
			return avg
		else:
			return False

class Data:
	def __init__(self, url, codename, hardware):
		self.url = url
		self.codename = codename
		self.hardware = hardware

	def __reFind(self, regex, string):
		"""Find and return regex match"""
		try:
			match = re.search(regex, string).group(1)
		except AttributeError:
			# Group None types with unwanted status 'Last update unknown'
			match = 'unknown'

		return match

	def getInfo(self):
		"""Return valid mirror status and bandwidth"""
		regex1 = (r'Version\nArchitecture\nStatus\n[\w|\s]'
				   '+The\s%s\s\w+\n%s\n(.*)\n' % (self.codename, self.hardware))
		regex2 = r'Speed:\n([0-9]{1,3}\s\w+)'
		archive = "https://launchpad.net/ubuntu/+mirror/%s-archive" % self.url
		try:
			launch_html = urlopen(archive)
		except HTTPError:
			try:
				launch_html = urlopen(archive.replace('-archive', ''))
			except HTTPError:
				print(("%s is one of the top mirrors, but "
					   "has a unique launchpad url.\n"
					   "Cannot verify, so removed from list" % self.url))
				return False

		launch_html = launch_html.read().decode()
		text = BeautifulSoup(launch_html).get_text()
		status = self.__reFind(regex1, text)
		if 'unknown' in status:
			return False

		speed = self.__reFind(regex2, text)
		if not status or not speed:
			return False
		else:
			return [self.url, [status, speed]]

