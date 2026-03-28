"""RemoteDevicesView and RemoteDeviceDetailView."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from unifi_browser.helpers import render_device_detail, status_badge, uptime
from unifi_browser.views.base import DetailView


class RemoteDevicesView(Container):
    """Lists devices on a remote site."""

    _COLUMNS = ("State", "Name", "Model", "IP Address", "MAC", "Uptime", "Firmware")

    def compose(self) -> ComposeResult:
        yield Static("◈  Remote Devices", id="r-devices-title")
        yield DataTable(id="r-devices-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#r-devices-title", Static).update(
            f"◈  Remote Devices  [dim]─[/dim]  [bold #e6a817]{site_name}[/bold #e6a817]"
            "  [dim]— Enter for details · ESC to go back[/dim]"
        )

    def populate(self, devices: list[dict]) -> None:
        from unifi_browser.helpers import firmware_badge
        table = self.query_one(DataTable)
        table.clear()
        for dev in devices:
            fw_able  = dev.get("firmwareUpdatable")
            fw_label = "updateAvailable" if fw_able else ("upToDate" if fw_able is not None else "—")
            table.add_row(
                status_badge(dev.get("state") or "unknown"),
                str(dev.get("name") or "—"),
                str(dev.get("model") or "—"),
                str(dev.get("ipAddress") or "—"),
                str(dev.get("macAddress") or "—"),
                uptime(dev.get("startupTime") or ""),
                firmware_badge(fw_label) if fw_label != "—" else "—",
                key=dev.get("id") or dev.get("mac"),
            )


class RemoteDeviceDetailView(DetailView):
    """Full detail panel for a single remote device."""

    TITLE_ID  = "r-detail-title"
    SCROLL_ID = "r-detail-scroll"
    BODY_ID   = "r-detail-body"

    def show_device(self, device: dict) -> None:
        name = device.get("name") or device.get("macAddress") or "Unknown"
        self._set_title(
            f"◈  Remote Device  [dim]─[/dim]  [bold #e6a817]{name}[/bold #e6a817]"
            "  [dim]— ESC to go back[/dim]"
        )
        self._set_body(render_device_detail(device))
