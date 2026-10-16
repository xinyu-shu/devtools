#!/usr/bin/env python3
"""Synchronize locally built DSS artifacts to an existing remote DSS kit.

The tool intentionally does not build DSS or restart a remote service. It only
copies artifacts that the local DSS package build would consume.
"""

from __future__ import annotations

import argparse
import configparser
import os
import re
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = TOOL_DIR / "config.ini"
HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
# Share the resource list between preflight validation and the transfer plan.
RESOURCE_DIRECTORIES = (
    "container-exec",
    "code-envs/python",
    "llm/presets",
    "enterprise-asset-library",
)


@dataclass(frozen=True)
class Remote:
    host: str
    user: str
    port: int
    root: str


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def load_host(config: configparser.ConfigParser, config_path: Path) -> str:
    remote_config = config["remote"]
    host = remote_config.get("host", "").strip()
    host_file = remote_config.get("host_file", "").strip()
    if bool(host) == bool(host_file):
        fail("configure exactly one of remote.host or remote.host_file")
    if host_file:
        host_path = Path(host_file).expanduser()
        if not host_path.is_absolute():
            host_path = config_path.parent / host_path
        try:
            lines = host_path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            fail(f"could not read remote.host_file {host_path}: {error}")
        if len(lines) != 1 or not lines[0].strip():
            fail(f"remote.host_file must contain exactly one non-empty line: {host_path}")
        host = lines[0].strip()
    if not HOST_RE.fullmatch(host):
        fail("remote host must be a hostname or IP address")
    return host


def load_config(path: Path, workspace: str) -> Tuple[Remote, Path]:
    if not path.is_file():
        fail(f"configuration file not found: {path} (copy config.example.ini first)")
    config = configparser.ConfigParser()
    config.read(path)
    try:
        remote = Remote(
            host=load_host(config, path),
            user=config["remote"]["user"].strip(),
            port=config.getint("remote", "port"),
            root=config["remote"]["root"].strip(),
        )
        source = Path(config[f"workspace.{workspace}"]["path"]).expanduser()
    except (KeyError, ValueError, configparser.Error) as error:
        fail(f"invalid configuration: {error}")
    if not remote.user or not re.fullmatch(r"[A-Za-z0-9_.-]+", remote.user):
        fail("remote.user contains unsupported characters")
    if not 1 <= remote.port <= 65535:
        fail("remote.port must be between 1 and 65535")
    if not remote.root.startswith("/") or "\n" in remote.root:
        fail("remote.root must be an absolute path")
    return remote, source


def git_value(source: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source), *arguments], check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def inspect_source(source: Path, allow_dirty: bool) -> Tuple[str, int]:
    if not source.is_dir():
        fail(f"DSS workspace does not exist: {source}")
    if not (source / ".git").exists():
        fail(f"DSS workspace is not a Git checkout: {source}")
    try:
        revision = git_value(source, "rev-parse", "HEAD")
        dirty = bool(git_value(source, "status", "--porcelain"))
    except subprocess.CalledProcessError as error:
        fail(f"could not inspect DSS checkout: {error}")
    if dirty and not allow_dirty:
        fail("DSS workspace has uncommitted changes; use --allow-dirty to deploy it")
    dist = source / "dist"
    jars = list(dist.glob("*.jar")) if dist.is_dir() else []
    if not jars:
        fail(f"no JARs found in {dist}; build DSS locally first")
    required = [
        source / "src/main/python/dataiku",
        source / "src/main/python/dataikuapi",
        source / "dist/frontend",
        source / "lib",
        source / "packagers/studio/scripts",
        source / "packagers/dkuinstall",
    ]
    required.extend(source / "resources" / directory for directory in RESOURCE_DIRECTORIES)
    missing = [str(item) for item in required if not item.is_dir()]
    if missing:
        fail("missing locally built/source directories: " + ", ".join(missing))
    return revision, len(jars)


def ssh_command(remote: Remote) -> str:
    return f"ssh -p {remote.port} -o IdentitiesOnly=yes"


def destination(remote: Remote, suffix: str) -> str:
    return f"{remote.user}@{remote.host}:{remote.root.rstrip('/')}/{suffix.lstrip('/')}"


