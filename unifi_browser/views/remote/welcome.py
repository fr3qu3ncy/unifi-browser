"""RemoteWelcomeView — shown before any remote connection."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from unifi_browser.constants import LOGO


class RemoteWelcomeView(Container):
    def compose(self) -> ComposeResult:
        yield Static(LOGO, id="r-logo")
        yield Static(
            "  [bold #e6a817]Remote (Cloud)[/bold #e6a817]  ·  "
            "Connect to the Unifi Cloud API at api.ui.com\n\n"
            "  Use [bold #e6a817]/connect remote[/bold #e6a817] to connect  ·  "
            "Press [bold]l[/bold] to switch to Local view  ·  "
            "Type [bold #e6a817]/help[/bold #e6a817] for all commands\n\n"
            "  [dim]Requires Unifi controller firmware [/dim][bold]>= 5.0.3[/bold]",
            id="r-welcome-hints",
        )
