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


def assign_defaults(info, keys, default):
    """Assign a default dict value to key if key is not present"""
    for key in keys:
        if key not in info:
            info[key] = default


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


def apt_select():
    """Run apt-select: Ubuntu archive mirror reporting tool"""
    parser = get_args()
    args = parser.parse_args()
    flag_number = args.top_number[0]
    # Convert status argument to format used by Launchpad
    flag_status = args.min_status[0].replace('-', ' ')
    if flag_status != 'unknown':
        flag_status = flag_status[0].upper() + flag_status[1:]

    flag_list = args.list_only
    flag_choose = args.choose
    flag_ping = args.ping_only

    if flag_choose and (not flag_number or flag_number < 2):
        parser.print_usage()
        exit((
            "error: -c/--choose option requires -t/--top-number NUMBER "
            "where NUMBER is greater than 1."
        ))

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

    archives = Mirrors(mirrors_list, flag_status, codename, hardware)
    archives.get_rtts()
    if archives.got["ping"] < flag_number:
        flag_number = archives.got["ping"]

    if flag_number == 0:
        exit("Cannot connect to any mirrors in %s\n." % mirrors_list)

    if not flag_ping:
        archives.get_launchpad_urls()
        if not archives.abort_launch:
            archives.status_num = flag_number
            stderr.write("Looking up %d status(es)\n" % flag_number)
            archives.lookup_statuses()

        if flag_number > 1:
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
    if flag_ping:
        archives.top_list = archives.ranked[:flag_number+1]

    for url in archives.top_list:
        info = archives.urls[url]
        host = info["Host"]
        if url == repo_name:
            host += " (current)"
            current_key = rank

        if not flag_ping and not archives.abort_launch:
            if "Status" in info:
                assign_defaults(info, ("Org", "Speed"), "N/A")
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
        if rank == flag_number:
            break

    key = 0
    if flag_choose:
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

    if flag_list:
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
