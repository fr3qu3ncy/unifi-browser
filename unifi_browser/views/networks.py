"""NetworksView and NetworkDetailView."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from unifi_browser.helpers import enabled_badge, mgmt_badge, render_network_detail
from unifi_browser.views.base import DetailView


class NetworksView(Container):
    """Lists networks / VLANs configured on a site."""

    _COLUMNS = ("Name", "VLAN", "Management", "Enabled", "Default", "Origin")

    def compose(self) -> ComposeResult:
        yield Static("◈  Networks", id="networks-title")
        yield DataTable(id="networks-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#networks-title", Static).update(
            f"◈  Networks  [dim]─[/dim]  [bold cyan]{site_name}[/bold cyan]"
            "  [dim]— Enter for details · ESC to go back[/dim]"
        )

    def populate(self, networks: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for net in networks:
            origin = (net.get("metadata") or {}).get("origin") or "—"
            origin_label = {"USER_DEFINED": "User", "SYSTEM_DEFINED": "System"}.get(origin, origin)
            table.add_row(
                str(net.get("name") or "—"),
                str(net.get("vlanId") or "—"),
                mgmt_badge(net.get("management") or ""),
                enabled_badge(net.get("enabled")),
                "★" if net.get("default") else "☆",
                origin_label,
                key=net.get("id"),
            )


class NetworkDetailView(DetailView):
    """Full detail panel for a single network."""

    TITLE_ID  = "network-detail-title"
    SCROLL_ID = "network-detail-scroll"
    BODY_ID   = "network-detail-body"

    def show_network(self, network: dict) -> None:
        name = network.get("name") or "Unknown"
        self._set_title(
            f"◈  Network  [dim]─[/dim]  [bold cyan]{name}[/bold cyan]"
            "  [dim]— ESC to go back[/dim]"
        )
        self._set_body(render_network_detail(network))
