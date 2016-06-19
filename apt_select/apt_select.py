#!/usr/bin/env python

from sys import exit, stderr, version_info
from os import getcwd
from arguments import get_args
from utils import get_html, URLGetError
from mirrors import Mirrors
from apt_system import AptSources, SourcesFileError


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
            archives.lookup_statuses(args.min_status)

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


def main():
    try:
        apt_select()
    except KeyboardInterrupt:
        stderr.write("Aborting...\n")

if __name__ == '__main__':
    # Support input for both Python 2 and 3
    get_input = input
    if version_info[:2] <= (2, 7):
        get_input = raw_input

    main()
