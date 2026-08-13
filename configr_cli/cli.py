import os
import click
from configr_cli.gitlab import fetch_file, list_files, GitLabAPIError, browse_configs
from configr_cli.local import browse_local_configs, load_local_path, save_local_path
from configr_cli.utils import create_configr_token_file

from getpass import getpass
from pathlib import Path


DEFAULT_PROJECT = "edgar-treischl/configr"


@click.group()
def cli():
    """configr-cli: Fetch shared config files from the configr repo."""
    pass


@cli.command()
@click.argument("remote_path", required=True)
@click.argument("project", required=False)
@click.option("--ref", default="main", help="Git branch or tag (default: main)")
@click.option("--save", is_flag=True, help="Save the file locally instead of printing")
@click.option("--output", default=None, help="Write file to this path.")
@click.option("--force", is_flag=True, help="Overwrite without prompting.")
def get(remote_path, project, ref, save, output, force):
    """Fetch a file from the GitLab repo, print or save it."""

    if not project:
        project = DEFAULT_PROJECT

    try:
        content = fetch_file(project=project, filepath=remote_path, ref=ref)

        if save:
            filename = os.path.abspath(output or os.path.basename(remote_path))

            if os.path.exists(filename) and not force:
                overwrite = click.confirm(
                    f"File '{filename}' already exists. Overwrite?", default=False
                )
                if not overwrite:
                    click.echo("Aborted: file not overwritten.")
                    return

            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            click.echo(f"File saved as {filename}")
        else:
            click.echo(content)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option(
    "--project",
    default=DEFAULT_PROJECT,
    show_default=True,
    help="GitLab project path (default: hardcoded default)",
)
@click.option("--ref", default="main", help="Git branch or tag (default: main)")
def show(project, ref):
    """List all available config files."""
    if not project:
        project = DEFAULT_PROJECT  # fallback to hardcoded default

    try:
        files = list_files(project=project, ref=ref)
        if not files:
            click.echo("No configuration files found.")
        else:
            click.echo("Available configuration files:\n")
            for f in files:
                click.echo(f"  - {f}")
    except GitLabAPIError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option(
    "--project",
    default=DEFAULT_PROJECT,
    show_default=True,
    help="GitLab project path (default: hardcoded default)",
)
@click.option("--ref", default="main", help="Git branch or tag (default: main)")
@click.argument("filter_path", required=False)
def fetch(project, ref, filter_path):
    """Interactively browse and fetch config files."""
    if not project:
        project = DEFAULT_PROJECT

    try:
        browse_configs(project=project, ref=ref, filter_path=filter_path)
    except GitLabAPIError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command("init-token")
def init_token():
    """
    Initialize GitLab token by creating ~/.configr.env with CONFIGR_GITLAB_TOKEN.
    """
    path = Path("~/.configr.env").expanduser()

    if path.exists():
        click.echo(f"✅ Token file already exists at: {path}")
        return

    click.echo("🔐 GitLab token required for configr-cli.")
    token = getpass("Enter your GitLab Personal Access Token (input hidden): ").strip()

    if not token:
        click.echo("❌ No token entered. Aborting.")
        return

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(f"CONFIGR_GITLAB_TOKEN={token}\n")
        click.echo(f"✅ Token file created at: {path}")
    except Exception as e:
        click.echo(f"❌ Failed to create token file: {e}")


@cli.command("init-local")
@click.argument("local_path", required=False)
def init_local(local_path):
    """Save the path to a local configr snippet base for use with 'configr start'."""
    if not local_path:
        local_path = click.prompt(
            "📁 Enter the path to your local configr repository"
        ).strip()

    resolved = Path(local_path).expanduser().resolve()

    if not resolved.is_dir():
        click.echo(f"❌ Directory not found: {resolved}")
        return

    try:
        save_local_path(str(resolved))
        click.echo(f"✅ Local path saved: {resolved}")
        click.echo("👉 Run `configr start` to browse files from this location.")
    except Exception as e:
        click.echo(f"❌ Failed to save local path: {e}", err=True)


@cli.command()
@click.argument("filter_path", required=False)
def start(filter_path):
    """Interactively browse and fetch config files from local storage."""
    local_path = load_local_path()

    if not local_path:
        click.echo(
            "❌ No local path configured.\n"
            "👉 Run `configr init-local <path>` to set one up."
        )
        return

    resolved = Path(local_path).expanduser().resolve()

    if not resolved.is_dir():
        click.echo(
            f"❌ Configured local path not found: {resolved}\n"
            "👉 Run `configr init-local <path>` to update it."
        )
        return

    click.echo(f"📁 Searching for config files in: {resolved}\n")

    try:
        browse_local_configs(str(resolved), filter_path=filter_path)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    cli()
