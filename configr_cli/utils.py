import os
from pathlib import Path


def create_configr_token_file(dotenv_path=None):
    if not dotenv_path:
        home = os.environ.get("USERPROFILE") or os.environ.get("HOME")
        dotenv_path = os.path.join(home, ".configr.env")

    path = Path(dotenv_path)

    if path.exists():
        print(f"✅ Token file already exists at: {path}")
        return

    print("🔐 GitLab token required for configr-cli.")
    token = input(
        "Enter your GitLab Personal Access Token (stored in plain text): "
    ).strip()

    if not token:
        print("❌ No token entered. Aborting.")
        return

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"CONFIGR_GITLAB_TOKEN={token}\n")
        print(f"✅ Token file created at: {path}")
    except Exception as e:
        print(f"❌ Failed to create token file: {e}")
