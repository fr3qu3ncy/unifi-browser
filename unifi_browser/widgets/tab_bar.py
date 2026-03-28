"""
TabBar — top-docked Local / Remote mode switcher.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class TabBar(Widget):
    """Two-tab bar docked at the top for switching between Local and Remote modes."""

    class TabSelected(Message):
        """Posted when a tab is clicked."""
        def __init__(self, mode: str) -> None:
            super().__init__()
            self.mode = mode

    active: reactive[str] = reactive("local")
    local_connected: reactive[bool] = reactive(False)
    remote_connected: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="tab-bar-inner"):
            yield Static("", id="tab-local")
            yield Static("", id="tab-remote")
            yield Static(
                "  [dim]l[/dim][dim]=[/dim][dim]Local[/dim]  "
                "[dim]r[/dim][dim]=[/dim][dim]Remote[/dim]",
                id="tab-hints",
            )

    def on_mount(self) -> None:
        self._refresh_tabs()

    def watch_active(self, _: str) -> None:
        self._refresh_tabs()

    def watch_local_connected(self, _: bool) -> None:
        self._refresh_tabs()

    def watch_remote_connected(self, _: bool) -> None:
        self._refresh_tabs()

    def _refresh_tabs(self) -> None:
        local_dot  = "[bright_green]●[/bright_green]" if self.local_connected  else "[dim]○[/dim]"
        remote_dot = "[bright_green]●[/bright_green]" if self.remote_connected else "[dim]○[/dim]"

        if self.active == "local":
            local_markup  = f"[bold #00b4d8 reverse]  ◈ Local {local_dot}  [/bold #00b4d8 reverse]"
            remote_markup = f"[dim]  ◈ Remote {remote_dot}  [/dim]"
        else:
            local_markup  = f"[dim]  ◈ Local {local_dot}  [/dim]"
            remote_markup = f"[bold #e6a817 reverse]  ◈ Remote {remote_dot}  [/bold #e6a817 reverse]"

        try:
            self.query_one("#tab-local",  Static).update(local_markup)
            self.query_one("#tab-remote", Static).update(remote_markup)
        except Exception:
            pass  # not yet mounted

    def on_click(self, event) -> None:
        # Determine which tab was clicked based on offset
        try:
            local_widget  = self.query_one("#tab-local",  Static)
            remote_widget = self.query_one("#tab-remote", Static)
            if event.widget is local_widget:
                self.post_message(self.TabSelected("local"))
            elif event.widget is remote_widget:
                self.post_message(self.TabSelected("remote"))
        except Exception:
            pass
