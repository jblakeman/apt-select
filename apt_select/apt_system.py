#!/usr/bin/env python

from subprocess import check_output
from os import path
from apt_select.utils import utf8_decode

LAUNCHPAD_ARCH_32 = 'i386'
LAUNCHPAD_ARCH_64 = 'amd64'
LAUNCHPAD_ARCHES = frozenset([
    LAUNCHPAD_ARCH_32,
    LAUNCHPAD_ARCH_64
])

class AptSystem(object):
    """System information for use in apt related operations"""

    @staticmethod
    def get_release():
        """Call system for Ubuntu release information"""
        return [utf8_decode(s).strip()
                for s in check_output(["lsb_release", "-ics"]).split()]

    @staticmethod
    def get_arch():
        """Return architecture information in Launchpad format"""
        if utf8_decode(check_output(["uname", "-m"]).strip()) == 'x86_64':
            return LAUNCHPAD_ARCH_64

        return LAUNCHPAD_ARCH_32

    _not_ubuntu = "Must be an Ubuntu OS"
    try:
        dist, codename = get_release.__func__()
    except OSError:
        raise ValueError("%s\n%s" % _not_ubuntu)
    else:
        codename = codename.capitalize()

    if dist != 'Ubuntu':
        raise ValueError(_not_ubuntu)

    arch = get_arch.__func__()


class SourcesFileError(Exception):
    """Error class for operations on an apt configuration file

       Operations include:
            - verifying/reading from the current system file
            - generating a new config file"""
    pass


class AptSources(AptSystem):
    """Class for apt configuration files"""

    DEB_SCHEMES = frozenset(['deb', 'deb-src'])
    PROTOCOLS = frozenset(['http', 'ftp'])

    def __init__(self):
        self.directory = '/etc/apt/'
        self.apt_file = 'sources.list'
        self._config_path = self.directory + self.apt_file
        if not path.isfile(self._config_path):
            raise SourcesFileError((
                "%s must exist as file" % self._config_path
            ))

        self._required_component = "main"
        self._lines = []
        self.urls = []
        self.skip_gen_msg = "Skipping file generation"
        self.new_file_path = None

    def __set_sources_lines(self):
        """Read system config file and store the lines in memory for parsing
           and generation of new config file"""
        try:
            with open(self._config_path, 'r') as f:
                self._lines = f.readlines()
        except IOError as err:
            raise SourcesFileError((
                "Unable to read system apt file: %s" % err
            ))

    def __confirm_apt_source_uri(self, uri):
        """Check if line follows correct sources.list URI"""
        if (uri and (uri[0] in self.DEB_SCHEMES) and
                uri[1].split('://')[0] in self.PROTOCOLS):
            return True

        return False

    def __get_current_archives(self):
        """Parse through all lines of the system apt file to find current
           mirror urls"""
        urls = []
        cname = self.codename.lower()
        for line in self._lines:
            fields = line.split()
            if self.__confirm_apt_source_uri(fields):
                if (not urls and
                        (cname in fields[2]) and
                        (fields[3] == self._required_component)):
                    urls.append(fields[1])
                    continue
                elif (urls and
                        (fields[2] == '%s-security' % cname) and
                        # Mirror urls should be unique as they'll be
                        # used in a global search and replace
                        (urls[0] != fields[1])):
                    urls.append(fields[1])
                    break

        return urls

    def set_current_archives(self):
        """Read in the system apt config, parse to find current mirror urls
           to set as attribute"""
        try:
            self.__set_sources_lines()
        except SourcesFileError as err:
            raise SourcesFileError(err)

        urls = self.__get_current_archives()
        if not urls:
            raise SourcesFileError((
                "Error finding current %s URI in %s\n%s\n" %
                (self._required_component, self._config_path,
                 self.skip_gen_msg)
            ))

        self.urls = urls

    def __set_config_lines(self, new_mirror):
        """Replace all instances of the current urls with the new mirror"""
        self._lines = ''.join(self._lines)
        for url in self.urls:
            self._lines = self._lines.replace(url, new_mirror)

    def generate_new_config(self, work_dir, new_mirror):
        """Write new configuration file to current working directory"""
        self.__set_config_lines(new_mirror)
        self.new_file_path = work_dir.rstrip('/') + '/' + self.apt_file
        try:
            with open(self.new_file_path, 'w') as f:
                f.write(self._lines)
        except IOError as err:
            raise SourcesFileError((
                "Unable to generate new sources.list:\n\t%s\n" % err
            ))
