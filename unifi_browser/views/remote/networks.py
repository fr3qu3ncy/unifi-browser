"""RemoteNetworksView and RemoteNetworkDetailView."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from unifi_browser.helpers import enabled_badge, mgmt_badge, render_network_detail
from unifi_browser.views.base import DetailView


class RemoteNetworksView(Container):
    """Lists networks on a remote site."""

    _COLUMNS = ("Name", "VLAN", "Management", "Default", "Enabled")

    def compose(self) -> ComposeResult:
        yield Static("◈  Remote Networks", id="r-networks-title")
        yield DataTable(id="r-networks-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#r-networks-title", Static).update(
            f"◈  Remote Networks  [dim]─[/dim]  [bold #e6a817]{site_name}[/bold #e6a817]"
            "  [dim]— Enter for details · ESC to go back[/dim]"
        )

    def populate(self, networks: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for net in networks:
            table.add_row(
                str(net.get("name") or "—"),
                str(net.get("vlanId") or "—"),
                mgmt_badge(net.get("management") or ""),
                enabled_badge(net.get("default")),
                enabled_badge(net.get("enabled")),
                key=net.get("id"),
            )


class RemoteNetworkDetailView(DetailView):
    """Full detail panel for a single remote network."""

    TITLE_ID  = "r-network-detail-title"
    SCROLL_ID = "r-network-detail-scroll"
    BODY_ID   = "r-network-detail-body"

    def show_network(self, network: dict) -> None:
        name = network.get("name") or "Unknown"
        self._set_title(
            f"◈  Remote Network  [dim]─[/dim]  [bold #e6a817]{name}[/bold #e6a817]"
            "  [dim]— ESC to go back[/dim]"
        )
        self._set_body(render_network_detail(network))
