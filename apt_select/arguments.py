#!/usr/bin/env python
"""Process command line options for apt-select"""

from argparse import ArgumentParser, RawTextHelpFormatter

DEFAULT_COUNTRY = 'US'
DEFAULT_NUMBER = 1
STATUS_ARGS = (
    "up-to-date",
    "one-day-behind",
    "two-days-behind",
    "one-week-behind",
    "unknown"
)
SKIPPED_FILE_GENERATION = 4

def get_args():
    """Get parsed command line arguments"""
    parser = ArgumentParser(
        description=(
            "Find the fastest Ubuntu apt mirrors.\n"
            "Generate new sources.list file."
        ),
        epilog="The exit code is 0 on success, 1 on error, and %d if "\
        "sources.list already has the chosen\n"\
        "mirror and a new one was not generated." % SKIPPED_FILE_GENERATION,
        formatter_class=RawTextHelpFormatter
    )
    parser.add_argument(
        '-C',
        '--country',
        nargs='?',
        type=str,
        help=(
            "specify a country to test its list of mirrors\n"
            "used to match country list file names found at mirrors.ubuntu.com\n"
            "COUNTRY should follow ISO 3166-1 alpha-2 format\n"
            "default: %s" % DEFAULT_COUNTRY
        ),
        metavar='COUNTRY'
    )
    parser.add_argument(
        '-t',
        '--top-number',
        nargs='?',
        type=int,
        help=(
            "specify number of mirrors to return\n"
            "default: 1\n"
        ),
        const=DEFAULT_NUMBER,
        default=DEFAULT_NUMBER,
        metavar='NUMBER'
    )
    test_group = parser.add_mutually_exclusive_group(required=False)
    test_group.add_argument(
        '-m',
        '--min-status',
        nargs='?',
        choices=STATUS_ARGS,
        type=str,
        help=(
            "return mirrors with minimum status\n"
            "choices:\n"
            "   %(up)s\n"
            "   %(day)s\n"
            "   %(two_day)s\n"
            "   %(week)s\n"
            "   %(unknown)s\n"
            "default: %(up)s\n" % {
                'up': STATUS_ARGS[0],
                'day': STATUS_ARGS[1],
                'two_day': STATUS_ARGS[2],
                'week': STATUS_ARGS[3],
                'unknown': STATUS_ARGS[4]
            }
        ),
        const=STATUS_ARGS[0],
        default=STATUS_ARGS[0],
        metavar='STATUS'
    )
    test_group.add_argument(
        '-p',
        '--ping-only',
        action='store_true',
        help=(
            "rank mirror(s) by latency only, disregard status(es)\n"
            "cannot be used with -m/--min-status\n"
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
            "cannot be used with -c/--choose\n"
        ),
        default=False
    )

    return parser

if __name__ == '__main__':
    get_args().parse_args()
