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

`dist/frontend` is used rather than the raw `src/main/platypus` source tree, matching the normal DSS package export. Fully owned artifact directories, including LLM presets and the complete Enterprise Asset Library required by the backend JAR, are mirrored with delayed deletion; only JARs are removed from `dist/` so generated non-JAR package files are preserved. `scripts/` is additive because it also contains files not owned by `packagers/studio/scripts`.

The remote root must already be the correct compatible DSS kit. The tool prints the local Git revision but cannot prove the remote kit's base revision. For an atomic deployment, the remote setup needs a versioned release directory, an activation symlink, and service lifecycle commands; those depend on the remote layout and are intentionally not guessed here.

## Starter-template fix and source validation

The sync includes `resources/enterprise-asset-library/` in full, matching
`packagers/studio/make-studio-package.sh`. This includes notebook, web-app and
agent starter templates, prompts and email templates. The backend loads all
three starter-template families together, so a missing
`builtin-starter-code-templates/code_agent/python/` also prevents the notebook
creation form from listing templates.

`check` and `sync` now validate all transferred resource and script directories
before any rsync starts. The resource copy list is shared with validation.
`python/dataiku/apinode/` is excluded from the parent mirror so its separately
packaged files survive `--delete`; this exclusion preserves it but does not
update it.

Local regression checks (no SSH, deployment or containers):

```sh
python3 -B -m unittest discover -s dss-sync -p 'test_*.py' -v
```

Run that command from the devtools repository root. Use the documented
`sync --dry-run` command to review a configured transfer plan before deploying.

## Package-copy audit (16 October 2026)

Compared with the current local DSS workspace's
`packagers/studio/make-studio-package.sh`. An omitted path below means the sync
script does not refresh it; it does **not** establish that it is absent on the
remote kit. These remaining paths were identified, not added to this fix.
The tool still assumes a compatible, already installed kit.

| Package input / target | Remaining gap |
| --- | --- |
| `resources/enterprise-asset-library` | Fixed: the entire directory is now mirrored and validated. |
| `resources/jupyter` | Omitted, including `nbconvert-templates` used for notebook exports. |
| `resources/code-envs` | Only `python` is synced; `r` and `conda-support` are omitted. |
| `resources/llm` | Only `presets` is synced. In the audited workspace it is the only child, so there is no current content gap; future sibling directories would be omitted. |
| Other directly copied resources | Omitted: `R`, `api-deployer`, `apinode`, `article-templates`, `cobuild`, `code-studios`, `cuda`, `data-lineage`, `databricks`, `docgen`, `docportal`, `eurorates`, `govern`, `graphics-export`, `holidays.db`, `i18n`, `integration`, `logging`, `migration`, `navigation`, `nginx`, `nlp`, `notifications`, `plugins-list.json`, `publicdata`, `python-samples`, `report-templates`, `saved-models`, `scenarios`, `security`, `spark`, `themes`, `tutorials`, `weekends.db`. Together with omitted `jupyter`, 35 of the packager's 39 unique direct resource-copy entries are wholly omitted; `code-envs` is partially covered. |
| `resources/builtin-python-env/{container-images,dss-server}` | Both requirement-resource directories are omitted. Copying them would update build specifications, not run containers or update installed environments. |
| `src/main/python/*` → `python/` | Only `dataiku` and `dataikuapi` are synced. Omitted packages: `ai_code_assistant`, `dataikuscoring`, `dataikusecurity`, `deploymentsupport`. The packager also copies the `dataikuapi-setup` directory and loose files such as `backend-main-python.iml`. |
| `lambda/src/main/python/dataiku/apinode` → `python/dataiku/apinode` | Omitted overlay. This fix protects the remote copy from parent deletion, but does not refresh it. |
| `gh/server/backend/src/main/python/govern` → `python/govern` | Omitted Govern Python package. |
| `packagers/common/scripts` → `scripts/` | Common `.sh`/`.py` launchers and the `install/` overlay are omitted. The packager selects `.ps1`/`.cmd` instead of `.sh` on Windows. The current studio-script copy is additive, so existing common scripts are preserved. |
| `packagers/dkuinstall` → `scripts/dkuinstall` | Only top-level `.py` files are synced; `__init__.py` makes it through, but the packager copies the full tree. Audit non-Python data or future subdirectories before broadening this filter. |
| `src/main/java/*.properties` → `dist/` | Logging files `apinode-default-log4j.properties`, `log-jul.properties`, `log4j.properties` are omitted. The JAR filter preserves existing remote properties but leaves them stale. |
| `dist/govern-frontend`, `dist/R`, `stories` | Entirely omitted. R's public downloadable package is also built/exposed separately. |
| `jupyter-integration` → `jupyter-integration/` | The current packager copies server-integration Python code, static files, templates and runtime metadata, and builds a platform wheelhouse. None is synced. Adding this can affect the new-runtime versus legacy-fork test baseline, and Linux runtime wheels must be built for Linux rather than copied from a macOS build. |
| `plugins/{k8s-metrics-utils,builtin-macros,colorbrewer-palettes,local-r-dev-setup,code-studio-blocks,project-standards,default-samples}` → `resources/plugins/` | Builtin plugin copies are omitted. |
| Root installer and generated package metadata | `installer.sh` (or Windows installers), `dss-arch.txt`, `requirements.json` for launcher builds, `dss-version.json` and `dss-tools-version.json` are not refreshed. Do not copy macOS platform declarations over a Linux kit. |
| Downloaded/generated package outputs | Legacy Jupyter recovery bundle, nbextensions, Toree, Python runtime archives, virtualenv, native tools/PDFium, GeoIP, downloaded tutorial archives, builtin snippets, notices and `public/packages` client/scoring/R archives are not rebuilt or synced. They depend on a full platform-appropriate package build. Geoadmin/geozip and Hadoop/Spark standalone archives are separate package outputs. |

Additional packaging differences: the sync mirrors all of local `lib/`, while
the packager selects runtime subtrees; this can transfer build-only libraries.
The existing transport flags require rsync 3.x with `--protect-args`; macOS builtin rsync rejects that option, so ensure a compatible rsync is on `PATH` (on both ends for remote argument protection).
The packager dereferences `dist/*.jar` symlinks (`cp -L`), while rsync currently
preserves them. No JAR symlinks exist in the audited local `dist/`, but a future
build using absolute symlinks could produce broken remote links.

For complete package parity, build a kit for the remote platform and deploy its
contents. This selective development sync is not a substitute for that build.
