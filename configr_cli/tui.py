"""Two-panel TUI for browsing local config files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

import pyperclip
from InquirerPy import inquirer
from rich.syntax import Syntax
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static


_LANG_MAP = {
    ".py": "python",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".sh": "bash",
    ".r": "r",
    ".toml": "toml",
    ".json": "json",
    ".md": "markdown",
}

_ROOT_FOLDER = "(root)"


def _detect_language(filepath: Path) -> str:
    """Map a file path to a Pygments language identifier for syntax highlighting."""
    name = filepath.name
    suffix = filepath.suffix.lower()
    if name == "Makefile" or suffix == ".mk":
        return "makefile"
    if name == "Dockerfile":
        return "docker"
    return _LANG_MAP.get(suffix, "text")


def _extract_folders(files: List[str]) -> List[str]:
    """Return sorted unique top-level folder names; root-level files go into _ROOT_FOLDER."""
    folders: list[str] = []
    has_root = False
    for f in files:
        parts = Path(f).parts
        if len(parts) > 1:
            folder = parts[0]
            if folder not in folders:
                folders.append(folder)
        else:
            has_root = True
    folders.sort()
    if has_root:
        folders.insert(0, _ROOT_FOLDER)
    return folders


def _files_for_folder(files: List[str], folder: str) -> List[str]:
    if folder == _ROOT_FOLDER:
        return [f for f in files if len(Path(f).parts) == 1]
    return [f for f in files if Path(f).parts[0] == folder]


def load_local_manifest(local_path: str) -> Optional[List[str]]:
    """Read manifest.json from the local configr repo root, return list of paths."""
    manifest = Path(local_path) / "manifest.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return None


class FilePreview(Static):
    """Displays syntax-highlighted file contents in the right panel."""

    def show_file(self, filepath: Optional[Path]) -> None:
        if filepath is None:
            self.update("[dim]Select a file to preview it here.[/dim]")
            return
        try:
            content = filepath.read_text(encoding="utf-8")
            lang = _detect_language(filepath)
            self.update(Syntax(content, lang, theme="monokai", line_numbers=True))
        except Exception as exc:
            self.update(f"[red]Could not read file: {exc}[/red]")


class ConfigrBrowserApp(App):
    """
    Two-panel TUI:
      Left  – folders → files → action buttons (always visible)
      Right – live syntax-highlighted file preview
    """

    TITLE = "configr start"
    SUB_TITLE = "Browse your config files"

    CSS = """
    Screen {
        background: $background;
    }

    /* ── Outer layout ── */
    #main-container {
        height: 1fr;
    }

    /* ── Left panel ── */
    #left-panel {
        width: 34;
        background: $surface;
        border-right: vkey $primary-darken-3;
    }

    /* Section heading chips */
    .section-head {
        background: $primary-darken-3;
        color: $text-muted;
        padding: 0 2;
        text-style: bold;
        width: 100%;
        height: 1;
    }

    #folder-list {
        height: auto;
        max-height: 8;
        background: $surface;
        padding: 0 1;
        border: none;
    }

    #folder-list > ListItem {
        padding: 0 1;
        background: transparent;
    }

    #folder-list > ListItem:hover {
        background: $primary-darken-2;
    }

    #folder-list > ListItem.--highlight {
        background: $primary-darken-1;
    }

    #folder-list > ListItem.selected {
        background: $accent-darken-1;
        color: $text;
        text-style: bold;
    }

    #files-list {
        height: 1fr;
        background: $surface;
        padding: 0 1;
        border: none;
    }

    #files-list > ListItem {
        padding: 0 1;
        background: transparent;
    }

    #files-list > ListItem:hover {
        background: $primary-darken-2;
    }

    #files-list > ListItem.--highlight {
        background: $primary-darken-1;
    }

    #files-list > ListItem.selected {
        background: $accent-darken-1;
        color: $text;
        text-style: bold;
    }

    /* ── Instructions strip ── */
    #instructions {
        height: 1;
        background: $surface-darken-1;
        color: $text-disabled;
        padding: 0 2;
        content-align: left middle;
    }

    /* ── Export section ── */
    #export-section {
        height: auto;
        background: $surface-darken-1;
        padding: 1 2 1 2;
        border-top: tall $primary-darken-3;
    }

    #export-label {
        color: $text-muted;
        text-style: bold;
        margin-bottom: 1;
    }

    #action-buttons {
        height: auto;
    }

    #action-buttons Button {
        width: 1fr;
        min-width: 1;
        height: 4;
        background: $primary-darken-2;
        border: none;
        color: $text;
        content-align: center middle;
    }

    #action-buttons Button:hover {
        background: $primary;
    }

    #action-buttons Button:disabled {
        background: $surface;
        color: $text-disabled;
        border: none;
    }

    /* ── Right panel ── */
    #right-panel {
        width: 1fr;
        background: $background;
    }

    #preview-label {
        background: $primary-darken-3;
        color: $text-muted;
        padding: 0 2;
        text-style: bold;
        width: 100%;
        height: 1;
    }

    #preview-container {
        height: 1fr;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit_app", "Quit"),
        Binding("tab", "focus_next", "Next panel", show=False),
        Binding("shift+tab", "focus_previous", "Prev panel", show=False),
    ]

    def __init__(
        self, local_path: str, files: List[str], filter_path: Optional[str] = None
    ) -> None:
        super().__init__()
        self._local_path = Path(local_path)
        self._all_files = files
        self._folders = _extract_folders(files)
        self._current_folder = (
            filter_path.rstrip("/")
            if filter_path and filter_path.rstrip("/") in self._folders
            else (self._folders[0] if self._folders else None)
        )
        self._current_file: Optional[str] = None
        self._file_list: List[str] = (
            _files_for_folder(files, self._current_folder)
            if self._current_folder
            else []
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _folder_items(self) -> List[ListItem]:
        return [
            ListItem(Label(f"📁 {f}"), id=f"folder_{i}")
            for i, f in enumerate(self._folders)
        ]

    def _file_items(self, folder: str) -> List[ListItem]:
        files = _files_for_folder(self._all_files, folder)
        self._file_list = files
        if not files:
            return [ListItem(Label("[dim](no files)[/dim]"), id="file_empty")]
        short_names = [Path(f).name for f in files]
        return [ListItem(Label(n), id=f"file_{i}") for i, n in enumerate(short_names)]

    def _set_action_buttons_disabled(self, disabled: bool) -> None:
        for btn_id in ("btn-print", "btn-save", "btn-copy"):
            self.query_one(f"#{btn_id}", Button).disabled = disabled

    def _mark_folder_selected(self, folder_idx: int) -> None:
        for item in self.query("#folder-list ListItem"):
            item.remove_class("selected")
        try:
            self.query_one(f"#folder_{folder_idx}", ListItem).add_class("selected")
        except Exception:
            pass

    def _mark_file_selected(self, file_idx: int) -> None:
        for item in self.query("#files-list ListItem"):
            item.remove_class("selected")
        try:
            self.query_one(f"#file_{file_idx}", ListItem).add_class("selected")
        except Exception:
            pass

    # ── Layout ─────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield Label("FOLDERS", classes="section-head")
                yield ListView(*self._folder_items(), id="folder-list")
                yield Label("FILES", classes="section-head")
                initial_items = (
                    self._file_items(self._current_folder)
                    if self._current_folder
                    else [ListItem(Label("[dim](select a folder)[/dim]"), id="file_empty")]
                )
                yield ListView(*initial_items, id="files-list")
                yield Label("↑ ↓ navigate · Enter export", id="instructions")
                with Vertical(id="export-section"):
                    yield Label("EXPORT FILE", id="export-label")
                    with Horizontal(id="action-buttons"):
                        yield Button("📄\nPrint", id="btn-print", disabled=True)
                        yield Button("💾\nSave", id="btn-save", disabled=True)
                        yield Button("📋\nCopy", id="btn-copy", disabled=True)
            with Vertical(id="right-panel"):
                yield Label("PREVIEW", id="preview-label")
                with ScrollableContainer(id="preview-container"):
                    yield FilePreview(id="file-preview")
        yield Footer()

    def on_mount(self) -> None:
        if self._current_folder and self._current_folder in self._folders:
            folder_idx = self._folders.index(self._current_folder)
            self.query_one("#folder-list", ListView).index = folder_idx
            self._mark_folder_selected(folder_idx)
        # Auto-preview the first file in the initial folder
        if self._file_list:
            self._current_file = self._file_list[0]
            self._set_action_buttons_disabled(False)
            self._mark_file_selected(0)
            self.query_one("#file-preview", FilePreview).show_file(
                self._local_path / self._current_file
            )
            self.query_one("#preview-label", Label).update(
                f"PREVIEW  ·  {self._current_file}"
            )
        self.query_one("#files-list", ListView).focus()

    # ── Event handlers ──────────────────────────────────────────────────────────

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if not event.item:
            return
        item_id = event.item.id or ""

        if event.list_view.id == "folder-list":
            if not item_id.startswith("folder_"):
                return
            try:
                idx = int(item_id[7:])
                folder = self._folders[idx]
            except (ValueError, IndexError):
                return
            self._current_folder = folder
            self._mark_folder_selected(idx)
            files_list = self.query_one("#files-list", ListView)
            await files_list.clear()
            await files_list.mount(*self._file_items(folder))
            # Auto-preview first file in the newly selected folder
            if self._file_list:
                self._current_file = self._file_list[0]
                self._set_action_buttons_disabled(False)
                self._mark_file_selected(0)
                self.query_one("#file-preview", FilePreview).show_file(
                    self._local_path / self._current_file
                )
                self.query_one("#preview-label", Label).update(
                    f"PREVIEW  ·  {self._current_file}"
                )
            else:
                self._current_file = None
                self._set_action_buttons_disabled(True)
                self.query_one("#file-preview", FilePreview).show_file(None)
                self.query_one("#preview-label", Label).update("PREVIEW")

        elif event.list_view.id == "files-list":
            if not item_id.startswith("file_") or item_id == "file_empty":
                return
            try:
                idx = int(item_id[5:])
                rel = self._file_list[idx]
            except (ValueError, IndexError):
                return
            self._current_file = rel
            self._set_action_buttons_disabled(False)
            self._mark_file_selected(idx)
            filepath = self._local_path / rel
            self.query_one("#file-preview", FilePreview).show_file(filepath)
            self.query_one("#preview-label", Label).update(f"PREVIEW  ·  {rel}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self._current_file:
            return
        action_map = {
            "btn-print": "print",
            "btn-save": "save",
            "btn-copy": "copy",
        }
        action = action_map.get(event.button.id or "")
        if action:
            self.exit((self._current_file, action))

    def action_quit_app(self) -> None:
        self.exit(None)


def browse_local_configs_tui(
    local_path: str, filter_path: Optional[str] = None
) -> None:
    """Load manifest, launch TUI, then execute the chosen action."""
    files = load_local_manifest(local_path)
    if files is None:
        # Graceful fallback: list by supported extension
        from configr_cli.local import list_local_files

        files = list_local_files(local_path)
        if files:
            print(
                "⚠️  No manifest.json found — showing all supported config files.\n"
                "    Add a manifest.json to your local configr repo for curated results."
            )

    if not files:
        print(f"❌ No config files found in '{local_path}'.")
        return

    app = ConfigrBrowserApp(local_path, files, filter_path)
    result = app.run()

    if result is None:
        print("❌ Operation cancelled.")
        return

    rel_path, action = result
    content = (Path(local_path) / rel_path).read_text(encoding="utf-8")

    if action == "print":
        print(f"\n📄 Contents of '{rel_path}':\n")
        print(content)

    elif action == "save":
        filename_only = os.path.basename(rel_path)
        if os.path.exists(filename_only):
            overwrite = inquirer.confirm(
                message=f"⚠️ '{filename_only}' already exists. Overwrite?",
                default=False,
            ).execute()
            if not overwrite:
                print("❌ Aborted. File not overwritten.")
                return
        with open(filename_only, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ '{rel_path}' saved locally as '{filename_only}'.")

    elif action == "copy":
        pyperclip.copy(content)
        print("📋 File contents copied to clipboard.")
