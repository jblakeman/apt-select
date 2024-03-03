#!/usr/bin/env python

from os import path
from subprocess import check_output

from apt_select import constant, utility

SUPPORTED_KERNEL = "Linux"
SUPPORTED_DISTRIBUTION_TYPE = "Ubuntu"

UNAME = "uname"
KERNEL_COMMAND = (UNAME, "-s")
MACHINE_COMMAND = (UNAME, "-m")
RELEASE_COMMAND = ("lsb_release", "-ics")
RELEASE_FILE = "/etc/lsb-release"

LAUNCHPAD_ARCH_32 = "i386"
LAUNCHPAD_ARCH_64 = "amd64"
LAUNCHPAD_ARCHES = frozenset([LAUNCHPAD_ARCH_32, LAUNCHPAD_ARCH_64])


class System:
    """System information for use in apt related operations"""

    def __init__(self) -> None:
        _kernel = utility.utf8_decode(check_output(KERNEL_COMMAND)).strip()
        if _kernel != SUPPORTED_KERNEL:
            raise OSError(
                f"Invalid kernel found: {_kernel}. Expected {SUPPORTED_KERNEL}."
            )

        try:
            self.dist, self.codename = tuple(
                utility.utf8_decode(s).strip()
                for s in check_output(RELEASE_COMMAND).split()
            )
        except OSError:
            # Fall back to using lsb-release info file if lsb_release command
            # is not available. e.g. Ubuntu minimal (core, docker image).
            try:
                with open(
                    RELEASE_FILE, "r", encoding=constant.ENCODING_UTF_8
                ) as release_file:
                    try:
                        lsb_info = dict(
                            line.strip().split("=") for line in release_file.readlines()
                        )
                    except ValueError as err:
                        raise OSError(
                            f"Unexpected release file format found in {RELEASE_FILE}."
                        ) from err

                    try:
                        self.dist = lsb_info["DISTRIB_ID"]
                        self.codename = lsb_info["DISTRIB_CODENAME"]
                    except KeyError as err:
                        raise OSError(
                            f"Expected distribution keys missing from {RELEASE_FILE}."
                        ) from err

            except (IOError, OSError) as err:
                raise OSError(
                    (
                        "Unable to determine system distribution. "
                        f"{SUPPORTED_DISTRIBUTION_TYPE} is required."
                    )
                ) from err

        if self.dist != SUPPORTED_DISTRIBUTION_TYPE:
            raise OSError(
                f"{self.dist} distributions are not supported. {SUPPORTED_DISTRIBUTION_TYPE} is required."
            )

        self.arch = LAUNCHPAD_ARCH_32
        if utility.utf8_decode(check_output(MACHINE_COMMAND).strip()) == "x86_64":
            self.arch = LAUNCHPAD_ARCH_64


class SourcesFileError(Exception):
    """Error class for operations on an apt configuration file

    Operations include:
         - verifying/reading from the current system file
         - generating a new config file"""


class Sources:
    """Class for apt configuration files"""

    DEB_SCHEMES = frozenset(["deb", "deb-src"])
    PROTOCOLS = frozenset(["http", "ftp", "https"])

    DIRECTORY = "/etc/apt/"
    LIST_FILE = "sources.list"
    _CONFIG_PATH = DIRECTORY + LIST_FILE

    def __init__(self, codename: str) -> None:
        self._codename = codename.lower()
        if not path.isfile(self._CONFIG_PATH):
            raise SourcesFileError(f"{self._CONFIG_PATH} must exist as file")

        self._required_component = "main"
        self._lines: str | list[str] = []
        self.urls: dict[str, str] = {}
        self.skip_gen_msg = "Skipping file generation"
        self.new_file_path: str | None = None

    def __set_sources_lines(self) -> None:
        """Read system config file and store the lines in memory for parsing
        and generation of new config file"""
        try:
            with open(self._CONFIG_PATH, "r", encoding=constant.ENCODING_UTF_8) as f:
                self._lines = f.readlines()
        except IOError as err:
            raise SourcesFileError(f"Unable to read system apt file: {err}") from err

    def __confirm_apt_source_uri(self, uris: list[str]) -> bool:
        """Check if line follows correct sources.list URI"""
        if (
            uris
            and (uris[0] in self.DEB_SCHEMES)
            and uris[1].split("://")[0] in self.PROTOCOLS
        ):
            return True

        return False

    def __get_current_archives(self) -> dict[str, str]:
        """Parse through all lines of the system apt file to find current
        mirror urls"""
        urls: dict[str, str] = {}
        for line in self._lines:
            fields = line.split()
            if self.__confirm_apt_source_uri(uris=fields):
                if (
                    not urls
                    and (self._codename in fields[2])
                    and (fields[3] == self._required_component)
                ):
                    urls["current"] = fields[1]
                elif urls and (fields[2] == f"{self._codename}-security"):
                    urls["security"] = fields[1]
                    break

        return urls

    def set_current_archives(self) -> None:
        """Read in the system apt config, parse to find current mirror urls
        to set as attribute"""
        try:
            self.__set_sources_lines()
        except SourcesFileError as err:
            raise SourcesFileError(err) from err

        urls = self.__get_current_archives()
        if not urls:
            raise SourcesFileError(
                f"Error finding current {self._required_component} URI in {self._CONFIG_PATH}\n{self.skip_gen_msg}\n"
            )

        self.urls = urls

    def __set_config_lines(self, new_mirror: str) -> None:
        """Replace all instances of the current urls with the new mirror"""
        self._lines = "".join(self._lines)
        for url in self.urls.values():
            self._lines = self._lines.replace(url, new_mirror)

    def generate_new_config(self, work_dir: str, new_mirror: str) -> None:
        """Write new configuration file to current working directory"""
        self.__set_config_lines(new_mirror=new_mirror)
        self.new_file_path = work_dir.rstrip("/") + "/" + self.LIST_FILE
        try:
            if isinstance(self._lines, str):
                with open(
                    self.new_file_path, "w", encoding=constant.ENCODING_UTF_8
                ) as f:
                    f.write(self._lines)
        except IOError as err:
            raise SourcesFileError(
                f"Unable to generate new sources.list:\n\t{err}\n"
            ) from err
