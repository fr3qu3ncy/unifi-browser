"""RemoteWansView — WAN interfaces for a remote site."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static


class RemoteWansView(Container):
    """Lists WAN interfaces configured on a remote site."""

    _COLUMNS = ("#", "Name", "ID")

    def compose(self) -> ComposeResult:
        yield Static("◈  Remote WAN Interfaces", id="r-wans-title")
        yield DataTable(id="r-wans-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#r-wans-title", Static).update(
            f"◈  Remote WAN Interfaces  [dim]─[/dim]  [bold #e6a817]{site_name}[/bold #e6a817]"
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
