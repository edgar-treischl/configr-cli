import os
from pathlib import Path
import json
import base64
from InquirerPy import inquirer
import requests
import pyperclip
from dotenv import dotenv_values


# configr_cli/gitlab.py

SUPPORTED_CONFIG_FILES = (
    ".yml",
    ".yaml",
    ".mk",
     ".sh",
    "Makefile",
    ".gitlab-ci.yml",
    "Dockerfile",
)


class GitLabAPIError(Exception):
    """Custom exception for GitLab API errors."""

    pass


def load_configr_token(dotenv_path="~/.configr.env"):
    path = Path(dotenv_path).expanduser()
    if not path.exists():
        return None
    config = dotenv_values(path)
    return config.get("CONFIGR_GITLAB_TOKEN")


def get_token_and_api_url(token=None, api_url=None):
    """
    Resolve the GitLab token and API URL.

    Priority order:
      1. Directly passed token
      2. Token from ~/.configr.env (via load_configr_token)
      3. Environment variable: GITLAB_TOKEN

    Raises:
        RuntimeError: If no token is found.

    Returns:
        Tuple[str, str]: (token, api_url)
    """
    if not token:
        token = load_configr_token()

    if not token:
        token = os.getenv("GITLAB_TOKEN")

    if not token:
        raise RuntimeError(
            "❌ No GitLab token found.\n\n"
            "Checked:\n"
            "  - ~/.configr.env (CONFIGR_GITLAB_TOKEN)\n"
            "  - Environment variable: GITLAB_TOKEN\n\n"
            "👉 Run `configr init-token` to set up your credentials."
        )

    api_url = api_url or "https://gitlab.lrz.de/api/v4"

    return token, api_url


def fetch_manifest(project, ref="main", token=None, api_url=None):
    """
    Fetch the manifest file from the configr repo.
    """
    manifest_path = "manifest.json"  # or whatever path you choose
    content = fetch_file(
        project, filepath=manifest_path, ref=ref, token=token, api_url=api_url
    )
    return json.loads(content)


def fetch_file(project, filepath, ref="main", token=None, api_url=None):
    token, api_url = get_token_and_api_url(token, api_url)
    encoded_project = requests.utils.quote(project, safe="")
    encoded_file = requests.utils.quote(filepath, safe="")
    url = f"{api_url}/projects/{encoded_project}/repository/files/{encoded_file}?ref={ref}"

    # headers = {"Authorization": f"Bearer {token}"}
    headers = {"PRIVATE-TOKEN": token}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise GitLabAPIError(
            f"Failed to fetch file '{filepath}' from project '{project}' "
            f"(status {response.status_code}): {response.text}"
        )

    data = response.json()
    return base64.b64decode(data["content"]).decode("utf-8")


def list_files(project, ref="main", token=None, api_url=None):
    # Fetch the manifest file from GitLab repo
    try:
        files = fetch_manifest(project, ref=ref, token=token, api_url=api_url)
    except GitLabAPIError as e:
        # handle error or fallback if needed
        raise e

    files_sorted = sorted(files)
    return files_sorted


def browse_configs(project: str, ref: str, filter_path: str = None):
    files = list_files(project=project, ref=ref)

    if filter_path:
        files = [f for f in files if f.startswith(filter_path + "/")]

    if not files:
        print("No config files available.")
        return
    choices = files + ["❌ Cancel"]

    selected = inquirer.select(
        message="Select a config file to fetch:",
        choices=choices,
        pointer=">",
        default=files[0],
        cycle=True,
    ).execute()

    if selected == "❌ Cancel":
        print("❌ Operation cancelled.")
        return

    print(f"\n📥 Fetching '{selected}' from {project}@{ref}...\n")
    content = fetch_file(project=project, filepath=selected, ref=ref)

    action = inquirer.select(
        message="What do you want to do with the file?",
        choices=[
            "Print to terminal",
            "Save to current directory",
            "Copy to clipboard",
            "❌ Cancel",
        ],
        default="Print to terminal",
    ).execute()

    if action == "Cancel":
        print("❌ Operation cancelled.")
        return

    elif action == "Print to terminal":
        print(f"\n📄 Contents of '{selected}':\n")
        print(content)

    elif action == "Save to current directory":
        filename_only = os.path.basename(selected)

        if os.path.exists(filename_only):
            overwrite = inquirer.confirm(
                message=f"⚠️ '{filename_only}' already exists. Overwrite?",
                default=False,
            ).execute()

            if not overwrite:
                print("❌ Aborted. File not overwritten.")
                return

        with open(filename_only, "w") as f:
            f.write(content)

        print(f"✅ '{selected}' fetched and saved locally as '{filename_only}'.")

    elif action == "Copy to clipboard":
        pyperclip.copy(content)
        print("📋 File contents copied to clipboard.")
