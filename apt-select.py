#!/usr/bin/env python

from sys import exit, stderr, version_info
from os import getcwd, path
from subprocess import check_output
from arguments import get_args
from util_funcs import get_html, HTMLGetError
from mirrors import Mirrors


def not_ubuntu():
    """Notify of incompatibility"""
    exit("Not an Ubuntu OS")


def confirm_mirror(uri):
    """Check if line follows correct sources.list URI"""
    deb = ('deb', 'deb-src')
    proto = ('http://', 'ftp://')
    if (uri and (uri[0] in deb) and
            (proto[0] in uri[1] or
             proto[1] in uri[1])):
        return True

    return False


def ask(query):
    """Ask for unput from user"""
    answer = get_input(query)
    return answer


def yes_or_no(query):
    """Get definitive answer"""
    opts = ('yes', 'no')
    answer = ask(query)
    while answer != opts[0]:
        if answer == opts[1]:
            exit(0)
        answer = ask("Please enter '%s' or '%s': " % opts)


def validate_args():
    parser = get_args()
    args = parser.parse_args()
    args.top_number = args.top_number[0]
    args.min_status = args.min_status[0].replace('-', ' ')

    if not args.ping_only and (args.min_status != 'unknown'):
        # Convert status argument to format used by Launchpad
        args.min_status = args.min_status[0].upper() + args.min_status[1:]

    if args.choose and (not args.top_number or args.top_number < 2):
        parser.print_usage()
        exit((
            "error: -c/--choose option requires -t/--top-number NUMBER "
            "where NUMBER is greater than 1."
        ))

    return args


def get_release():
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


def apt_select():
    """Run apt-select: Ubuntu archive mirror reporting tool"""
    args = validate_args()
    release = get_release()

    directory = '/etc/apt/'
    apt_file = 'sources.list'
    sources_path = directory + apt_file
    if not path.isfile(sources_path):
        exit("%s must exist as file" % sources_path)

    mirrors_loc = "mirrors.ubuntu.com"
    mirrors_url = "http://%s/mirrors.txt" % mirrors_loc
    stderr.write("Getting list of mirrors...")
    try:
        mirrors_list = get_html(mirrors_url)
    except HTMLGetError as err:
        exit("Error getting list from %s:\n\t%s" % (mirrors_list, err))
    stderr.write("done.\n")
    mirrors_list = mirrors_list.splitlines()

    codename = release[1][0].upper() + release[1][1:]
    hardware = check_output(["uname", "-m"]).strip().decode('utf-8')
    if hardware == 'x86_64':
        hardware = 'amd64'
    else:
        hardware = 'i386'

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
            archives.lookup_statuses(args.min_status, codename, hardware)

        if args.top_number > 1:
            stderr.write('\n')

    repo_name = ""
    found = False
    skip_gen_msg = "Skipping file generation."
    with open(sources_path, 'r') as sources_file:
        lines = sources_file.readlines()
        repos = []
        required_repo = "main"
        for line in lines:
            fields = line.split()
            if confirm_mirror(fields):
                if (not found and
                        (release[1] in fields[2]) and
                        (fields[3] == required_repo)):
                    repos += [fields[1]]
                    found = True
                    continue
                elif fields[2] == '%s-security' % (release[1]):
                    repos += [fields[1]]
                    break

        if not repos:
            stderr.write((
                "Error finding current %s repository in %s\n%s\n" %
                (required_repo, sources_path, skip_gen_msg)
            ))
        else:
            repo_name = repos[0]

    rank = 0
    current_key = -1
    if args.ping_only:
        archives.top_list = archives.ranked[:args.top_number+1]

    for url in archives.top_list:
        info = archives.urls[url]
        host = info["Host"]
        if url == repo_name:
            host += " (current)"
            current_key = rank

        if not args.ping_only and not archives.abort_launch:
            if "Status" in info:
                for key in ("Org", "Speed"):
                    info.setdefault(key, "N/A")
                print((
                    "%(rank)d. %(mirror)s\n%(tab)sLatency: %(ms)d ms\n"
                    "%(tab)sOrg:     %(org)s\n%(tab)sStatus:  %(status)s\n"
                    "%(tab)sSpeed:   %(speed)s" % {
                        'tab': '    ',
                        'rank': rank + 1,
                        'mirror': host,
                        'ms': info["Latency"],
                        'org': info["Organisation"],
                        'status': info["Status"],
                        'speed': info["Speed"]
                    }
                ))
        else:
            print("%d. %s: %d ms" % (rank+1, info["Host"], info["Latency"]))

        rank += 1
        if rank == args.top_number:
            break

    key = 0
    if args.choose:
        key = ask((
            "Choose a mirror (1 - %d)\n'q' to quit " %
            len(archives.top_list)
        ))
        while True:
            try:
                key = int(key)
            except ValueError:
                if key == 'q':
                    exit()

            if (type(key) is not str) and (key >= 1) and (key <= rank):
                break

            key = ask("Invalid entry ")

        key -= 1

    if args.list_only:
        exit()

    # Avoid generating duplicate sources.list
    if current_key == key:
        exit((
            "%s is the currently used mirror.\n%s" %
            (archives.urls[repo_name]["Host"], skip_gen_msg)
        ))

    mirror = archives.top_list[key]
    lines = ''.join(lines)
    for repo in repos:
        lines = lines.replace(repo, mirror)

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
        with open(write_file, 'w') as sources_file:
            sources_file.write(lines)
    except IOError as err:
        exit("Unable to generate sources.list:\n\t%s\n" % err)
    else:
        print("New config file saved to %s" % write_file)

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
