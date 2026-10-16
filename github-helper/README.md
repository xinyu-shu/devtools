# GitHub helper

Interactive helpers for creating pull requests with the GitHub CLI. The
existing GCP VM and DSS setup commands are also kept in this CLI.

Requires Python 3 and an authenticated `gh` CLI (`gh auth login`). Run commands
from the Git checkout where you want to open the pull request:

```sh
python3 /path/to/devtools/github-helper/main.py pr create
python3 /path/to/devtools/github-helper/main.py pr create --dry-run
```

The helper prompts for the base branch, labels, milestone, and reviewers, then
asks for confirmation before running `gh pr create`. `--dry-run` passes through
to the GitHub CLI.

Edit `settings.txt` beside the helper scripts to change the defaults. Settings
are resolved relative to the scripts, independently of the working directory.

## GCP utilities

The VM command requires the `gcloud` CLI. It reads the `default-gcp-*` entries
from the same `settings.txt` and prompts for any missing values:

```sh
python3 /path/to/devtools/github-helper/main.py gcp vm --dry-run
python3 /path/to/devtools/github-helper/main.py gcp vm
python3 /path/to/devtools/github-helper/main.py gcp dss-conf
```

`gcp dss-conf` is the existing setup stub: it prints the DSS download URL and
attempts to create a `dss` directory in the working directory. It does not
install DSS or configure artifact synchronization.
