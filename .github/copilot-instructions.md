# Copilot Instructions for configr-cli

## Project Overview

**configr-cli** is a Python CLI tool that fetches shared configuration files (Makefiles, Dockerfiles, CI configs, etc.) from a centralized GitLab repository ("configr") and distributes them to team projects. Users authenticate with a GitLab Personal Access Token, then interactively browse and retrieve config files.

## Commands

### Dev Setup
```bash
uv sync
```

### Run the CLI locally
```bash
uv run configr --help
```

### Lint (Black via pre-commit)
```bash
pre-commit run --all-files
```

### Tests
```bash
pytest                              # full suite
pytest tests/test_cli.py -v        # single file
pytest tests/test_cli.py::test_name -v  # single test
```

> **Note:** Tests use Click's `CliRunner`. The test entry point is `cli` (not `main`) from `configr_cli.cli`.

### Docs
```bash
mkdocs build -d public
```

## Architecture

Four modules, strict separation of concerns:

| Module | Role |
|---|---|
| `configr_cli/cli.py` | Click CLI — defines all commands, handles user I/O |
| `configr_cli/gitlab.py` | GitLab API client — token resolution, HTTP, interactive prompts |
| `configr_cli/local.py` | Local filesystem browsing — same TUI as gitlab.py but reads from disk |
| `configr_cli/utils.py` | Token file initialization |

**Data flow for `configr fetch` (GitLab):**
1. Token resolved from `~/.configr.env` → `GITLAB_TOKEN` env var → `RuntimeError`
2. `fetch_manifest()` retrieves `manifest.json` from the configr repo via GitLab API
3. `browse_configs()` renders an interactive InquirerPy menu
4. `fetch_file()` retrieves base64-encoded file content from GitLab
5. User chooses: Print / Save / Copy to clipboard / Cancel

**Data flow for `configr start` (local):**
1. `CONFIGR_LOCAL_PATH` read from `~/.configr.env` (set via `configr init-local`)
2. `list_local_files()` walks the directory, matching files by `SUPPORTED_CONFIG_FILES`
3. `browse_local_configs()` renders the same InquirerPy menu
4. File content read directly from disk
5. User chooses: Print / Save / Copy to clipboard / Cancel

## Key Conventions

### CLI Commands (Click)
All commands attach to the `@click.group() def cli()` group in `cli.py`. Pattern:
```python
@cli.command()
@click.argument("remote_path", required=True)
@click.option("--ref", default="main", help="...")
def my_command(remote_path, ref):
    ...
```
Error output always uses `click.echo(f"Error: {e}", err=True)`.

### Token Resolution (always use this helper)
```python
token, api_url = get_token_and_api_url(token, api_url)
```
Priority: explicit arg → `~/.configr.env` (`CONFIGR_GITLAB_TOKEN`) → `GITLAB_TOKEN` env var → `RuntimeError`.

### GitLab API Requests
Always URL-encode project and file paths with `requests.utils.quote(..., safe="")`. Auth header: `{"PRIVATE-TOKEN": token}`. File content is base64-encoded in responses.

### Custom Exception
Raise `GitLabAPIError` (defined in `gitlab.py`) for all GitLab API failures — include HTTP status code and response text.

### Supported Config File Types
```python
SUPPORTED_CONFIG_FILES = (".yml", ".yaml", ".mk", ".sh", "Makefile", ".gitlab-ci.yml", "Dockerfile")
```

### Interactive Prompts
Use **InquirerPy** (`inquirer.select`, `inquirer.confirm`) for all interactive UX. Use `inquirer.confirm(..., default=False)` before any destructive file operation (overwrite check).

### User-Facing Output
Use emoji prefixes consistently: `✅` success, `❌` error/abort, `📥` fetching, `📄` print, `📋` clipboard, `🔐` token.

### Local Path Resolution (`local.py`)
`load_local_path()` reads `CONFIGR_LOCAL_PATH` from `~/.configr.env`. `save_local_path()` updates that key without touching others (e.g., `CONFIGR_GITLAB_TOKEN`). File discovery uses `_is_supported(filename)` which matches `SUPPORTED_CONFIG_FILES` — dot-prefixed entries are treated as extensions (`endswith`), bare names are exact matches.

### Default Project
```python
DEFAULT_PROJECT = "edgar-treischl/configr"  # in gitlab.py
```
Always pass `project` through as a parameter — don't hardcode elsewhere.
