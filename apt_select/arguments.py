#!/usr/bin/env python
"""Process command line options for apt-select"""

from argparse import ArgumentParser, RawTextHelpFormatter


def get_args():
    """Get parsed command line arguments"""
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
        nargs='?',
        type=int,
        help=(
            "specify number of mirrors to return\n"
            "default: 1\n"
        ),
        const=1,
        default=1,
        metavar='NUMBER'
    )
    status_args = (
        "up-to-date",
        "one-day-behind",
        "two-days-behind",
        "one-week-behind",
        "unknown"
    )
    test_group = parser.add_mutually_exclusive_group(required=False)
    test_group.add_argument(
        '-m',
        '--min-status',
        nargs='?',
        choices=status_args,
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
                'up': status_args[0],
                'day': status_args[1],
                'two_day': status_args[2],
                'week': status_args[3],
                'unknown': status_args[4]
            }
        ),
        const=status_args[0],
        default=status_args[0],
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
