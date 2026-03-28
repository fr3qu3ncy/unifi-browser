"""WifiView and WifiDetailView."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Static

from unifi_browser.helpers import (
    bool_row,
    enabled_badge,
    format_frequencies,
    format_security_type,
    render_wifi_detail,
)
from unifi_browser.views.base import DetailView


class WifiView(Container):
    """Lists WiFi broadcast SSIDs for a site."""

    _COLUMNS = ("Status", "Name", "Security", "Bands", "Network")

    def compose(self) -> ComposeResult:
        yield Static("◈  WiFi", id="wifi-title")
        yield DataTable(id="wifi-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#wifi-title", Static).update(
            f"◈  WiFi  [dim]─[/dim]  [bold cyan]{site_name}[/bold cyan]"
            "  [dim]— Enter for details · ESC to go back[/dim]"
        )

    def populate(self, broadcasts: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for b in broadcasts:
            sec_type = (b.get("securityConfiguration") or {}).get("type") or ""
            net_type  = (b.get("network") or {}).get("type") or "—"
            freqs     = b.get("broadcastingFrequenciesGHz") or []
            table.add_row(
                enabled_badge(b.get("enabled")),
                str(b.get("name") or "—"),
                format_security_type(sec_type),
                format_frequencies(freqs),
                net_type.capitalize(),
                key=b.get("id"),
            )


class WifiDetailView(DetailView):
    """Full detail panel for a single WiFi broadcast, with passphrase toggle."""

    TITLE_ID  = "wifi-detail-title"
    SCROLL_ID = "wifi-detail-scroll"
    BODY_ID   = "wifi-detail-body"

    BINDINGS = [Binding("p", "toggle_passphrase", "Toggle passphrase")]

    _wifi_data: dict = {}
    _show_passphrase: bool = False

    def show_wifi(self, wifi: dict) -> None:
        self._wifi_data = wifi
        self._show_passphrase = False
        self._refresh_content()

    def action_toggle_passphrase(self) -> None:
        self._show_passphrase = not self._show_passphrase
        self._refresh_content()
        status = "revealed" if self._show_passphrase else "hidden"
        self.app.notify(f"Passphrase {status}", timeout=2)

    def _refresh_content(self) -> None:
        name = self._wifi_data.get("name") or "Unknown"
        passphrase_hint = "P to hide" if self._show_passphrase else "P to reveal"
        self._set_title(
            f"◈  WiFi  [dim]─[/dim]  [bold cyan]{name}[/bold cyan]"
            f"  [dim]— {passphrase_hint} passphrase · ESC to go back[/dim]"
        )
        self._set_body(render_wifi_detail(self._wifi_data, show_passphrase=self._show_passphrase))
