"""WelcomeView — shown on app start before any connection."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from unifi_browser.constants import LOGO


class WelcomeView(Container):
    def compose(self) -> ComposeResult:
        yield Static(LOGO, id="logo")
        yield Static(
            "  [bold cyan]Local Controller[/bold cyan]  ·  "
            "Connect directly to your Unifi Controller on your network\n\n"
            "  Use [bold cyan]/connect[/bold cyan] to connect  ·  "
            "Press [bold]r[/bold] to switch to Remote (Cloud) view  ·  "
            "Type [bold cyan]/help[/bold cyan] for all commands\n\n"
            "  [dim]Requires Unifi controller firmware [/dim][bold]>= 5.0.3[/bold]",
            id="welcome-hints",
        )
