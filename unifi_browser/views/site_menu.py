"""SiteMenuView — navigation hub after selecting a site."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static


class SiteMenuView(Container):
    """Navigation hub — shown after selecting a site."""

    _MENU_ITEMS = [
        ("⬡", "Devices",        "Network infrastructure — switches, APs, gateways", "devices"),
        ("◎", "Clients",        "Connected wired and wireless clients",              "clients"),
        ("⬢", "Networks",       "VLANs and network segments",                        "networks"),
        ("⌾", "WiFi",           "Wireless broadcast SSIDs and security settings",    "wifi"),
        ("⇅", "WAN Interfaces", "WAN uplink interfaces",                             "wans"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("◈  Site", id="sitemenu-title")
        yield DataTable(id="sitemenu-table", cursor_type="row", show_header=False)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_column("option", width=68)
        for icon, title, desc, action_id in self._MENU_ITEMS:
            table.add_row(
                f" {icon}  {title}   {desc}",
                key=action_id,
            )

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, name: str) -> None:
        self.query_one("#sitemenu-title", Static).update(
            f"◈  [bold cyan]{name}[/bold cyan]  [dim]— select an area to explore[/dim]"
        )
