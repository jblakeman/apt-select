#!/usr/bin/env python

from sys import exit, stderr, version_info
from os import getcwd, path
from subprocess import check_output
from arguments import get_args
from utils import get_html, URLGetError
from mirrors import Mirrors


class AptSystem(object):
    """System information for use in apt related operations"""

    def __init__(self):
        not_ubuntu = "Must be an Ubuntu OS"
        try:
            self._release = self.__get_release()
        except OSError as err:
            # We return both errors from the stack as lsb_release may
            # not be present for some strange reason
            raise ValueError("%s\n%s" % (not_ubuntu, err))

        if self._release["dist"] == 'Debian':
            raise ValueError("Debian is not currently supported")
        elif self._release["dist"] != 'Ubuntu':
            raise ValueError(not_ubuntu)

        self.codename = self._release["codename"].capitalize()
        self.arch = self.__get_arch()
        if self.arch not in ('i386', 'amd64'):
            raise ValueError((
                "%s: must have system architecture in valid Launchpad"
                "format" % self.arch.__name__
            ))

    def __get_release(self):
        """Call system for Ubuntu release information"""
        try:
            release = check_output(["lsb_release", "-ics"])
        except OSError as err:
            raise OSError(err)

        release = [s.strip() for s in release.decode('utf-8').split()]
        return {"dist": release[0], "codename": release[1]}

    def __get_arch(self):
        """Return architecture information in Launchpad format"""
        arch = check_output(["uname", "-m"]).strip().decode('utf-8')
        if arch == 'x86_64':
            return 'amd64'
        return 'i386'


class SourcesFileError(Exception):
    """Error class for operations on an apt configuration file

       Operations include:
            - verifying/reading from the current system file
            - generating a new config file"""
    pass


