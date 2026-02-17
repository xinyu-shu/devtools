#!/usr/bin/env python3
"""CLI for different things (Github PR)"""

import argparse
import sys

from pr import handle_pr_create


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Devtools")
    subparsers = parser.add_subparsers(dest="command")

    pr_parser = subparsers.add_parser("pr", help="PR-related commands")
    pr_subparsers = pr_parser.add_subparsers(dest="pr_command")

    create_parser = pr_subparsers.add_parser("create", help="Create a PR")
    create_parser.set_defaults(handler=handle_pr_create)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "handler"):
        parser.print_help()
        return 2

    return args.handler()


if __name__ == "__main__":
    sys.exit(main())
