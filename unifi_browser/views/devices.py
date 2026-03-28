"""DevicesView and DeviceDetailView."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from unifi_browser.helpers import firmware_badge, render_device_detail, status_badge
from unifi_browser.views.base import DetailView


class DevicesView(Container):
    """Lists devices managed by a selected site."""

    _COLUMNS = ("Status", "Name", "Model", "IP Address", "MAC", "Features", "Firmware", "Version")

    def compose(self) -> ComposeResult:
        yield Static("◈  Devices", id="devices-title")
        yield DataTable(id="devices-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#devices-title", Static).update(
            f"◈  Devices  [dim]─[/dim]  [bold cyan]{site_name}[/bold cyan]"
            "  [dim]— ESC to go back  ·  Enter for details[/dim]"
        )

    def populate(self, devices: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for dev in devices:
            state    = dev.get("state") or "—"
            fw_able  = dev.get("firmwareUpdatable")
            fw_label = "updateAvailable" if fw_able else "upToDate" if fw_able is not None else "—"
            features = ", ".join(dev.get("features") or []) or "—"
            table.add_row(
                status_badge(state) if state != "—" else Text("— "),
                str(dev.get("name") or "—"),
                str(dev.get("model") or "—"),
                str(dev.get("ipAddress") or "—"),
                str(dev.get("macAddress") or "—"),
                features,
                firmware_badge(fw_label) if fw_label != "—" else Text("— "),
                str(dev.get("firmwareVersion") or "—"),
                key=dev.get("id") or dev.get("macAddress"),
            )


class DeviceDetailView(DetailView):
    """Full detail panel for a single device."""

    TITLE_ID  = "detail-title"
    SCROLL_ID = "detail-scroll"
    BODY_ID   = "detail-body"

    def show_device(self, device: dict) -> None:
        name = device.get("name") or device.get("mac") or "Unknown"
        self._set_title(
            f"◈  Device  [dim]─[/dim]  [bold cyan]{name}[/bold cyan]"
            "  [dim]— ESC to go back[/dim]"
        )
        self._set_body(render_device_detail(device))
