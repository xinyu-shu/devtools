#!/usr/bin/env python3
"""CLI for different things (Github PR, GCP VM)"""

import argparse
import sys

from pr import handle_pr_create
from gcp import handle_gcp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Devtools")
    subparsers = parser.add_subparsers(dest="command")

    pr_parser = subparsers.add_parser("pr", help="PR-related commands")
    pr_subparsers = pr_parser.add_subparsers(dest="pr_command")

    create_parser = pr_subparsers.add_parser("create", help="Create a PR")
    create_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Add --dry-run to the gh pr create command",
    )
    create_parser.set_defaults(handler=handle_pr_create)

    gcp_parser = subparsers.add_parser("gcp", help="GCP VM commands")
    gcp_subparsers = gcp_parser.add_subparsers(dest="gcp_command")

    vm_parser = gcp_subparsers.add_parser("vm", help="Create a GCP VM")
    vm_parser.add_argument("--name", type=str, default=None, help="Instance name")
    vm_parser.add_argument("--project", type=str, default=None, help="GCP project ID")
    vm_parser.add_argument("--zone", type=str, default=None, help="VM zone")
    vm_parser.add_argument("--machine", type=str, default=None, help="Machine type")
    vm_parser.add_argument("--image", type=str, default=None, help="Image family")
    vm_parser.add_argument("--disk", type=str, default=None, help="Disk size in GB")
    vm_parser.add_argument(
        "--dry-run", action="store_true",
        help="Show command without executing",
    )
    vm_parser.set_defaults(handler=handle_gcp)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "handler"):
        parser.print_help()
        return 2

    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
