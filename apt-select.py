#!/usr/bin/env python

from __future__ import print_function
from sys import exit, stderr, stdout
from os import getcwd
from re import findall, search, match
from subprocess import check_output, CalledProcessError
from argparse import ArgumentParser, RawTextHelpFormatter

try:
    from urllib.request import urlopen, HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

from mirrors import RoundTrip, Data, statuses

parser = ArgumentParser(description=(
                            "Find the fastest Ubuntu apt mirrors.\n"
                            "Generate new sources.list file."
                        ),
                        formatter_class=RawTextHelpFormatter)
parser.add_argument('-t', '--top-number', nargs=1, type=int,
                    help=(
                        "specify number of mirrors to return\n"
                        "default: 1\n"
                    ), default=1, metavar='NUMBER')

status_args = [
    x[0].lower() + x[1:] for x in [
        y.replace(' ', '-') for y in statuses
    ]
]
status_args.reverse()

parser.add_argument('-m', '--min-status', nargs=1,
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
                    default=status_args[0], metavar='STATUS')

group = parser.add_mutually_exclusive_group(required=False)
group.add_argument('-c', '--choose', action='store_true',
                    help=(
                        "choose mirror from a list\n"
                        "requires -t/--top-num NUMBER where NUMBER > 1\n"
                    ), default=False)
group.add_argument('-l', '--list', dest='list_only', action='store_true',
                    help=(
                        "print list of mirrors only, don't generate file\n"
                        "cannot be used in conjunction with -c/--choose option"
                    ),
                    default=False)

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

def errorExit(err, status):
    print(err, file=stderr)
    exit(status)

if flag_choose and (not flag_number or flag_number < 2):
    parser.print_usage()
    errorExit(("error: -c/--choose option requires -t/--top-number NUMBER "
               "where NUMBER is greater than 1."), 1)

def notUbuntu():
    errorExit("Not an Ubuntu OS", 1)

try:
    release = check_output("lsb_release -ics 2>/dev/null", shell=True)
except CalledProcessError:
    notUbuntu()
else:
    release = [s.strip() for s in release.decode().split()]

hardware = check_output("uname -m", shell=True).strip().decode()
if release[0] == 'Debian':
    errorExit("Debian is not currently supported", 1)
elif release[0] != 'Ubuntu':
    notUbuntu()

codename = release[1][0].upper() + release[1][1:]
ubuntu_url = "mirrors.ubuntu.com"
mirror_list = "http://%s/mirrors.txt" % ubuntu_url
try:
    archives = urlopen(mirror_list)
except IOError as err:
    errorExit(("Could not connect to '%s'.\n"
               "%s" % (mirror_list, err)), 1)

def progressUpdate(processed, total, status=None):
    if total > 1:
        stdout.write('\r')
        percent = int((float(processed)/total)*100)
        stdout.write("[%d/%d] %d%%" % (processed, total, percent))
        stdout.flush()

print("Got list from %s" % ubuntu_url)
archives = archives.read().decode()
urls = findall(r'http://([\w|\.|\-]+)/', archives)
tested = 0
processed = 0
avg_rtts = {}
num_urls = len(urls)
print("Testing %d mirror(s)" % num_urls)
progressUpdate(0, num_urls)
for url in urls:
    ping = RoundTrip(url)
    avg = ping.avgRTT()
    if avg:
        avg_rtts.update({url:avg})
        tested += 1

    processed += 1
    progressUpdate(processed, num_urls)

print()
if num_urls != tested:
    print("%d mirror(s) returned no response" % (num_urls - tested))

if hardware == 'x86_64':
    hardware = 'amd64'
else:
    hardware = 'i386'

ranks = sorted(avg_rtts, key=avg_rtts.__getitem__)
info = []
print("Looking up status information")
progressUpdate(0, flag_number)
for rank in ranks:
    d = Data(rank, codename, hardware, flag_status)
    data = d.getInfo()
    if data:
        info.append(data)

    info_size = len(info)
    progressUpdate(info_size, flag_number)
    if info_size == flag_number:
        break

print()
if info_size == 0:
    errorExit("Unable to find alternative mirror status(es)", 1)

directory = '/etc/apt/'
apt_file = 'sources.list'
found = None
with open('%s' % directory + apt_file, 'r') as f:
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

    for line in lines:
        fields = line.split()
        if not found:
            if (confirmMirror(fields) and
                    (release[1] in fields[2])):
                repo = [fields[1]]
                found = True
                continue
        else:
            if (confirmMirror(fields) and
                    (fields[2] == '%s-security' % (release[1]))):
                repo += [fields[1]]
                break
    else:
        errorExit("Error finding current repositories", 1)

repo_name = match(r'http://([\w|\.|\-]+)/', repo[0]).group(1)
current = None
current_key = None
for i, j in enumerate(info):
    mirror_url = j[0]
    if mirror_url == repo_name:
        mirror_url += " (current)"
        current_key = i
        if i == 0:
            current = True
        else:
            current = False

    print(("%(rank)d. %(mirror)s\n%(tab)sLatency: %(ms)d ms\n"
           "%(tab)sStatus: %(status)s\n%(tab)sBandwidth: %(speed)s" %
           {
                'tab': '    ',
                'rank': i + 1,
                'mirror': mirror_url,
                'ms': avg_rtts[j[0]],
                'status': j[1][0],
                'speed': j[1][1]
           }))

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
        errorExit(("%s is the currently used mirror.\n"
                   "There is nothing to be done." % repo_name), 0)

if flag_choose:
    query = "Choose a mirror (1 - %d)\n'q' to quit " % info_size
    key = ask(query)
    while True:
        match = search(r'[1-5]', key)
        if match and (len(key) == 1):
            key = int(key)
            break
        elif key == 'q':
            exit()
        else:
            query = "Invalid entry "
            key = ask(query)

    key = key - 1
    if current_key == key:
        currentMirror(require=False)

    mirror = info[key][0]
else:
    mirror = info[0][0]

if flag_list:
    exit()
else:
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
            "Continue?\n[yes|no] " %
            {'dir': directory, 'apt': apt_file}
        )
        yesOrNo()

    try:
        with open(apt_file, 'w') as f:
            f.write(lines)
    except IOError as err:
        if err.strerror == 'Permission denied':
            errorExit(("%s\nYou do not own %s\n"
                       "Please run the script from a directory you own." %
                       (err, wd)), 1)
        else:
            errorExit(err, 1)

exit(0)
