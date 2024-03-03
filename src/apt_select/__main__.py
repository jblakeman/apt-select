#!/usr/bin/env python
"""Main apt-select script"""

import os
import re
import sys
from argparse import Namespace

import requests
from apt_select import apt, argument, constant, mirror


def set_args() -> tuple[str | Namespace, int]:
    """Set arguments, disallow bad combination"""
    parser = argument.get_arg_parser()
    args = parser.parse_args()

    # Convert status argument to format used by Launchpad
    args.min_status = args.min_status.replace("-", " ")
    if not args.ping_only and (args.min_status != "unknown"):
        args.min_status = args.min_status.capitalize()

    if args.choose and (not args.top_number or args.top_number < 2):
        parser.print_usage()
        return (
            "error: -c/--choose option requires -t/--top-number NUMBER "
            "where NUMBER is greater than 1."
        ), constant.NOK

    if not args.country:
        sys.stderr.write("WARNING: no country code provided. defaulting to US.\n")
        args.country = argument.DEFAULT_COUNTRY
    elif not re.match(r"^[a-zA-Z]{2}$", args.country):
        return (
            f"Invalid country. {args.country} is not in ISO 3166-1 alpha-2 format",
            constant.NOK,
        )

    return args, constant.OK


def get_mirrors(
    mirrors_url: str,
    country: str,
    timeout_sec: float = constant.DEFAULT_REQUEST_TIMEOUT_SEC,
) -> tuple[list[str], int]:
    """Fetch list of Ubuntu mirrors"""
    sys.stderr.write("Getting list of mirrors...")
    response = requests.get(
        mirrors_url, headers=constant.DEFAULT_REQUEST_HEADERS, timeout=timeout_sec
    )
    not_found = requests.codes.get("NOT_FOUND", None)
    if response.status_code == not_found:
        return (
            [f"The mirror list for country: {country} was not found at {mirrors_url}"],
            constant.NOK,
        )

    sys.stderr.write("done.\n")

    return response.text.splitlines(), constant.OK


def print_status(info: dict[str, float | str], rank: int) -> None:
    """Print full mirror status report for ranked item"""
    for key in ("Org", "Speed"):
        info.setdefault(key, "N/A")

    print(
        (
            f"{rank}. {info['Host']}\n"
            f"{'    '}Latency: {info['Latency']:.2f} ms\n"
            f"{'    '}Org:     {info['Organisation']}\n"
            f"{'    '}Status:  {info['Status']}\n"
            f"{'    '}Speed:   {info['Speed']}"
        )
    )


def print_latency(
    info: dict[str, float | str], rank: int, max_hostname_length: int
) -> None:
    """Print latency information for mirror in ranked report"""
    hostname_length = info.get("host_length", max_hostname_length)
    if isinstance(hostname_length, int):
        print(
            f"{rank}. {info['Host']}: "
            f"{(max_hostname_length - hostname_length) * ' '}{info['Latency']:.2f} ms"
        )


def ask(query: str) -> str:
    """Ask for unput from user"""
    answer = input(query)
    return answer


def get_selected_mirror(list_size: int) -> tuple[int | None, int]:
    """Prompt for user input to select desired mirror"""
    key = ask(f"Choose a mirror (1 - {list_size})\n'q' to quit ")
    while True:
        if key == "q":
            return None, constant.USER_INTERRUPT
        try:
            if 1 <= int(key) <= list_size:
                break
        except ValueError:
            key = ask("Invalid entry ")

    return int(key), constant.OK


def yes_or_no(query: str) -> int:
    """Get definitive answer"""
    opts = ("yes", "no")
    answer = ask(query)
    while answer != opts[0]:
        if answer == opts[1]:
            return constant.USER_INTERRUPT
        answer = ask(f"Please enter '{opts[0]}' or '{opts[1]}': ")
    return constant.OK


