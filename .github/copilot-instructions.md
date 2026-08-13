# Repository instructions

## Build, test, lint, and docs

- `Makefile` is the primary entry point for common tasks; run `make help` to
  list its targets. The commands wrap uv and its committed lockfile.
- Install the locked environment with `make install`; use `make sync` after
  intentionally changing dependencies. The default `dev` dependency group
  installs the test, formatting, build, and documentation tools.
- Build the distributable package with `make build`.
- Run the CLI from the environment with `make cli` (the console
  entry point is `configr_cli.cli:cli`).
- Tests use pytest conventions. Run the suite with `make test`, or one test
  with `make test TEST=tests/test_cli.py::test_greeting`. The sole test is
  stale: it imports a nonexistent `configr_cli.cli.main` and describes a
  removed greeting command. Repair it before using the suite as a regression
  baseline.
- Formatting is enforced by the Black hook in `.pre-commit-config.yaml`; run
  `make lint`.
- Build the documentation with `make docs`.

## Architecture

- `configr_cli.cli` is the Click command layer. It exposes two related flows:
  remote GitLab commands (`get`, `show`, and `fetch`) and local browsing
  commands (`init-local` and `start`). Keep orchestration and user-facing Click
  output here; data access and UI behavior live in their respective modules.
- `configr_cli.gitlab` owns remote access. The remote repository's
  `manifest.json` is the authoritative file list, while individual files are
  fetched through GitLab's repository-files API and base64-decoded. Token
  resolution is: explicit argument, `CONFIGR_GITLAB_TOKEN` in
  `~/.configr.env`, then `GITLAB_TOKEN` in the process environment. The default
  API is the LRZ GitLab instance.
- `configr_cli.local` owns local configuration and discovery.
  `CONFIGR_LOCAL_PATH` is stored in the same `~/.configr.env` file without
  replacing other keys. Local browsing lazily imports `configr_cli.tui` to
  avoid a module cycle because the TUI imports local discovery for fallback.
- `configr_cli.tui` is a Textual two-panel browser. It prefers a curated local
  `manifest.json`; without one, it falls back to recursive discovery through
  `local.list_local_files`. The app returns `(relative_path, action)` when it
  exits, and printing, saving, or copying is performed afterward.
- MkDocs sources are under `docs/`. Both `.gitlab-ci.yml` and
  `.github/workflows/docs.yml` build and publish the documentation from `main`;
  keep both deployment paths working.

## Repository-specific conventions

- Keep supported filename rules centralized in
  `gitlab.SUPPORTED_CONFIG_FILES`; local discovery reuses that tuple. Entries
  beginning with `.` are treated as suffixes, while entries such as `Makefile`
  and `Dockerfile` are exact filenames.
- Preserve paths relative to the configured repository throughout discovery
  and the TUI. The UI groups only by the first path component and represents
  root-level files with the `_ROOT_FOLDER` sentinel.
- Textual list items use indexed IDs (`folder_<n>` and `file_<n>`), and event
  handlers map those indices back to `_folders` and `_file_list`. Keep those
  collections and widget IDs synchronized when changing navigation.
- Both local and remote save actions flatten the selected path to its basename
  and prompt before overwriting. The noninteractive `get --save` flow instead
  supports `--output` and `--force`.
- `save_local_path` deliberately updates only `CONFIGR_LOCAL_PATH` and retains
  the token and unknown lines in `~/.configr.env`; do not rewrite the file from
  a newly generated dotenv mapping.
- Keep command examples and setup behavior aligned across `README.md` and
  `docs/getstarted.md`.
