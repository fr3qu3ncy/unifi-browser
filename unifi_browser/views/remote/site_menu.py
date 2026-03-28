"""RemoteSiteMenuView — navigation hub after selecting a remote site."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static


class RemoteSiteMenuView(Container):
    """Navigation hub — shown after selecting a remote site."""

    _MENU_ITEMS = [
        ("⬡", "Devices",        "Network infrastructure — switches, APs, gateways",   "r-devices"),
        ("◎", "Clients",        "Connected wired and wireless clients",                "r-clients"),
        ("⬢", "Networks",       "VLANs and network segments",                          "r-networks"),
        ("⌾", "WiFi",           "Wireless broadcast SSIDs and security settings",      "r-wifi"),
        ("⇅", "WAN Interfaces", "WAN uplink interfaces",                               "r-wans"),
        ("⬛", "Controller",     "Details about this site's Unifi controller (host)",   "r-controller"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("◈  Remote Site", id="r-sitemenu-title")
        yield DataTable(id="r-sitemenu-table", cursor_type="row", show_header=False)

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
        self.query_one("#r-sitemenu-title", Static).update(
            f"◈  [bold #e6a817]{name}[/bold #e6a817]  [dim]— select an area to explore[/dim]"
        )
