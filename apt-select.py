#!/usr/bin/env python

from sys import exit
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
parser.add_argument('-c', '--choose', action='store_true',
                    help=(
                        "choose mirror from a list\n"
                        "requires -t, --top-num NUMBER where NUMBER > 2\n"
                    ), default=False)
parser.add_argument('-l', '--list', dest='list_only', action='store_true',
                    help=(
                        "print list of mirrors only, don't generate file\n"
                        "cannot be used in conjunction with -c, --choose option"
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

if flag_choose and (not flag_number or flag_number < 2):
    parser.print_usage()
    print(("-c, --choose option requires -t, --top-number NUMBER "
           "where NUMBER is greater than 1."))
    exit(1)
if flag_choose and flag_list:
    parser.print_usage()
    print("-c, --choose and -l, --list options cannot be used together.")
    exit(1)

def notUbuntu():
    print("Not an Ubuntu OS")
    exit(1)

try:
    release = check_output("lsb_release -ics 2>/dev/null", shell=True)
except CalledProcessError:
    notUbuntu()
else:
    release = [s.strip() for s in release.decode().split()]

hardware = check_output("uname -m", shell=True).strip().decode()
if release[0] == 'Debian':
    print("Debian is not currently supported")
    exit(1)
elif release[0] != 'Ubuntu':
    notUbuntu()

codename = release[1][0].upper() + release[1][1:]
mirror_list = "http://mirrors.ubuntu.com/mirrors.txt"
try:
    archives = urlopen(mirror_list)
except IOError as err:
    print(("Could not connect to '%s'.\n"
           "%s" % (mirror_list, err)))
    exit(1)

print("Got list of mirrors")
archives = archives.read().decode()
urls = findall(r'http://([\w|\.|\-]+)/', archives)
n = 0
avg_rtts = {}
for url in urls:
    ping = RoundTrip(url)
    print("Connecting to %s" % url)
    avg = ping.avgRTT()
    if avg:
        avg_rtts.update({url:avg})
        n += 1

print("Tested %d mirrors" % n)
if hardware == 'x86_64':
    hardware = 'amd64'
else:
    hardware = 'i386'

ranks = sorted(avg_rtts, key=avg_rtts.__getitem__)
info = []
print("Looking up status information")
for rank in ranks:
    d = Data(rank, codename, hardware, flag_status)
    data = d.getInfo()
    if data:
        info.append(data)

    info_size = len(info)
    if info_size == flag_number:
        break

if info_size == 0:
    print("Unable to find alternative mirror status(es)")
    exit(1)
elif info_size == 1:
    header = "\nTop mirror:\n"
else:
    header = "\nTop %d mirrors:\n" % info_size

print(header)

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
        print("Error finding current repositories")
        exit(1)

repo_name = match(r'http://([\w|\.|\-]+)/', repo[0]).group(1)
current_key = None
for i, j in enumerate(info):
    mirror_url = j[0]
    if mirror_url == repo_name:
        mirror_url += " (current)"
        current_key = i

    print("%d. %s\n\tLatency: %d ms\n\tStatus: %s\n\tBandwidth: %s\n" %
          (i + 1, mirror_url, avg_rtts[j[0]], j[1][0], j[1][1]))

try:
    input = raw_input
except NameError:
    pass

def ask(query):
    global input
    answer = input(query)
    return answer

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
        print("The mirror you selected is the currently used mirror.\n"
              "There is nothing to be done.")
    exit(0)

    mirror = info[key][0]
else:
    mirror = info[0][0]

# Switch mirror from resolvable url back to full http/ftp path
for m in archives.splitlines():
    if mirror in m:
        mirror = m
        break

if not flag_list:
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
            print(("%s\nYou do not own %s\n"
                   "Please run the script from a directory you own." %
                   (err, wd)))
            exit(1)
        else:
            print(err)
            exit(1)

exit(0)