class AptSources(AptSystem):
    """Class for apt configuration files"""

    def __init__(self):
        super(AptSources, self).__init__()
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

    def __confirm_mirror(self, uri, deb, protos):
        """Check if line follows correct sources.list URI"""
        if (uri and (uri[0] in deb) and
                (protos[0] in uri[1] or
                 protos[1] in uri[1])):
            return True

        return False

    def __get_current_archives(self):
        """Parse through all lines of the system apt file to find mirror urls
           to replace"""
        deb = set(('deb', 'deb-src'))
        protos = ('http://', 'ftp://')
        urls = []
        cname = self._release["codename"]
        for line in self._lines:
            fields = line.split()
            if self.__confirm_mirror(fields, deb, protos):
                # Start by finding the required component ("main")
                if (not urls and
                        # The release name (e.g. xenial) and component
                        # are the third, and fourth fields (as
                        # described in sources.list man page examples)
                        (cname in fields[2]) and
                        (fields[3] == self._required_component)):
                    urls.append(fields[1])
                    continue
                elif (urls and
                        # The release prefixes the security component
                        (fields[2] == '%s-security' % cname) and
                        # Mirror urls must be unique as they'll be
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


def set_args():
    """Set arguments, disallow bad combination"""
    parser = get_args()
    args = parser.parse_args()

    # Convert status argument to format used by Launchpad
    args.min_status = args.min_status.replace('-', ' ')
    if not args.ping_only and (args.min_status != 'unknown'):
        args.min_status = args.min_status.capitalize()

    if args.choose and (not args.top_number or args.top_number < 2):
        parser.print_usage()
        exit((
            "error: -c/--choose option requires -t/--top-number NUMBER "
            "where NUMBER is greater than 1."
        ))

    return args


def get_mirrors(mirrors_url):
    """Fetch list of Ubuntu mirrors"""
    stderr.write("Getting list of mirrors...")
    try:
        mirrors_list = get_html(mirrors_url)
    except URLGetError as err:
        exit("Error getting list from %s:\n\t%s" % (mirrors_list, err))
    stderr.write("done.\n")

    return mirrors_list.splitlines()


def print_status(info, rank):
    """Print full mirror status report for ranked item"""
    for key in ("Org", "Speed"):
            info.setdefault(key, "N/A")

    print((
        "%(rank)d. %(mirror)s\n%(tab)sLatency: %(ms).2f ms\n"
        "%(tab)sOrg:     %(org)s\n%(tab)sStatus:  %(status)s\n"
        "%(tab)sSpeed:   %(speed)s" % {
            'tab': '    ',
            'rank': rank + 1,
            'mirror': info["Host"],
            'ms': info["Latency"],
            'org': info["Organisation"],
            'status': info["Status"],
            'speed': info["Speed"]
        }
    ))


def print_latency(info, rank):
    """Print latency information for mirror in ranked report"""
    print("%d. %s: %.2f ms" % (rank+1, info["Host"], info["Latency"]))


def ask(query):
    """Ask for unput from user"""
    answer = get_input(query)
    return answer


def get_selected_mirror(rank, list_size):
    """Prompt for user input to select desired mirror"""
    key = ask("Choose a mirror (1 - %d)\n'q' to quit " % list_size)
    while True:
        try:
            key = int(key)
        except ValueError:
            if key == 'q':
                exit()
        else:
            if (key >= 1) and (key <= rank):
                break

        key = ask("Invalid entry ")

    return key-1


def yes_or_no(query):
    """Get definitive answer"""
    opts = ('yes', 'no')
    answer = ask(query)
    while answer != opts[0]:
        if answer == opts[1]:
            exit(0)
        answer = ask("Please enter '%s' or '%s': " % opts)


def apt_select():
    """Run apt-select: Ubuntu archive mirror reporting tool"""
    args = set_args()
    try:
        sources = AptSources()
    except ValueError as err:
        exit("Error setting system information: %s" % err)
    except SourcesFileError as err:
        exit("Error with current apt sources: %s" % err)

    mirrors_loc = "mirrors.ubuntu.com"
    mirrors_url = "http://%s/mirrors.txt" % mirrors_loc
    mirrors_list = get_mirrors(mirrors_url)

    archives = Mirrors(mirrors_list, args.ping_only, args.min_status)
    archives.get_rtts()
    if archives.got["ping"] < args.top_number:
        args.top_number = archives.got["ping"]

    if args.top_number == 0:
        exit("Cannot connect to any mirrors in %s\n." % mirrors_list)

    if not args.ping_only:
        archives.get_launchpad_urls()
        if not archives.abort_launch:
            # Mirrors needs a limit to stop launching threads
            archives.status_num = args.top_number
            stderr.write("Looking up %d status(es)\n" % args.top_number)
            archives.lookup_statuses(
                args.min_status, sources.codename, sources.arch
            )

        if args.top_number > 1:
            stderr.write('\n')

    rank = 0
    current_key = -1
    if args.ping_only or archives.abort_launch:
        archives.top_list = archives.ranked[:args.top_number]

    try:
        sources.set_current_archives()
    except SourcesFileError as err:
        raise SourcesFileError(err)

    current_url = sources.urls[0]
    for url in archives.top_list:
        info = archives.urls[url]
        if url == current_url:
            info["Host"] += " (current)"
            current_key = rank

        if not args.ping_only and not archives.abort_launch:
            print_status(info, rank)
        else:
            print_latency(info, rank)

        rank += 1
        if rank == args.top_number:
            break

    key = 0
    if args.choose:
        key = get_selected_mirror(rank, len(archives.top_list))

    if args.list_only:
        exit()

    # Avoid generating duplicate sources.list
    if current_key == key:
        exit((
            "%s is the currently used mirror.\n%s" %
            (archives.urls[current_url]["Host"], sources.skip_gen_msg)
        ))

    work_dir = getcwd()
    if work_dir == sources.directory[0:-1]:
        query = (
            "'%(dir)s' is the current directory.\n"
            "Generating a new '%(apt)s' file will "
            "overwrite the current file.\n"
            "You should copy or backup '%(apt)s' before replacing it.\n"
            "Continue?\n[yes|no] " % {
                'dir': sources.directory,
                'apt': sources.apt_file
            }
        )
        yes_or_no(query)

    new_mirror = archives.top_list[key]
    try:
        sources.generate_new_config(work_dir, new_mirror)
    except SourcesFileError as err:
        exit("Error generating new config file" % err)
    else:
        print("New config file saved to %s" % sources.new_file_path)

    exit()

if __name__ == '__main__':
    # Support input for both Python 2 and 3
    get_input = input
    if version_info[:2] <= (2, 7):
        get_input = raw_input

    try:
        apt_select()
    except KeyboardInterrupt:
        stderr.write("Aborting...\n")
