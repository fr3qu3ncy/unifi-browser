"""WansView — WAN interfaces for a local site."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static


class WansView(Container):
    """Lists WAN interfaces configured on a local site."""

    _COLUMNS = ("#", "Name", "ID")

    def compose(self) -> ComposeResult:
        yield Static("◈  WAN Interfaces", id="wans-title")
        yield DataTable(id="wans-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#wans-title", Static).update(
            f"◈  WAN Interfaces  [dim]─[/dim]  [bold cyan]{site_name}[/bold cyan]"
            "  [dim]— ESC to go back[/dim]"
        )

    def populate(self, wans: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for idx, wan in enumerate(wans, start=1):
            table.add_row(
                str(idx),
                str(wan.get("name") or "—"),
                str(wan.get("id") or "—"),
                key=wan.get("id"),
            )
