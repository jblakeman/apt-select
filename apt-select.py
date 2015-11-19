#!/usr/bin/env python

from __future__ import print_function
from sys import exit, stderr
from os import getcwd, path
from subprocess import check_output
from argparse import ArgumentParser, RawTextHelpFormatter
from util_funcs import getHTML
from mirrors import RoundTrip, Data, statuses
from bs4 import BeautifulSoup

parser = ArgumentParser(
    description=(
        "Find the fastest Ubuntu apt mirrors.\n"
        "Generate new sources.list file."
    ),
    formatter_class=RawTextHelpFormatter
)
parser.add_argument(
    '-t',
    '--top-number',
    nargs=1,
    type=int,
    help=(
        "specify number of mirrors to return\n"
        "default: 1\n"
    ),
    default=1,
    metavar='NUMBER'
)

status_args = [
    x[0].lower() + x[1:] for x in [
        y.replace(' ', '-') for y in statuses
    ]
]
status_args.reverse()

test_group = parser.add_mutually_exclusive_group(required=False)
test_group.add_argument(
    '-m',
    '--min-status',
    nargs=1,
    choices=status_args,
    help=(
        "return mirrors with minimum status\n"
        "choices:\n"
        "   %(up)s\n"
        "   %(day)s\n"
        "   %(two_day)s\n"
        "   %(week)s\n"
        "   %(unknown)s\n"
        "default: %(up)s\n" % {
            'up':status_args[0],
            'day':status_args[1],
            'two_day':status_args[2],
            'week':status_args[3],
            'unknown':status_args[4]
        }
    ),
    default=status_args[0],
    metavar='STATUS'
)
test_group.add_argument(
    '-p',
    '--ping-only',
    action='store_true',
    help=(
        "rank mirror(s) by latency only, disregard status(es)\n"
        "cannot be used in conjunction with -m/--min-status\n"
    ),
    default=False
)

output_group = parser.add_mutually_exclusive_group(required=False)
output_group.add_argument(
    '-c',
    '--choose',
    action='store_true',
    help=(
        "choose mirror from a list\n"
        "requires -t/--top-num NUMBER where NUMBER > 1\n"
    ),
    default=False
)
output_group.add_argument(
    '-l',
    '--list',
    dest='list_only',
    action='store_true',
    help=(
        "print list of mirrors only, don't generate file\n"
        "cannot be used in conjunction with -c/--choose\n"
    ),
    default=False
)

args = parser.parse_args()

# argparse returns list type for only choice arguments, not default
def indexZero(flag):
    if type(flag) is list:
        return flag[0]
    else:
        return flag

flag_number = indexZero(args.top_number)
flag_status = indexZero(args.min_status).replace('-', ' ')
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

def notUbuntu():
    exit("Not an Ubuntu OS")

try:
    release = check_output(["lsb_release", "-ics"])
except OSError:
    notUbuntu()
else:
    release = [s.strip() for s in release.decode('utf-8').split()]

if release[0] == 'Debian':
    exit("Debian is not currently supported")
elif release[0] != 'Ubuntu':
    notUbuntu()

directory = '/etc/apt/'
apt_file = 'sources.list'
sources_path = directory + apt_file
if not path.isfile(sources_path):
    exit("%s must exist as file" % sources_path)

codename = release[1][0].upper() + release[1][1:]
ubuntu_url = "mirrors.ubuntu.com"
mirror_list = "http://%s/mirrors.txt" % ubuntu_url

stderr.write("Getting list of mirrors ...")
archives = getHTML(mirror_list)
stderr.write("done.\n")

def parseURL(path):
    path = path.split('//', 1)[-1]
    return path.split('/', 1)[0]

urls = {}
for archive in archives.splitlines():
    urls[parseURL(archive)] = None

def progressUpdate(processed, total, message):
    if total > 1:
        percent = int((float(processed) / total) * 100)
        stderr.write("\r%s [%d/%d] %d%%" % (message, processed, total, percent))
        stderr.flush()

tested = 0
processed = 0
low_rtts = {}
num_urls = len(urls)
message = "Testing %d mirror(s)" % num_urls
progressUpdate(0, num_urls, message)
for url in urls:
    ping = RoundTrip(url)
    lowest = ping.minRTT()
    if lowest:
        low_rtts.update({url:lowest})
        tested += 1

    processed += 1
    progressUpdate(processed, num_urls, message)

stderr.write('\n')

if len(low_rtts) == 0:
    exit((
        "Cannot connect to any mirrors in %s\n."
        "Minimum latency of this machine may exceed"
        "2.5 seconds or\nthere may be other unknown"
        "TCP connectivity issues.\n" % mirror_list
    ))

hardware = check_output(["uname", "-m"]).strip().decode('utf-8')
if hardware == 'x86_64':
    hardware = 'amd64'
else:
    hardware = 'i386'

ranks = sorted(low_rtts, key=low_rtts.__getitem__)
num_ranked = len(ranks)
if flag_number > num_ranked:
    flag_number = num_ranked

