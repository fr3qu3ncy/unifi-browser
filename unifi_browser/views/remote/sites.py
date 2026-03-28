"""RemoteSitesView — lists sites from the Unifi Cloud API."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static


class RemoteSitesView(Container):
    """Lists the sites available in the Unifi Cloud account."""

    _COLUMNS = ("Name", "Controller", "IP Address", "Status", "Host ID")

    def compose(self) -> ComposeResult:
        yield Static(
            "◈  Remote Sites  [dim]— Enter: view site · I: ISP Metrics · H: All Hosts · ESC: back[/dim]",
            id="r-sites-title",
        )
        yield DataTable(id="r-sites-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def populate(self, sites: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for site in sites:
            host_info      = site.get("_hostInfo") or {}
            hardware       = host_info.get("hardware") or {}
            reported_state = host_info.get("reportedState") or {}
            location       = host_info.get("location") or {}

            # Name: prefer description from meta, then hostname from hardware/reportedState
            name = (
                (site.get("meta") or {}).get("desc")
                or hardware.get("hostname")
                or reported_state.get("hostname")
                or host_info.get("hostname")
                or site.get("siteId", "—")
            )

            # Controller model
            controller = (
                hardware.get("name")
                or hardware.get("shortname")
                or host_info.get("type")
                or "—"
            )

            # IP address
            ip_address = (
                host_info.get("ipAddress")
                or reported_state.get("ipAddress")
                or "—"
            )

            # Status
            status = (
                reported_state.get("controllerStatus")
                or reported_state.get("state")
                or host_info.get("type")
                or "—"
            )

            table.add_row(
                str(name),
                str(controller),
                str(ip_address),
                str(status),
                str(site.get("hostId") or "—"),
                key=site.get("siteId"),
            )
