"""
HelpScreen modal — displays available slash commands and usage info.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from unifi_browser.constants import COMMANDS


class HelpScreen(ModalScreen[None]):
    """Modal overlay with commands, tab switching, and firmware info."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter",  "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        cmd_lines = []
        for cmd, desc in COMMANDS.items():
            cmd_lines.append(f"  [bold cyan]{cmd:<16}[/bold cyan] {desc}")

        content = "\n".join([
            "[bold cyan]Local vs Remote[/bold cyan]\n",
            "  Unifi Browser supports two connection modes:\n",
            "  [bold cyan]Local[/bold cyan]   — connects directly to a Unifi Controller on your network",
            "           Use [bold cyan]/connect local[/bold cyan] or switch to the Local tab and type [bold cyan]/connect[/bold cyan]\n",
            "  [bold #e6a817]Remote[/bold #e6a817]  — connects to the Unifi Cloud API (api.ui.com)",
            "           Use [bold #e6a817]/connect remote[/bold #e6a817] or switch to the Remote tab and type [bold #e6a817]/connect[/bold #e6a817]\n",
            "  [bold]/connect[/bold] with no argument opens the login for whichever tab you are currently on.",
            "  Press [bold]l[/bold] for Local · [bold]r[/bold] for Remote  (or click the tabs at the top)\n",
            "[dim]─────────────────────────────────────────────────────────[/dim]\n",
            "[bold cyan]Commands[/bold cyan]\n",
            *cmd_lines,
            "\n[dim]─────────────────────────────────────────────────────────[/dim]\n",
            "[bold #e6a817]ISP Metrics[/bold #e6a817]  [dim](remote mode only)[/dim]\n",
            "  Shows per-host internet connection stats and time-series sparklines.",
            "  Access via [bold #e6a817]/isp[/bold #e6a817] command or press [bold #e6a817]I[/bold #e6a817] from anywhere in Remote mode.\n",
            "  Press [bold]Tab[/bold] to cycle through range presets:",
            "    [bold #e6a817]5m · 24h[/bold #e6a817]   5-minute samples over the last 24 hours",
            "    [bold #e6a817]1h · 7d[/bold #e6a817]    Hourly samples over the last 7 days",
            "    [bold #e6a817]1h · 30d[/bold #e6a817]   Hourly samples over the last 30 days\n",
            "  Metrics shown: ISP name/ASN, latency, download/upload throughput,",
            "  packet loss, uptime — plus sparkline graphs for each metric.\n",
            "[dim]─────────────────────────────────────────────────────────[/dim]\n",
            "[bold yellow]Requirements[/bold yellow]\n",
            "  Unifi controller firmware [bold]>= 5.0.3[/bold] is required for API access.",
            "  Earlier firmware versions do not expose the REST API used by this tool.",
        ])

        with Center():
            with Middle():
                with Vertical(id="help-dialog"):
                    yield Static("◈  Help", id="help-title")
                    yield Static(content, id="help-body")
                    yield Button("Close", id="help-close", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#help-close", Button).focus()

    def on_button_pressed(self) -> None:
        self.dismiss()
