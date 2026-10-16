# DSS artifact sync

This tool copies locally built DSS artifacts to an **existing** remote DSS-kit directory. It does not build DSS remotely, start or stop DSS, or create a remote release directory.

## Setup

```sh
cd /Users/xinyushu/repos/devtools/dss-sync
cp config.example.ini config.ini
chmod +x sync.py
./sync.py --workspace default check
```

Edit `config.ini` for the intended remote kit and workspaces. Keep it local: it is intentionally ignored by Git.

`public_ip.txt` is the single source of truth for the VM address. It contains
exactly one hostname or IP address, and is used by both the sync tool and the
tunnel command:

```sh
ssh -L 23200:localhost:23200 xinyu.shu@$(cat /Users/xinyushu/repos/devtools/dss-sync/public_ip.txt)
```

When the VM address changes, update only `public_ip.txt`.

## Use

```sh
./sync.py --workspace default check
./sync.py --workspace default sync --dry-run
./sync.py --workspace default sync
./sync.py --workspace default sync --jobs 4
```

The tool refuses a dirty workspace by default. Pass `--allow-dirty` only when the uncommitted changes are deliberately part of the deployment.

Independent artifact directories are synchronized in parallel. By default, the
number of concurrent `rsync` jobs is the number of CPU cores on the machine
running the script; use `--jobs N` to override it.

## Scope and safety

`dist/frontend` is used rather than the raw `src/main/platypus` source tree, matching the normal DSS package export. Fully owned artifact directories, including LLM presets required by the backend JAR, are mirrored with delayed deletion; only JARs are removed from `dist/` so generated non-JAR package files are preserved. `scripts/` is additive because it also contains files not owned by `packagers/studio/scripts`.

The remote root must already be the correct compatible DSS kit. The tool prints the local Git revision but cannot prove the remote kit's base revision. For an atomic deployment, the remote setup needs a versioned release directory, an activation symlink, and service lifecycle commands; those depend on the remote layout and are intentionally not guessed here.
