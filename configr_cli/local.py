import os
from pathlib import Path

from dotenv import dotenv_values

from configr_cli.gitlab import SUPPORTED_CONFIG_FILES


def load_local_path(dotenv_path="~/.configr.env"):
    path = Path(dotenv_path).expanduser()
    if not path.exists():
        return None
    config = dotenv_values(path)
    return config.get("CONFIGR_LOCAL_PATH")


def save_local_path(local_path: str, dotenv_path="~/.configr.env"):
    """Write/update CONFIGR_LOCAL_PATH in ~/.configr.env without touching other keys."""
    env_file = Path(dotenv_path).expanduser()
    env_file.parent.mkdir(parents=True, exist_ok=True)

    existing_lines = env_file.read_text().splitlines() if env_file.exists() else []
    updated = False
    new_lines = []
    for line in existing_lines:
        if line.startswith("CONFIGR_LOCAL_PATH="):
            new_lines.append(f"CONFIGR_LOCAL_PATH={local_path}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"CONFIGR_LOCAL_PATH={local_path}")

    env_file.write_text("\n".join(new_lines) + "\n")


def _is_supported(filename: str) -> bool:
    for pattern in SUPPORTED_CONFIG_FILES:
        if pattern.startswith("."):
            if filename.endswith(pattern):
                return True
        else:
            if filename == pattern:
                return True
    return False


def list_local_files(local_path: str, filter_path: str = None) -> list[str]:
    base = Path(local_path)
    files = []
    for root, dirs, filenames in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for filename in filenames:
            if _is_supported(filename):
                rel = Path(root).relative_to(base) / filename
                files.append(str(rel))

    if filter_path:
        files = [f for f in files if f.startswith(filter_path)]

    return sorted(files)


def browse_local_configs(local_path: str, filter_path: str = None):
    from configr_cli.tui import browse_local_configs_tui

    browse_local_configs_tui(local_path, filter_path)
