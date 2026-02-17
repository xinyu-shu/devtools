import shlex
import subprocess

from settings import get_settings


def prompt_with_default(question: str, default: str) -> str:
    prompt = f"{question} [{default}]: " if default else f"{question}: "
    response = input(prompt).strip()
    return response if response else default


def build_pr_create_command(dry_run: bool = False) -> str:
    settings = get_settings()
    result = "gh pr create -a @me"

    use_fill_first = prompt_with_default(
        "Use the first commit as the PR title and description?",
        "y",
    ).lower()
    if use_fill_first == "y":
        result += " --fill-first"
    else:
        raise NotImplementedError("Only 'fill-first' (using first commit title and description) option is currently implemented.")
    if dry_run:
        result += " --dry-run"

    default_branch = settings.get("default-branch", "")
    base_branch = prompt_with_default("Base branch", default_branch)
    if base_branch:
        result += f" -B {shlex.quote(base_branch)}"

    default_labels = settings.get("labels", "")
    labels_input = prompt_with_default("Labels", default_labels)
    labels = [label.strip() for label in labels_input.split(",") if label.strip()]
    for label in labels:
        result += f" -l {shlex.quote(label)}"

    default_milestone = settings.get("milestone", "")
    milestone = prompt_with_default("Milestone", default_milestone)
    if milestone:
        result += f" -m {milestone}"

    print("Users - use the indexes to select them as PR reviewers")
    for i, reviewer in enumerate(settings["reviewers"]):
        print(f"- {i+1}: {reviewer.name} ({reviewer.username})")
        
    reviewers = prompt_with_default("Reviewers", "")
    for reviewer in reviewers.strip().split(","):
        if reviewer.isnumeric():
            i = int(reviewer)
            if 0 < i <= len(settings["reviewers"]):
                result += f" -r {settings['reviewers'][i-1].username}"
        elif reviewer.strip():
            result += f" -r {reviewer}"

    return result


def handle_pr_create(args) -> int:
    result = build_pr_create_command(dry_run=args.dry_run)
    confirmation = prompt_with_default(f"Run this command?\n{result}", "y").lower()

    if confirmation == "y":
        completed = subprocess.run(shlex.split(result), check=False)
        return completed.returncode

    print("Cancelled.")
    return 1
