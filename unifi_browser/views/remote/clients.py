"""RemoteClientsView and RemoteClientDetailView."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from unifi_browser.helpers import client_type_badge, render_client_detail, time_ago
from unifi_browser.views.base import DetailView


class RemoteClientsView(Container):
    """Lists clients connected to a remote site."""

    _COLUMNS = ("Type", "Name", "IP Address", "MAC", "Connected", "Uplink Device")

    def compose(self) -> ComposeResult:
        yield Static("◈  Remote Clients", id="r-clients-title")
        yield DataTable(id="r-clients-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#r-clients-title", Static).update(
            f"◈  Remote Clients  [dim]─[/dim]  [bold #e6a817]{site_name}[/bold #e6a817]"
            "  [dim]— Enter for details · ESC to go back[/dim]"
        )

    def populate(self, clients: list[dict], devices: list[dict]) -> None:
        dev_names: dict[str, str] = {
            d.get("id", ""): (d.get("name") or d.get("id", "—")) for d in devices
        }
        table = self.query_one(DataTable)
        table.clear()
        for client in clients:
            uplink_id   = client.get("uplinkDeviceId") or ""
            uplink_name = dev_names.get(uplink_id) or uplink_id or "—"
            table.add_row(
                client_type_badge(client.get("type") or ""),
                str(client.get("name") or "—"),
                str(client.get("ipAddress") or "—"),
                str(client.get("macAddress") or "—"),
                time_ago(client.get("connectedAt") or ""),
                uplink_name,
                key=client.get("id"),
            )


class RemoteClientDetailView(DetailView):
    """Full detail panel for a single remote client."""

    TITLE_ID  = "r-client-detail-title"
    SCROLL_ID = "r-client-detail-scroll"
    BODY_ID   = "r-client-detail-body"

    def show_client(self, client: dict, devices: list[dict]) -> None:
        name = client.get("name") or client.get("macAddress") or "Unknown"
        self._set_title(
            f"◈  Remote Client  [dim]─[/dim]  [bold #e6a817]{name}[/bold #e6a817]"
            "  [dim]— ESC to go back[/dim]"
        )
        self._set_body(render_client_detail(client, devices))