def run(command: List[str], dry_run: bool) -> None:
    display = " ".join(repr(part) if " " in part else part for part in command)
    print(f"+ {display}")
    if not dry_run:
        subprocess.run(command, check=True)


def rsync_command(source: Path, remote: Remote, target: str, *, delete: bool, extra: Optional[List[str]] = None) -> List[str]:
    command = [
        "rsync", "--archive", "--compress", "--no-owner", "--no-group", "--human-readable",
        "--itemize-changes", "--protect-args", "-e", ssh_command(remote),
    ]
    if delete:
        command.append("--delete-delay")
    if extra:
        command.extend(extra)
    command.extend([f"{source}/", destination(remote, target)])
    return command


def run_all(commands: List[List[str]], dry_run: bool, jobs: int) -> None:
    if dry_run:
        for command in commands:
            run(command, dry_run=True)
        return

    with ThreadPoolExecutor(max_workers=min(jobs, len(commands))) as executor:
        futures: List[Future[None]] = [
            executor.submit(run, command, False) for command in commands
        ]
        for future in as_completed(futures):
            future.result()


def synchronize(source: Path, remote: Remote, dry_run: bool, jobs: int) -> None:
    # These directories fully belong to the local checkout and can be mirrored.
    commands = [
        # The packager overlays lambda/src/main/python/dataiku/apinode here.
        # Excluding it also protects that remote-only subtree from --delete.
        rsync_command(source / "src/main/python/dataiku", remote, "python/dataiku", delete=True,
                      extra=["--exclude=/apinode/"]),
        rsync_command(source / "src/main/python/dataikuapi", remote, "python/dataikuapi", delete=True),
        rsync_command(source / "dist/frontend", remote, "frontend", delete=True),
        rsync_command(source / "lib", remote, "lib", delete=True),
    ]
    commands.extend(
        rsync_command(source / "resources" / directory, remote, f"resources/{directory}", delete=True)
        for directory in RESOURCE_DIRECTORIES
    )
    # Mirror only JARs: package dist/ may also contain generated .properties files.
    commands.append(rsync_command(source / "dist", remote, "dist", delete=True,
                                  extra=["--include=*/", "--include=*.jar", "--exclude=*"]))
    # scripts/ also contains packager-common files; do not delete unknown entries.
    commands.append(rsync_command(source / "packagers/studio/scripts", remote, "scripts", delete=False))
    commands.append(rsync_command(source / "packagers/dkuinstall", remote, "scripts/dkuinstall", delete=True,
                                  extra=["--include=*.py", "--exclude=*"]))
    run_all(commands, dry_run, jobs)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    argument_parser.add_argument("--workspace", choices=("default", "boom"), default="default")
    argument_parser.add_argument("--allow-dirty", action="store_true")
    subparsers = argument_parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="validate the local workspace and display its revision")
    sync_parser = subparsers.add_parser("sync", help="copy local artifacts to the configured remote kit")
    sync_parser.add_argument("--dry-run", action="store_true", help="print rsync commands without running them")
    sync_parser.add_argument("--yes", action="store_true", help="skip the interactive deployment confirmation")
    sync_parser.add_argument(
        "--jobs",
        type=positive_int,
        default=os.cpu_count() or 1,
        help="concurrent rsync jobs (default: number of local CPU cores)",
    )
    return argument_parser


def main() -> int:
    args = parser().parse_args()
    remote, source = load_config(args.config, args.workspace)
    revision, jar_count = inspect_source(source, args.allow_dirty)
    print(f"workspace: {source}\nrevision:  {revision}\nJARs:      {jar_count}")
    print(f"target:    {remote.user}@{remote.host}:{remote.root}")
    if args.command == "check":
        return 0
    print(f"parallelism: {args.jobs}")
    if not args.dry_run and not args.yes:
        answer = input("Deploy these artifacts to the target above? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled.")
            return 1
    try:
        synchronize(source, remote, args.dry_run, args.jobs)
    except subprocess.CalledProcessError as error:
        print(f"error: command failed with exit code {error.returncode}", file=sys.stderr)
        return error.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
