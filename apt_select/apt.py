#!/usr/bin/env python

from subprocess import check_output
from os import path
from apt_select.utils import utf8_decode

SUPPORTED_KERNEL = 'Linux'
SUPPORTED_DISTRIBUTION_TYPE = 'Ubuntu'

UNAME = 'uname'
KERNEL_COMMAND = (UNAME, '-s')
MACHINE_COMMAND = (UNAME, '-m')
RELEASE_COMMAND = ('lsb_release', '-ics')
RELEASE_FILE = '/etc/lsb-release'

LAUNCHPAD_ARCH_32 = 'i386'
LAUNCHPAD_ARCH_64 = 'amd64'
LAUNCHPAD_ARCHES = frozenset([
    LAUNCHPAD_ARCH_32,
    LAUNCHPAD_ARCH_64
])


class System(object):
    """System information for use in apt related operations"""

    def __init__(self):
        _kernel = utf8_decode(check_output(KERNEL_COMMAND)).strip()
        if _kernel != SUPPORTED_KERNEL:
            raise OSError(
                "Invalid kernel found: %s. Expected %s." % (
                    _kernel,
                    SUPPORTED_KERNEL,
                )
            )

        try:
            self.dist, self.codename = tuple(
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
                        self.dist = lsb_info['DISTRIB_ID']
                        self.codename = lsb_info['DISTRIB_CODENAME']
                    except KeyError:
                        raise OSError(
                            "Expected distribution keys missing from %s." % RELEASE_FILE
                        )

            except (IOError, OSError):
                raise OSError((
                    "Unable to determine system distribution. "
                    "%s is required." % SUPPORTED_DISTRIBUTION_TYPE
                ))

        if self.dist != SUPPORTED_DISTRIBUTION_TYPE:
            raise OSError(
                "%s distributions are not supported. %s is required." % (
                    self.dist, SUPPORTED_DISTRIBUTION_TYPE
                )
            )

        self.arch = LAUNCHPAD_ARCH_32
        if utf8_decode(check_output(MACHINE_COMMAND).strip()) == 'x86_64':
            self.arch = LAUNCHPAD_ARCH_64


class SourcesFileError(Exception):
    """Error class for operations on an apt configuration file

       Operations include:
            - verifying/reading from the current system file
            - generating a new config file"""
    pass


class Sources(object):
    """Class for apt configuration files"""

    DEB_SCHEMES = frozenset(['deb', 'deb-src'])
    PROTOCOLS = frozenset(['http', 'ftp', 'https'])

    DIRECTORY = '/etc/apt/'
    LIST_FILE = 'sources.list'
    _CONFIG_PATH = DIRECTORY + LIST_FILE

    def __init__(self, codename):
        self._codename = codename.lower()
        if not path.isfile(self._CONFIG_PATH):
            raise SourcesFileError((
                "%s must exist as file" % self._CONFIG_PATH
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
            with open(self._CONFIG_PATH, 'r') as f:
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
        urls = {}
        for line in self._lines:
            fields = line.split()
            if self.__confirm_apt_source_uri(fields):
                if (not urls and
                        (self._codename in fields[2]) and
                        (fields[3] == self._required_component)):
                    urls['current'] = fields[1]
                elif urls and (fields[2] == '%s-security' % self._codename):
                    urls['security'] = fields[1]
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
                (self._required_component, self._CONFIG_PATH,
                 self.skip_gen_msg)
            ))

        self.urls = urls

    def __set_config_lines(self, new_mirror):
        """Replace all instances of the current urls with the new mirror"""
        self._lines = ''.join(self._lines)
        for url in self.urls.values():
            self._lines = self._lines.replace(url, new_mirror)

    def generate_new_config(self, work_dir, new_mirror):
        """Write new configuration file to current working directory"""
        self.__set_config_lines(new_mirror)
        self.new_file_path = work_dir.rstrip('/') + '/' + self.LIST_FILE
        try:
            with open(self.new_file_path, 'w') as f:
                f.write(self._lines)
        except IOError as err:
            raise SourcesFileError((
                "Unable to generate new sources.list:\n\t%s\n" % err
            ))
