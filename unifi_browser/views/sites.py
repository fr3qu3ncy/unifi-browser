"""SitesView — lists sites returned by the local Unifi Controller."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static


class SitesView(Container):
    """Lists the sites on the local Unifi controller."""

    _COLUMNS = ("Name", "ID")

    def compose(self) -> ComposeResult:
        yield Static("◈  Sites  [dim]— press Enter to view a site[/dim]", id="sites-title")
        yield DataTable(id="sites-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def populate(self, sites: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for site in sites:
            table.add_row(
                str(site.get("name") or "—"),
                str(site.get("id") or "—"),
                key=site.get("id"),
            )