def apt_select() -> tuple[str | None, int]:
    """Run apt-select: Ubuntu archive mirror reporting tool"""

    try:
        system = apt.System()
    except OSError as err:
        return f"Error setting system information:\n\t{err}", constant.NOK

    try:
        sources = apt.Sources(codename=system.codename)
    except apt.SourcesFileError as err:
        return f"Error with current apt sources:\n\t{err}", constant.NOK

    args, status = set_args()
    if status != constant.OK or isinstance(args, str):
        return f"{args}", status

    mirrors_loc = "mirrors.ubuntu.com"
    mirrors_url = f"http://{mirrors_loc}/{args.country.upper()}.txt"
    mirrors_list, status = get_mirrors(mirrors_url=mirrors_url, country=args.country)
    if status != constant.OK:
        return "".join(mirrors_list), status

    mirrors = mirror.Mirrors(
        url_list=mirrors_list, min_status=args.min_status, ping_only=args.ping_only
    )
    mirrors.measure_rtts()
    if mirrors.got["ping"] < args.top_number:
        args.top_number = mirrors.got["ping"]

    if args.top_number == 0:
        return f"Cannot connect to any mirrors in {mirrors_list}\n.", constant.NOK

    if not args.ping_only:
        mirrors.fetch_launchpad_urls()
        if not mirrors.abort_launch:
            # Mirrors needs a limit to stop launching threads
            mirrors.status_num = args.top_number
            sys.stderr.write(f"Looking up {args.top_number} status(es)\n")
            mirrors.lookup_statuses(
                codename=system.codename.capitalize(), arch=system.arch
            )

        if args.top_number > 1:
            sys.stderr.write("\n")

    if args.ping_only or mirrors.abort_launch:
        mirrors.top_list = mirrors.ranked[: args.top_number]

    sources.set_current_archives()
    current_url = sources.urls["current"]
    if mirrors.urls.get(current_url):
        _v1: float | str = mirrors.urls[current_url]["Host"]
        if isinstance(_v1, str):
            mirrors.urls[current_url]["Host"] = f"{_v1} (current)"

    show_status = False
    max_hostname_length = 0
    if not args.ping_only and not mirrors.abort_launch:
        show_status = True
    else:
        max_hostname_length = max(
            _set_hostname_length(index=i + 1, entry=mirrors.urls[url])
            for i, url in enumerate(mirrors.top_list)
        )
    for i, url in enumerate(mirrors.top_list):
        info = mirrors.urls[url]
        rank = i + 1
        if show_status:
            print_status(info=info, rank=rank)
        else:
            print_latency(info=info, rank=rank, max_hostname_length=max_hostname_length)

    key = 0
    if args.choose:
        maybe_key, status = get_selected_mirror(list_size=len(mirrors.top_list))
        if status != constant.OK:
            return None, constant.USER_INTERRUPT
        if maybe_key is None:
            return "Invalid mirror index", constant.INVALID_MIRROR_INDEX
        key = maybe_key - 1

    if args.list_only:
        return None, constant.OK

    new_mirror = mirrors.top_list[key]
    print(f"Selecting mirror {new_mirror} ...")
    if current_url == new_mirror:
        return (
            f"[{current_url}] is the currently used mirror.\n"
            f"{sources.skip_gen_msg}\n"
        ), constant.SKIPPED_FILE_GENERATION

    work_dir = os.getcwd()
    if work_dir == sources.DIRECTORY[0:-1]:
        query = (
            f"'{sources.DIRECTORY}' is the current directory.\n"
            f"Generating a new '{sources.LIST_FILE}' file will "
            "overwrite the current file.\n"
            "You should copy or backup '%(apt)s' before replacing it.\n"
            "Continue?\n[yes|no] "
        )
        status = yes_or_no(query=query)
        if status != constant.OK:
            return None, status

    new_mirror = mirrors.top_list[key]
    try:
        sources.generate_new_config(work_dir=work_dir, new_mirror=new_mirror)
    except apt.SourcesFileError as err:
        return f"Error generating new config file {err}", constant.NOK
    print(f"New config file saved to {sources.new_file_path}")

    return None, constant.OK


def _set_hostname_length(index: int, entry: dict[str, float | int | str]) -> int:
    hostname_len = len(f"{index}{entry['Host']}")
    entry["host_length"] = hostname_len
    return hostname_len


def main() -> int:
    try:
        msg, status = apt_select()
        if msg:
            sys.stderr.write(msg)
        return status
    except KeyboardInterrupt:
        sys.stderr.write("Aborting...\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
