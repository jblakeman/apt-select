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

parser = ArgumentParser(description="Find the fastest Ubuntu mirrors",
                        formatter_class=RawTextHelpFormatter)
parser.add_argument('-a', '--auto', action='store_true',
                    help="choose the best mirror", default=False)

status_args = [
    x[0].lower() + x[1:] for x in [
        y.replace(' ', '-') for y in statuses
    ]
]
status_args.reverse()

parser.add_argument('-s', '--status', nargs=1,
                    choices=status_args,
                    help=(
                        'return mirrors with minimum status\n'
                        'choices:\n'
                        '   %(up)s\n'
                        '   %(day)s\n'
                        '   %(two_day)s\n'
                        '   %(week)s\n'
                        '   %(unknown)s\n'
                        'default: %(up)s\n' % {
                            'up':status_args[0],
                            'day':status_args[1],
                            'two_day':status_args[2],
                            'week':status_args[3],
                            'unknown':status_args[4]
                        }
                    ),
                    default=status_args[0], metavar='')

args = parser.parse_args()
flag_status = args.status

# argparse returns list type for only choice arguments, not default
if type(flag_status) is list:
    flag_status = flag_status[0]

flag_status = flag_status.replace('-', ' ')
if flag_status != 'unknown':
    flag_status = flag_status[0].upper() + flag_status[1:]

flag_auto = args.auto

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

top_num = 5
ranks = sorted(avg_rtts, key=avg_rtts.__getitem__)
info = []
print("Looking up status information")
for rank in ranks:
    d = Data(rank, codename, hardware, flag_status)
    data = d.getInfo()
    if data:
        info.append(data)

    info_size = len(info)
    if info_size == top_num:
        break

if info_size == 0:
    print("Unable to find alternative mirror status(es)")
    exit(1)
elif info_size == 1:
    print("Alternative mirror found:")
else:
    print("\nTop %d mirrors:\n" % info_size)

directory = '/etc/apt/'
apt_file = 'sources.list'
found = None
deb = ('deb', 'deb-src')
proto = ('http://', 'ftp://')
with open('%s' % directory + apt_file, 'r') as f:
    lines = f.readlines()
    def confirm_mirror(url, deb, proto):
        if (url and (url[0] in deb) and
                (proto[0] in url[1] or
                 proto[1] in url[1])):
            return True
        else:
            return

    for line in lines:
        fields = line.split()
        if not found:
            if (confirm_mirror(fields, deb, proto) and
                    (release[1] in fields[2])):
                repo = [fields[1]]
                found = True
                continue
        else:
            if (confirm_mirror(fields, deb, proto) and
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

def ask(query, default):
    global input, flag_auto
    if flag_auto:
        return default

    answer = input(query)
    return answer

query = "Choose a mirror (1 - %d)\n'q' to quit " % info_size
key = ask(query, '1')

while True:
    match = search(r'[1-5]', key)
    if match and (len(key) == 1):
        key = int(key)
        break
    elif key == 'q':
        exit()
    else:
        query = "Invalid entry "
        key = ask(query, '1')

key = key - 1
if current_key == key:
    print("The mirror you selected is the currently used mirror.\n"
           "There is nothing to be done.")
    exit(0)

mirror = info[key][0]
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
    query = ''
    options = "Please enter '%s' or '%s': " % (y,n)
    while True:
        answer = ask(query, 'yes')
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
