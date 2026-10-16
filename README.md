# Devtools

This repository contains two tools:

| Directory | Purpose | Documentation |
| --- | --- | --- |
| `github-helper/` | Interactive GitHub PR helpers and existing GCP utilities | [GitHub helper](github-helper/README.md) |
| `dss-sync/` | Sync locally built DSS artifacts to an existing remote DSS kit | [DSS sync](dss-sync/README.md) |

Both tools use Python 3's standard library. The GitHub helper also uses `gh`;
DSS sync uses `git`, `ssh`, and `rsync`.

Run the GitHub helper from the repository where you want to create a PR:

```sh
python3 /path/to/devtools/github-helper/main.py pr create
```

Run DSS sync using its existing entry point and configuration:

```sh
python3 /path/to/devtools/dss-sync/sync.py --workspace default check
python3 /path/to/devtools/dss-sync/sync.py --workspace default sync --dry-run
```

The former root-level helper scripts now live in `github-helper/`. Update any
aliases or scripts that invoked `devtools/main.py` to use
`devtools/github-helper/main.py`.
