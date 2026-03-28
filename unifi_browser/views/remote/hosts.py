"""RemoteHostsView and RemoteHostDetailView — cloud host list and detail."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from unifi_browser.helpers import render_host_detail
from unifi_browser.views.base import DetailView


class RemoteHostsView(Container):
    """Lists all Unifi Cloud hosts (controllers)."""

    _COLUMNS = ("Name", "Type", "IP Address", "Firmware", "State", "Host ID")

    def compose(self) -> ComposeResult:
        yield Static(
            "◈  Remote Hosts  [dim]— all controllers on your account · Enter: details · ESC: back[/dim]",
            id="r-hosts-title",
        )
        yield DataTable(id="r-hosts-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def populate(self, hosts: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for host in hosts:
            rs = host.get("reportedState") or {}
            state = rs.get("state") or "—"
            if state == "connected":
                state_fmt = "[bright_green]● connected[/bright_green]"
            elif state == "disconnected":
                state_fmt = "[red]○ disconnected[/red]"
            else:
                state_fmt = f"[yellow]{state}[/yellow]"
            table.add_row(
                str(rs.get("name") or rs.get("hostname") or "—"),
                str(host.get("type") or "—"),
                str(host.get("ipAddress") or rs.get("ip") or "—"),
                str(rs.get("version") or "—"),
                state_fmt,
                str(host.get("id") or "—"),
                key=host.get("id"),
            )


class RemoteHostDetailView(DetailView):
    """Full detail panel for a single remote host/controller (from all-hosts list)."""

    TITLE_ID  = "r-host-detail-title"
    SCROLL_ID = "r-host-detail-scroll"
    BODY_ID   = "r-host-detail-body"

    def show_host(self, host: dict) -> None:
        rs   = host.get("reportedState") or {}
        name = rs.get("name") or rs.get("hostname") or host.get("id", "Unknown")
        self._set_title(
            f"◈  Remote Host  [dim]─[/dim]  [bold #e6a817]{name}[/bold #e6a817]"
            "  [dim]— ESC to go back[/dim]"
        )
        self._set_body(render_host_detail(host))


class RemoteControllerDetailView(DetailView):
    """Full detail panel for the controller of the currently selected site."""

    TITLE_ID  = "r-controller-title"
    SCROLL_ID = "r-controller-scroll"
    BODY_ID   = "r-controller-body"

    def show_host(self, host: dict) -> None:
        rs   = host.get("reportedState") or {}
        name = rs.get("name") or rs.get("hostname") or host.get("id", "Unknown")
        self._set_title(
            f"◈  Controller  [dim]─[/dim]  [bold #e6a817]{name}[/bold #e6a817]"
            "  [dim]— ESC to go back[/dim]"
        )
        self._set_body(render_host_detail(host))
