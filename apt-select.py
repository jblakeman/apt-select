#!/usr/bin/env python

from sys import exit, stderr, version_info
from os import getcwd, path
from subprocess import check_output
from arguments import get_args
from utils import get_html, URLGetError
from mirrors import Mirrors


def set_args():
    """Set arguments, disallow bad combination"""
    parser = get_args()
    args = parser.parse_args()

    # Convert status argument to format used by Launchpad
    args.min_status = args.min_status.replace('-', ' ')
    if not args.ping_only and (args.min_status != 'unknown'):
        args.min_status = args.min_status[0].upper() + args.min_status[1:]

    if args.choose and (not args.top_number or args.top_number < 2):
        parser.print_usage()
        exit((
            "error: -c/--choose option requires -t/--top-number NUMBER "
            "where NUMBER is greater than 1."
        ))

    return args


def not_ubuntu():
    """Notify of incompatibility"""
    exit("Not an Ubuntu OS")


def get_release():
    """Call system for Ubuntu release information"""
    try:
        release = check_output(["lsb_release", "-ics"])
    except OSError:
        not_ubuntu()
    else:
        release = [s.strip() for s in release.decode('utf-8').split()]

    if release[0] == 'Debian':
        exit("Debian is not currently supported")
    elif release[0] != 'Ubuntu':
        not_ubuntu()

    return release


def mandatory_file(file_path):
    """Panic if required file doesn't exist"""
    if not path.isfile(file_path):
        exit("%s must exist as file" % file_path)


def get_mirrors(mirrors_url):
    """Fetch list of Ubuntu mirrors"""
    stderr.write("Getting list of mirrors...")
    try:
        mirrors_list = get_html(mirrors_url)
    except URLGetError as err:
        exit("Error getting list from %s:\n\t%s" % (mirrors_list, err))
    stderr.write("done.\n")

    return mirrors_list.splitlines()


def get_arch():
    """Return architecture information in Launchpad format"""
    arch = check_output(["uname", "-m"]).strip().decode('utf-8')
    if arch == 'x86_64':
        return 'amd64'
    return 'i386'


def confirm_mirror(uri, deb, protos):
    """Check if line follows correct sources.list URI"""
    if (uri and (uri[0] in deb) and
            (protos[0] in uri[1] or
             protos[1] in uri[1])):
        return True

    return False


def get_current_archives(sources_file, release, required_component):
    """Parse system apt sources file for URIs to replace"""
    lines = sources_file.readlines()
    archives = []
    deb = {k: None for k in ('deb', 'deb-src')}
    protos = ('http://', 'ftp://')
    for line in lines:
        fields = line.split()
        if confirm_mirror(fields, deb, protos):
            # Start by finding the required component (main)
            if (not archives and
                    # The release name (e.g. xenial) and component are the
                    # third, and fourth fields (as described in the sources.list
                    # man page examples)
                    (release[1] in fields[2]) and
                    (fields[3] == required_component)):
                archives.append(fields[1])
                continue
            # Try to find the mirror used for security component, only if
            # we've already found the mirror for the required repository
            elif (archives and
                    # The release name dash-prefixes the security component
                    (fields[2] == '%s-security' % (release[1])) and
                    # Mirror urls should be unique as they'll be used in a
                    # global search and replace to generate a new file
                    (archives[0] != fields[1])):
                archives.append(fields[1])
                break

    return {"archives": archives, "lines": lines}


def print_status(info, rank):
    """Print full mirror status report for ranked item"""
    for key in ("Org", "Speed"):
            info.setdefault(key, "N/A")

    print((
        "%(rank)d. %(mirror)s\n%(tab)sLatency: %(ms)d ms\n"
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
    print("%d. %s: %d ms" % (rank+1, info["Host"], info["Latency"]))


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


def gen_sources_file(file_name, lines):
    """Generate new apt sources.list file"""
    try:
        with open(file_name, 'w') as f:
            f.write(lines)
    except IOError as err:
        raise (err)
    else:
        print("New config file saved to %s" % file_name)


def apt_select():
    """Run apt-select: Ubuntu archive mirror reporting tool"""
    args = set_args()
    release = get_release()

    directory = '/etc/apt/'
    apt_file = 'sources.list'
    sources_path = directory + apt_file
    mandatory_file(sources_path)

    mirrors_loc = "mirrors.ubuntu.com"
    mirrors_url = "http://%s/mirrors.txt" % mirrors_loc
    mirrors_list = get_mirrors(mirrors_url)

    codename = release[1][0].upper() + release[1][1:]
    arch = get_arch()

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
            archives.lookup_statuses(args.min_status, codename, arch)

        if args.top_number > 1:
            stderr.write('\n')

    archive_name = ""
    required_component = "main"
    skip_gen_msg = "Skipping file generation."
    with open(sources_path, 'r') as sources_file:
        sources = get_current_archives(sources_file, release, required_component)
        if "archives" not in sources:
            stderr.write((
                "Error finding current %s archivesitory in %s\n%s\n" %
                (required_component, sources_path, skip_gen_msg)
            ))
        else:
            archive_name = sources["archives"][0]

    rank = 0
    current_key = -1
    if args.ping_only or archives.abort_launch:
        archives.top_list = archives.ranked[:args.top_number]

    for url in archives.top_list:
        info = archives.urls[url]
        if url == archive_name:
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
            (archives.urls[archive_name]["Host"], skip_gen_msg)
        ))

    # Replace all relevant instances of current mirror URIs in sources.list
    # with the new mirror URI.  We use this to write the new file.
    mirror = archives.top_list[key]
    sources["lines"] = ''.join(sources["lines"])
    for archive in sources["archives"]:
        sources["lines"] = sources["lines"].replace(archive, mirror)

    work_dir = getcwd()
    if work_dir == directory[0:-1]:
        query = (
            "'%(dir)s' is the current directory.\n"
            "Generating a new '%(apt)s' file will "
            "overwrite the current file.\n"
            "You should copy or backup '%(apt)s' before replacing it.\n"
            "Continue?\n[yes|no] " % {
                'dir': directory,
                'apt': apt_file
            }
        )
        yes_or_no(query)

    write_file = work_dir.rstrip('/') + '/' + apt_file
    try:
        gen_sources_file(write_file, sources["lines"])
    except IOError as err:
        exit("Unable to generate new sources.list:\n\t%s\n" % err)

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