info = []
if not flag_ping:
    message = "Looking up %d status(es)" % flag_number
    progressUpdate(0, flag_number, message)
    launchpad_base = "https://launchpad.net"
    launchpad_url = launchpad_base + "/ubuntu/+archivemirrors"
    launchpad_html = getHTML(launchpad_url)
    for element in BeautifulSoup(launchpad_html).table.descendants:
        try:
            url = element.a
        except AttributeError:
            pass
        else:
            try:
                url = url["href"]
            except TypeError:
                pass
            else:

                if url in archives.splitlines():
                    urls[parseURL(url)] = launchpad_base + prev

                if url.startswith("/ubuntu/+mirror/"):
                    prev = url

    for rank in ranks:
        launchpad_data = Data(
            rank,
            urls[rank],
            codename,
            hardware,
            flag_status
        ).getInfo()
        if launchpad_data:
            info.append(launchpad_data)

        info_size = len(info)
        progressUpdate(info_size, flag_number, message)
        if info_size == flag_number:
            break
else:
    for rank in ranks:
        info.append(rank)
        info_size = len(info)
        if info_size == flag_number:
            break

if (flag_number > 1) and not flag_ping:
    stderr.write('\n')

if info_size == 0:
    exit((
        "Unable to find alternative mirror status(es)\n"
        "Try using -p/--ping-only option or adjust -m/--min-status argument"
    ))

found = None
with open(sources_path, 'r') as f:
    lines = f.readlines()
    def confirmMirror(url):
        deb = ('deb', 'deb-src')
        proto = ('http://', 'ftp://')
        if (url and (url[0] in deb) and
                (proto[0] in url[1] or
                 proto[1] in url[1])):
            return True
        else:
            return

    repo = []
    required_repo = "main"
    for line in lines:
        fields = line.split()
        if confirmMirror(fields):
            if (not found and
                    (release[1] in fields[2]) and
                    (fields[3] == required_repo)):
                repo += [fields[1]]
                found = True
                continue
            elif (fields[2] == '%s-security' % (release[1])):
                repo += [fields[1]]
                break

    if not repo:
        exit((
            "Error finding current %s repository in %s" %
            (required_repo, sources_path)
        ))

repo_name = parseURL(repo[0])
current = None
current_key = None
for i, j in enumerate(info):
    if type(j) is tuple:
        mirror_url = j[0]
    else:
        mirror_url = j

    if mirror_url == repo_name:
        mirror_url += " (current)"
        current_key = i
        if i == 0:
            current = True
        else:
            current = False

    if not flag_ping:
        print((
            "%(rank)d. %(mirror)s\n"
            "%(tab)sLatency:  \t%(ms)d ms\n"
            "%(tab)sStatus:   \t%(status)s\n"
            "%(tab)sBandwidth:\t%(speed)s" % {
                'tab':    '    ',
                'rank':   i + 1,
                'mirror': mirror_url,
                'ms':     low_rtts[j[0]],
                'status': j[1][0],
                'speed':  j[1][1]
            }
        ))
    else:
        print("%d. %s: %d ms" % (i + 1, j, low_rtts[j]))

try:
    input = raw_input
except NameError:
    pass

def ask(query):
    global input
    answer = input(query)
    return answer

def currentMirror(require=True):
    global current
    global repo_name
    if current or not require:
        exit((
            "%s is the currently used mirror.\n"
            "There is nothing to be done." % repo_name
        ))

def whichKey(flag, info, key):
    if not flag:
        return info[key][0]
    else:
        return info[key]

if flag_choose:
    query = "Choose a mirror (1 - %d)\n'q' to quit " % info_size
    key = ask(query)
    choices = range(1, info_size+1)
    while True:
        try:
            key = int(key)
        except ValueError:
            if key == 'q':
                exit()

        if type(key) is str or key not in choices:
            query = "Invalid entry "
            key = ask(query)
            continue

        break

    key = key - 1
    if current_key == key:
        currentMirror(require=False)

    mirror = whichKey(flag_ping, info, key)
else:
    mirror = whichKey(flag_ping, info, 0)

if flag_list:
    exit()
elif not flag_choose:
    currentMirror()

# Switch mirror from resolvable url back to full path
for m in archives.splitlines():
    if mirror in m:
        mirror = m
        break

lines = ''.join(lines)
for r in repo:
    lines = lines.replace(r, mirror)

def yesOrNo():
    y = 'yes'
    n = 'no'
    options = "Please enter '%s' or '%s': " % (y,n)
    while True:
        answer = ask(query)
        if answer == y:
            break
        elif answer == n:
            exit(0)
        else:
            query = options

wd = getcwd()
if wd == directory[0:-1]:
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
    yesOrNo()

write_file = wd + "/" + apt_file
try:
    with open(write_file, 'w') as f:
        f.write(lines)
except IOError as err:
    if err.strerror == 'Permission denied':
        exit((
            "%s\nYou do not own %s\n"
            "Please run the script from a directory you own." %
            (err, wd)
        ))
    else:
        exit(err)
else:
    print("New config file saved to %s" % write_file)

exit(0)
