#!/usr/bin/env python
"""Main apt-select script"""

from sys import exit, stderr, version_info
from os import getcwd
from apt_select.arguments import get_args
from apt_select.utils import get_text, URLGetTextError
from apt_select.mirrors import Mirrors
from apt_select.apt_system import AptSources, SourcesFileError

# Support input for Python 2 and 3
get_input = input
if version_info[:2] <= (2, 7):
    get_input = raw_input


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
        mirrors_list = get_text(mirrors_url)
    except URLGetTextError as err:
        exit("Error getting list from %s:\n\t%s" % (mirrors_url, err))
    stderr.write("done.\n")

    return mirrors_list.splitlines()


def print_status(info, rank):
    """Print full mirror status report for ranked item"""
    for key in ("Org", "Speed"):
            info.setdefault(key, "N/A")

    print((
        "%(rank)d. %(mirror)s\n"
        "%(tab)sLatency: %(ms).2f ms\n"
        "%(tab)sOrg:     %(org)s\n"
        "%(tab)sStatus:  %(status)s\n"
        "%(tab)sSpeed:   %(speed)s" % {
            'tab': '    ',
            'rank': rank ,
            'mirror': info['Host'],
            'ms': info['Latency'],
            'org': info['Organisation'],
            'status': info['Status'],
            'speed': info['Speed']
        }
    ))


def print_latency(info, rank, max_host_len):
    """Print latency information for mirror in ranked report"""
    print("%(rank)d. %(mirror)s: %(padding)s%(ms).2f ms" % {
        'rank': rank,
        'padding': (max_host_len - info.get('host_len', max_host_len)) * ' ',
        'mirror': info['Host'],
        'ms': info['Latency']
    })


def ask(query):
    """Ask for unput from user"""
    answer = get_input(query)
    return answer


def get_selected_mirror(list_size):
    """Prompt for user input to select desired mirror"""
    key = ask("Choose a mirror (1 - %d)\n'q' to quit " % list_size)
    while True:
        try:
            key = int(key)
        except ValueError:
            if key == 'q':
                exit()
        else:
            if (key >= 1) and (key <= list_size):
                break

        key = ask("Invalid entry ")

    return key


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

    if args.ping_only or archives.abort_launch:
        archives.top_list = archives.ranked[:args.top_number]

    sources.set_current_archives()
    current_url = sources.urls[0]
    if archives.urls.get(current_url):
        archives.urls[current_url]['Host'] += " (current)"

    show_status = False
    max_host_len = 0
    if not args.ping_only and not archives.abort_launch:
        show_status = True
    else:
        def set_hostname_len(url, i):
            hostname_len = len(str(i) + archives.urls[url]['Host'])
            archives.urls[url]['host_len'] = hostname_len
            return hostname_len

        max_host_len = max([set_hostname_len(url, i+1)
                            for i, url in enumerate(archives.top_list)])
    for i, url in enumerate(archives.top_list):
        info = archives.urls[url]
        rank = i + 1
        if show_status:
            print_status(info, rank)
        else:
            print_latency(info, rank, max_host_len)

    key = 0
    if args.choose:
        key = get_selected_mirror(len(archives.top_list)) - 1

    if args.list_only:
        exit()

    new_mirror = archives.top_list[key]
    print("Selecting mirror %(mirror)s ..." % {'mirror': new_mirror})
    if current_url == new_mirror:
        exit((
            "%(url)s is the currently used mirror.\n"
            "%(message)s" % {
                'url': current_url,
                'message': sources.skip_gen_msg
            }))

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
    main()
