#!/usr/bin/env python3
"""
Unifi Browser — TUI for browsing Unifi network configuration via the local REST API.
"""
from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, Horizontal, Middle, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    ContentSwitcher,
    DataTable,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────────────────────

LOGO = """\
╔══════════════════════════════════════════════════════╗
║                                                      ║
║    ██╗   ██╗███╗  ██╗██╗███████╗██╗                  ║
║    ██║   ██║████╗ ██║██║██╔════╝██║                  ║
║    ██║   ██║██╔██╗██║██║█████╗  ██║                  ║
║    ██║   ██║██║╚████║██║██╔══╝  ██║                  ║
║    ╚██████╔╝██║ ╚███║██║██║     ██║                  ║
║     ╚═════╝ ╚═╝  ╚══╝╚═╝╚═╝     ╚═╝                  ║
║                                                      ║
║    ──────  Network Configuration Browser  ──────     ║
║                                                      ║
╚══════════════════════════════════════════════════════╝"""

DEFAULT_API_URL = "https://unifi.local/"

# Slash-command registry
COMMANDS: dict[str, str] = {
    "/connect":  "Connect to a Unifi Controller",
    "/sites":    "Go back to the sites list",
    "/sitemenu": "Go back to the site menu",
    "/help":     "Show available commands",
    "/exit":     "Exit Unifi Browser",
}

# Back-navigation map: current screen → parent screen
_BACK_SCREEN: dict[str, str] = {
    "sites":          "welcome",
    "sitemenu":       "sites",
    "devices":        "sitemenu",
    "clients":        "sitemenu",
    "networks":       "sitemenu",
    "detail":         "devices",
    "client-detail":  "clients",
    "network-detail": "networks",
}


# ─────────────────────────────────────────────────────────────────────────────
#  URL History — persists recent controller URLs between sessions
# ─────────────────────────────────────────────────────────────────────────────

class UrlHistory:
    """Persists a list of recently used controller URLs to disk."""

    _PATH: Path = Path.home() / ".config" / "unifi-browser" / "history.json"
    _MAX: int = 10

    def __init__(self) -> None:
        self._urls: list[str] = self._load()

    def _load(self) -> list[str]:
        try:
            data = _json.loads(self._PATH.read_text())
            return [u for u in data if isinstance(u, str)][:self._MAX]
        except Exception:
            return []

    def save(self) -> None:
        self._PATH.parent.mkdir(parents=True, exist_ok=True)
        self._PATH.write_text(_json.dumps(self._urls))

    def add(self, url: str) -> None:
        """Add url to the front; deduplicate; trim to _MAX entries."""
        self._urls = [url] + [u for u in self._urls if u != url]
        self._urls = self._urls[:self._MAX]
        self.save()

    @property
    def urls(self) -> list[str]:
        return list(self._urls)

    @property
    def last(self) -> str:
        return self._urls[0] if self._urls else DEFAULT_API_URL


url_history = UrlHistory()


# ─────────────────────────────────────────────────────────────────────────────
#  Messages
# ─────────────────────────────────────────────────────────────────────────────

class CommandIssued(Message):
    """Posted when the user submits a valid slash command."""

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command


# ─────────────────────────────────────────────────────────────────────────────
#  Unifi Local API Client
# ─────────────────────────────────────────────────────────────────────────────

class UnifiClient:
    """Async Unifi local REST API client (SSL verification disabled for self-signed certs)."""

    _API_BASE = "/proxy/network/integration/v1"

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._http = httpx.AsyncClient(verify=False, timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    def _url(self, path: str) -> str:
        return f"{self.base_url}{self._API_BASE}{path}"

    async def _fetch_all(self, path: str) -> list[dict]:
        """Fetch all pages from a paginated endpoint."""
        results: list[dict] = []
        offset = 0
        limit = 100
        while True:
            resp = await self._http.get(
                self._url(path),
                params={"limit": limit, "offset": offset},
                headers=self._headers(),
            )
            resp.raise_for_status()
            body = resp.json()
            data = body.get("data", [])
            results.extend(data)
            if offset + len(data) >= body.get("totalCount", 0) or not data:
                break
            offset += len(data)
        return results

    async def get_sites(self) -> list[dict]:
        resp = await self._http.get(self._url("/sites"), headers=self._headers())
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def get_devices(self, site_id: str) -> list[dict]:
        return await self._fetch_all(f"/sites/{site_id}/devices")

    async def get_clients(self, site_id: str) -> list[dict]:
        return await self._fetch_all(f"/sites/{site_id}/clients")

    async def get_networks(self, site_id: str) -> list[dict]:
        return await self._fetch_all(f"/sites/{site_id}/networks")

    async def get_network(self, site_id: str, network_id: str) -> dict:
        resp = await self._http.get(
            self._url(f"/sites/{site_id}/networks/{network_id}"),
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._http.aclose()


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers — badges & formatting
# ─────────────────────────────────────────────────────────────────────────────

def _status_badge(status: str) -> Text:
    """Coloured dot + label for device status."""
    _STYLES: dict[str, tuple[str, str]] = {
        "connected":    ("●", "bright_green"),
        "disconnected": ("●", "red"),
        "online":       ("●", "bright_green"),
        "offline":      ("●", "red"),
        "adopting":     ("●", "cyan"),
        "updating":     ("●", "yellow"),
        "rebooting":    ("●", "yellow"),
        "unknown":      ("●", "dim"),
        "pendingadoption": ("●", "cyan"),
    }
    icon, colour = _STYLES.get(status.lower(), ("●", "dim"))
    t = Text()
    t.append(f"{icon} ", style=colour)
    t.append(status)
    return t


def _firmware_badge(status: str) -> Text:
    """Coloured badge for firmwareStatus values."""
    _STYLES: dict[str, tuple[str, str]] = {
        "upToDate":        ("✓", "green"),
        "updateAvailable": ("↑", "yellow"),
        "needsUpdate":     ("↑", "yellow"),
        "updating":        ("↺", "cyan"),
    }
    icon, colour = _STYLES.get(status, ("?", "dim"))
    t = Text()
    t.append(f"{icon} ", style=colour)
    t.append(status)
    return t


def _uptime(startup_time_str: str) -> str:
    """Human-readable uptime from an ISO-8601 startupTime string."""
    if not startup_time_str:
        return "—"
    try:
        startup = datetime.fromisoformat(startup_time_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - startup
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return "—"


def _fmt_bool(v: object) -> str:
    if v is True:
        return "Yes"
    if v is False:
        return "No"
    return "—"


def _time_ago(iso_str: str) -> str:
    """Human-readable 'X ago' from an ISO-8601 timestamp."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        if days > 0:
            return f"{days}d ago"
        if hours > 0:
            return f"{hours}h ago"
        if minutes > 0:
            return f"{minutes}m ago"
        return "just now"
    except Exception:
        return "—"


def _client_type_badge(type_str: str) -> Text:
    """Coloured icon + label for WIRED / WIRELESS client type."""
    t = Text()
    if type_str == "WIRED":
        t.append("⬢ ", style="cyan")
        t.append("Wired", style="cyan")
    elif type_str == "WIRELESS":
        t.append("⌾ ", style="bright_green")
        t.append("WiFi", style="bright_green")
    else:
        t.append(type_str or "—")
    return t


def _mgmt_badge(management: str) -> Text:
    """Coloured badge for network management type."""
    t = Text()
    if management == "GATEWAY":
        t.append("⬡ ", style="bright_green")
        t.append("Gateway")
    elif management == "UNMANAGED":
        t.append("○ ", style="yellow")
        t.append("Unmanaged")
    else:
        t.append(management or "—")
    return t


def _enabled_badge(enabled: object) -> Text:
    t = Text()
    if enabled is True:
        t.append("✓", style="bright_green")
    else:
        t.append("✗", style="red")
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  CompletionItem / BottomArea / CompletionListView / CommandBar
# ─────────────────────────────────────────────────────────────────────────────

class CompletionItem(ListItem):
    def __init__(self, cmd: str, desc: str) -> None:
        super().__init__(Label(f"  [bold]{cmd}[/bold]  [dim]{desc}[/dim]  "))
        self.cmd = cmd


class BottomArea(Container):
    """Single dock:bottom container. Height managed programmatically."""

    _BASE_HEIGHT = 3

    def on_mount(self) -> None:
        self.styles.height = self._BASE_HEIGHT

    def show_completions(self, n_items: int) -> None:
        self.styles.height = self._BASE_HEIGHT + n_items + 1

    def hide_completions(self) -> None:
        self.styles.height = self._BASE_HEIGHT


class CompletionListView(ListView):
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.display = False
            self.app.query_one(BottomArea).hide_completions()
            self.app.query_one("#cmd-input", Input).focus()
            event.stop()


class CommandBar(Container):
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label("❯", id="cmd-prompt"),
            Input(placeholder="Type / for commands…", id="cmd-input"),
            id="cmd-row",
        )

    def on_mount(self) -> None:
        self.query_one("#cmd-input", Input).focus()

    @on(Input.Changed, "#cmd-input")
    def _filter(self, event: Input.Changed) -> None:
        value = event.value
        completions = self.app.query_one("#completions", ListView)
        bottom = self.app.query_one(BottomArea)
        if value.startswith("/"):
            matches = [(cmd, desc) for cmd, desc in COMMANDS.items() if cmd.startswith(value)]
            completions.clear()
            for cmd, desc in matches:
                completions.append(CompletionItem(cmd, desc))
            if matches:
                completions.display = True
                bottom.show_completions(len(matches))
            else:
                completions.display = False
                bottom.hide_completions()
        else:
            completions.display = False
            bottom.hide_completions()

    @on(Input.Submitted, "#cmd-input")
    def _submit(self, event: Input.Submitted) -> None:
        self._execute(event.value.strip())

    def on_key(self, event: events.Key) -> None:
        completions = self.app.query_one("#completions", ListView)
        inp = self.query_one("#cmd-input", Input)
        if event.key == "down" and completions.display and inp.has_focus:
            completions.focus()
            event.stop()
        elif event.key == "escape":
            inp.clear()
            completions.display = False
            self.app.query_one(BottomArea).hide_completions()
            event.stop()

    def _execute(self, cmd: str) -> None:
        inp = self.query_one("#cmd-input", Input)
        self.app.query_one("#completions").display = False
        self.app.query_one(BottomArea).hide_completions()
        inp.clear()
        if cmd in COMMANDS:
            self.post_message(CommandIssued(cmd))
        elif cmd:
            self.app.notify(f"Unknown command: {cmd!r}  (try /help)", severity="warning")


# ─────────────────────────────────────────────────────────────────────────────
#  WelcomeView
# ─────────────────────────────────────────────────────────────────────────────

class WelcomeView(Container):
    def compose(self) -> ComposeResult:
        yield Static(LOGO, id="logo")
        yield Static(
            "\n"
            "  [dim]Type[/dim] [bold cyan]/connect[/bold cyan]  "
            "[dim]to connect to your local Unifi Controller[/dim]\n"
            "  [dim]Type[/dim] [bold cyan]/help[/bold cyan]     "
            "[dim]to list available commands[/dim]\n"
            "  [dim]Type[/dim] [bold cyan]/exit[/bold cyan]     "
            "[dim]to quit[/dim]\n",
            id="welcome-hints",
        )


# ─────────────────────────────────────────────────────────────────────────────
#  SitesView
# ─────────────────────────────────────────────────────────────────────────────

class SitesView(Container):
    """Lists the sites on the local Unifi controller."""

    _COLUMNS = ["Name", "ID"]

    def compose(self) -> ComposeResult:
        yield Static("◈  Sites  [dim]— press Enter to view devices[/dim]", id="sites-title")
        yield DataTable(id="sites-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def populate(self, sites: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for site in sites:
            table.add_row(
                str(site.get("name") or "—"),
                str(site.get("id") or "—"),
                key=site.get("id"),
            )


# ─────────────────────────────────────────────────────────────────────────────
#  SiteMenuView  — navigation hub after selecting a site
# ─────────────────────────────────────────────────────────────────────────────

class SiteMenuView(Container):
    """Navigation hub — shown after selecting a site."""

    _MENU_ITEMS = [
        ("⬡", "Devices",  "Network infrastructure — switches, APs, gateways", "devices"),
        ("◎", "Clients",  "Connected wired and wireless clients",              "clients"),
        ("⬢", "Networks", "VLANs and network segments",                        "networks"),
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


# ─────────────────────────────────────────────────────────────────────────────
#  ClientsView
# ─────────────────────────────────────────────────────────────────────────────

class ClientsView(Container):
    """Lists clients connected to a site."""

    _COLUMNS = ["Type", "Name", "IP Address", "MAC", "Connected", "Uplink Device"]

    def compose(self) -> ComposeResult:
        yield Static("◈  Clients", id="clients-title")
        yield DataTable(id="clients-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#clients-title", Static).update(
            f"◈  Clients  [dim]─[/dim]  [bold cyan]{site_name}[/bold cyan]"
            "  [dim]— Enter for details · ESC to go back[/dim]"
        )

    def populate(self, clients: list[dict], devices: list[dict]) -> None:
        # Build a lookup: device id → device name for uplink resolution
        dev_names: dict[str, str] = {
            d.get("id", ""): (d.get("name") or d.get("id", "—")) for d in devices
        }
        table = self.query_one(DataTable)
        table.clear()
        for client in clients:
            uplink_id   = client.get("uplinkDeviceId") or ""
            uplink_name = dev_names.get(uplink_id) or uplink_id or "—"
            table.add_row(
                _client_type_badge(client.get("type") or ""),
                str(client.get("name") or "—"),
                str(client.get("ipAddress") or "—"),
                str(client.get("macAddress") or "—"),
                _time_ago(client.get("connectedAt") or ""),
                uplink_name,
                key=client.get("id"),
            )


# ─────────────────────────────────────────────────────────────────────────────
#  NetworksView
# ─────────────────────────────────────────────────────────────────────────────

class NetworksView(Container):
    """Lists networks / VLANs configured on a site."""

    _COLUMNS = ["Name", "VLAN", "Management", "Enabled", "Default", "Origin"]

    def compose(self) -> ComposeResult:
        yield Static("◈  Networks", id="networks-title")
        yield DataTable(id="networks-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self._COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        self.query_one("#networks-title", Static).update(
            f"◈  Networks  [dim]─[/dim]  [bold cyan]{site_name}[/bold cyan]"
            "  [dim]— Enter for details · ESC to go back[/dim]"
        )

    def populate(self, networks: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for net in networks:
            origin = (net.get("metadata") or {}).get("origin") or "—"
            # Pretty-print origin: USER_DEFINED → User, SYSTEM_DEFINED → System
            origin_label = {"USER_DEFINED": "User", "SYSTEM_DEFINED": "System"}.get(origin, origin)
            table.add_row(
                str(net.get("name") or "—"),
                str(net.get("vlanId") or "—"),
                _mgmt_badge(net.get("management") or ""),
                _enabled_badge(net.get("enabled")),
                "★" if net.get("default") else "☆",
                origin_label,
                key=net.get("id"),
            )


# ─────────────────────────────────────────────────────────────────────────────
#  DevicesView
# ─────────────────────────────────────────────────────────────────────────────

class DevicesView(Container):
    """Lists devices managed by a selected site."""

    _COLUMNS = ["Status", "Name", "Model", "IP Address", "MAC", "Features", "Firmware", "Version"]

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
            # Local API field names differ from the cloud API
            state    = dev.get("state") or "—"           # "ONLINE" / "OFFLINE"
            fw_able  = dev.get("firmwareUpdatable")       # bool
            fw_label = "updateAvailable" if fw_able else "upToDate" if fw_able is not None else "—"
            features = ", ".join(dev.get("features") or []) or "—"
            table.add_row(
                _status_badge(state) if state != "—" else Text("— "),
                str(dev.get("name") or "—"),
                str(dev.get("model") or "—"),
                str(dev.get("ipAddress") or "—"),
                str(dev.get("macAddress") or "—"),
                features,
                _firmware_badge(fw_label) if fw_label != "—" else Text("— "),
                str(dev.get("firmwareVersion") or "—"),
                key=dev.get("id") or dev.get("macAddress"),
            )


# ─────────────────────────────────────────────────────────────────────────────
#  DeviceDetailView
# ─────────────────────────────────────────────────────────────────────────────

class DeviceDetailView(Container):
    """Full detail panel for a single device."""

    def compose(self) -> ComposeResult:
        yield Static("◈  Device Detail", id="detail-title")
        with VerticalScroll(id="detail-scroll"):
            yield Static("", id="detail-body")

    def show_device(self, device: dict) -> None:
        name = device.get("name") or device.get("mac") or "Unknown"
        self.query_one("#detail-title", Static).update(
            f"◈  Device  [dim]─[/dim]  [bold cyan]{name}[/bold cyan]"
            "  [dim]— ESC or /sites to go back[/dim]"
        )
        self.query_one("#detail-body", Static).update(
            _render_device_detail(device)
        )


# ─────────────────────────────────────────────────────────────────────────────
#  ClientDetailView
# ─────────────────────────────────────────────────────────────────────────────

class ClientDetailView(Container):
    """Full detail panel for a single client."""

    def compose(self) -> ComposeResult:
        yield Static("◈  Client Detail", id="client-detail-title")
        with VerticalScroll(id="client-detail-scroll"):
            yield Static("", id="client-detail-body")

    def on_show(self) -> None:
        try:
            self.query_one("#client-detail-scroll").focus()
        except Exception:
            pass

    def show_client(self, client: dict, devices: list[dict]) -> None:
        name = client.get("name") or client.get("macAddress") or "Unknown"
        self.query_one("#client-detail-title", Static).update(
            f"◈  Client  [dim]─[/dim]  [bold cyan]{name}[/bold cyan]"
            "  [dim]— ESC to go back[/dim]"
        )
        self.query_one("#client-detail-body", Static).update(
            _render_client_detail(client, devices)
        )


# ─────────────────────────────────────────────────────────────────────────────
#  NetworkDetailView
# ─────────────────────────────────────────────────────────────────────────────

class NetworkDetailView(Container):
    """Full detail panel for a single network."""

    def compose(self) -> ComposeResult:
        yield Static("◈  Network Detail", id="network-detail-title")
        with VerticalScroll(id="network-detail-scroll"):
            yield Static("", id="network-detail-body")

    def on_show(self) -> None:
        try:
            self.query_one("#network-detail-scroll").focus()
        except Exception:
            pass

    def show_network(self, network: dict) -> None:
        name = network.get("name") or "Unknown"
        self.query_one("#network-detail-title", Static).update(
            f"◈  Network  [dim]─[/dim]  [bold cyan]{name}[/bold cyan]"
            "  [dim]— ESC to go back[/dim]"
        )
        self.query_one("#network-detail-body", Static).update(
            _render_network_detail(network)
        )


def _render_device_detail(dev: dict) -> str:
    """Build a Rich-markup string with all device details in labelled sections."""

    def row(label: str, value: object, colour: str = "#e2e2e2") -> str:
        val = str(value) if value not in (None, "", {}, []) else "—"
        return f"  [dim]{label:<24}[/dim] [{colour}]{val}[/{colour}]\n"

    state   = dev.get("state") or "—"
    fw_able = dev.get("firmwareUpdatable")
    fw_label = "updateAvailable" if fw_able else "upToDate" if fw_able is not None else "—"
    s_colour  = "bright_green" if state.upper() == "ONLINE" else ("red" if state.upper() == "OFFLINE" else "yellow")
    fw_colour = "green" if fw_label == "upToDate" else ("yellow" if fw_label == "updateAvailable" else "dim")

    lines = []

    # ── Identity ─────────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Identity[/bold cyan]\n")
    lines.append(row("Name",             dev.get("name")))
    lines.append(row("ID",               dev.get("id")))
    lines.append(row("MAC Address",      dev.get("macAddress")))
    lines.append(row("Model",            dev.get("model")))
    lines.append("\n")

    # ── Status ───────────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Status[/bold cyan]\n")
    lines.append(row("State",            state,    s_colour))
    lines.append(row("Supported",        _fmt_bool(dev.get("supported"))))
    lines.append(row("Firmware Version", dev.get("firmwareVersion")))
    lines.append(row("Firmware Update",  fw_label, fw_colour))
    lines.append("\n")

    # ── Network ──────────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Network[/bold cyan]\n")
    lines.append(row("IP Address",       dev.get("ipAddress")))
    lines.append("\n")

    # ── Capabilities ─────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Capabilities[/bold cyan]\n")
    features   = dev.get("features") or []
    interfaces = dev.get("interfaces") or []
    lines.append(row("Features",         ", ".join(features) if features else "—"))
    lines.append(row("Interfaces",       ", ".join(interfaces) if interfaces else "—"))
    lines.append("\n")

    # ── Additional Fields ────────────────────────────────────────────────────
    _shown = {
        "id", "name", "macAddress", "model",
        "state", "supported", "firmwareVersion", "firmwareUpdatable",
        "ipAddress", "features", "interfaces",
    }
    extras = {k: v for k, v in dev.items() if k not in _shown and v not in (None, "", {}, [])}
    if extras:
        lines.append("[bold cyan]  Additional Fields[/bold cyan]\n")
        for k, v in extras.items():
            if isinstance(v, (dict, list)):
                lines.append(row(k, _json.dumps(v)[:120]))
            else:
                lines.append(row(k, v))

    return "".join(lines)


def _render_client_detail(client: dict, devices: list[dict]) -> str:
    """Build a Rich-markup string with all client details."""

    def row(label: str, value: object, colour: str = "#e2e2e2") -> str:
        val = str(value) if value not in (None, "", {}, []) else "—"
        return f"  [dim]{label:<24}[/dim] [{colour}]{val}[/{colour}]\n"

    dev_names: dict[str, str] = {
        d.get("id", ""): (d.get("name") or d.get("id", "—")) for d in devices
    }
    uplink_id   = client.get("uplinkDeviceId") or ""
    uplink_name = dev_names.get(uplink_id) or uplink_id or "—"
    type_str    = client.get("type") or ""
    access      = (client.get("access") or {}).get("type") or "—"

    lines = []

    lines.append("[bold cyan]  Identity[/bold cyan]\n")
    lines.append(row("Name",       client.get("name")))
    lines.append(row("ID",         client.get("id")))
    lines.append(row("MAC Address", client.get("macAddress")))
    if type_str == "WIRED":
        type_label = "[cyan]⬢ Wired[/cyan]"
    elif type_str == "WIRELESS":
        type_label = "[bright_green]⌾ Wireless[/bright_green]"
    else:
        type_label = type_str or "—"
    lines.append(f"  [dim]{'Type':<24}[/dim] {type_label}\n")
    lines.append("\n")

    lines.append("[bold cyan]  Network[/bold cyan]\n")
    lines.append(row("IP Address",    client.get("ipAddress")))
    lines.append(row("Uplink Device", uplink_name))
    lines.append(row("Uplink ID",     uplink_id))
    lines.append("\n")

    lines.append("[bold cyan]  Connection[/bold cyan]\n")
    lines.append(row("Connected",     _time_ago(client.get("connectedAt") or "")))
    lines.append(row("Connected At",  client.get("connectedAt")))
    lines.append(row("Access Type",   access))
    lines.append("\n")

    return "".join(lines)


def _render_network_detail(net: dict) -> str:
    """Build a Rich-markup string with all network details including IPv4/DHCP config."""

    def row(label: str, value: object, colour: str = "#e2e2e2") -> str:
        val = str(value) if value not in (None, "", {}, []) else "—"
        return f"  [dim]{label:<30}[/dim] [{colour}]{val}[/{colour}]\n"

    def bool_row(label: str, value: object) -> str:
        if value is True:
            return f"  [dim]{label:<30}[/dim] [bright_green]Yes[/bright_green]\n"
        if value is False:
            return f"  [dim]{label:<30}[/dim] [red]No[/red]\n"
        return f"  [dim]{label:<30}[/dim] [dim]—[/dim]\n"

    lines = []

    # ── Identity ─────────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Identity[/bold cyan]\n")
    lines.append(row("Name",        net.get("name")))
    lines.append(row("ID",          net.get("id")))
    lines.append(row("VLAN ID",     net.get("vlanId")))
    mgmt = net.get("management") or ""
    if mgmt == "GATEWAY":
        lines.append(f"  [dim]{'Management':<30}[/dim] [bright_green]⬡ Gateway[/bright_green]\n")
    elif mgmt == "UNMANAGED":
        lines.append(f"  [dim]{'Management':<30}[/dim] [yellow]○ Unmanaged[/yellow]\n")
    else:
        lines.append(row("Management", mgmt))
    lines.append(bool_row("Default", net.get("default")))
    lines.append(bool_row("Enabled", net.get("enabled")))
    lines.append("\n")

    # ── Features ─────────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Features[/bold cyan]\n")
    lines.append(bool_row("Isolation",        net.get("isolationEnabled")))
    lines.append(bool_row("Cellular Backup",  net.get("cellularBackupEnabled")))
    lines.append(bool_row("Internet Access",  net.get("internetAccessEnabled")))
    lines.append(bool_row("mDNS Forwarding",  net.get("mdnsForwardingEnabled")))
    lines.append("\n")

    # ── IPv4 Configuration ───────────────────────────────────────────────────
    ipv4 = net.get("ipv4Configuration") or {}
    if ipv4:
        lines.append("[bold cyan]  IPv4 Configuration[/bold cyan]\n")
        prefix = ipv4.get("prefixLength")
        lines.append(row("Host IP Address",   ipv4.get("hostIpAddress")))
        lines.append(row("Prefix Length",     f"/{prefix}" if prefix is not None else "—"))
        lines.append(bool_row("Auto-Scale",   ipv4.get("autoScaleEnabled")))
        lines.append("\n")

        # ── DHCP Configuration ────────────────────────────────────────────────
        dhcp = ipv4.get("dhcpConfiguration") or {}
        if dhcp:
            lines.append("[bold cyan]  DHCP Configuration[/bold cyan]\n")
            lines.append(row("Mode",              dhcp.get("mode")))
            ip_range = dhcp.get("ipAddressRange") or {}
            if ip_range:
                lines.append(row("Range Start",       ip_range.get("start")))
                lines.append(row("Range End",         ip_range.get("stop")))
            lease_secs = dhcp.get("leaseTimeSeconds")
            if lease_secs is not None:
                hours, rem = divmod(int(lease_secs), 3600)
                mins = rem // 60
                lease_label = f"{hours}h {mins}m" if hours else f"{mins}m"
                lines.append(row("Lease Time",         f"{lease_label} ({lease_secs}s)"))
            else:
                lines.append(row("Lease Time",         None))
            lines.append(row("Domain Name",        dhcp.get("domainName")))
            lines.append(bool_row("Conflict Detection", dhcp.get("pingConflictDetectionEnabled")))
            lines.append("\n")

    # ── Metadata ─────────────────────────────────────────────────────────────
    meta = net.get("metadata") or {}
    if meta:
        lines.append("[bold cyan]  Metadata[/bold cyan]\n")
        origin = meta.get("origin") or "—"
        origin_label = {"USER_DEFINED": "User", "SYSTEM_DEFINED": "System"}.get(origin, origin)
        lines.append(row("Origin",        origin_label))
        lines.append(bool_row("Configurable", meta.get("configurable")))
        lines.append("\n")

    return "".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  LoginScreen  (Modal)
# ─────────────────────────────────────────────────────────────────────────────

class LoginScreen(ModalScreen[Optional[tuple[str, str]]]):
    """Modal form for entering local Unifi Controller credentials."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Center():
            with Middle():
                with Vertical(id="login-dialog"):
                    yield Static("◈  Connect to Unifi Controller", id="login-title")
                    yield Label("Local Controller URL")
                    yield Input(value=url_history.last, id="url-input")
                    # Recent URLs list — only shown when there are saved entries
                    if url_history.urls:
                        yield Label("Recent", id="history-label")
                        yield ListView(
                            *[ListItem(Label(u), id=f"hist-{i}") for i, u in enumerate(url_history.urls)],
                            id="url-history",
                        )
                    yield Label("Local API Key")
                    yield Input(
                        placeholder="Paste your local API key here",
                        password=True,
                        id="key-input",
                    )
                    with Horizontal(id="login-buttons"):
                        yield Button("Connect", id="btn-connect", variant="primary")
                        yield Button("Cancel",  id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#key-input", Input).focus()

    @on(ListView.Selected, "#url-history")
    def _history_selected(self, event: ListView.Selected) -> None:
        """Populate URL input when a history entry is clicked."""
        label = event.item.query_one(Label)
        self.query_one("#url-input", Input).value = str(label.renderable)
        self.query_one("#key-input", Input).focus()

    @on(Button.Pressed, "#btn-connect")
    def _do_connect(self) -> None:
        url = self.query_one("#url-input", Input).value.strip()
        key = self.query_one("#key-input", Input).value.strip()
        if not url:
            self.app.notify("Controller URL is required", severity="warning")
            return
        if not key:
            self.app.notify("API Key is required", severity="warning")
            return
        self.dismiss((url, key))

    @on(Button.Pressed, "#btn-cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Input.Submitted)
    def _field_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            self.query_one("#key-input", Input).focus()
        elif event.input.id == "key-input":
            self._do_connect()


# ─────────────────────────────────────────────────────────────────────────────
#  Main Application
# ─────────────────────────────────────────────────────────────────────────────

class UnifiBrowserApp(App):
    """Unifi Browser — navigate your Unifi estate from the terminal."""

    CSS_PATH = "app.tcss"
    TITLE = "Unifi Browser"

    _client:  Optional[UnifiClient] = None
    _sites:   list[dict] = []
    _devices: list[dict] = []
    _clients: list[dict] = []
    _networks: list[dict] = []
    _current_site_id:   str = ""
    _current_site_name: str = ""

    def compose(self) -> ComposeResult:
        yield ContentSwitcher(
            WelcomeView(id="welcome"),
            SitesView(id="sites"),
            SiteMenuView(id="sitemenu"),
            DevicesView(id="devices"),
            DeviceDetailView(id="detail"),
            ClientsView(id="clients"),
            ClientDetailView(id="client-detail"),
            NetworksView(id="networks"),
            NetworkDetailView(id="network-detail"),
            initial="welcome",
            id="content",
        )
        with BottomArea(id="bottom-area"):
            yield CompletionListView(id="completions")
            yield CommandBar(id="command-bar")

    # ── Global key handling ───────────────────────────────────────────────────

    def on_key(self, event: events.Key) -> None:
        inp = self.query_one("#cmd-input", Input)

        # "/" always jumps to command input
        if event.character == "/" and not inp.has_focus:
            inp.value = "/"
            inp.cursor_position = 1
            inp.focus()
            event.stop()
            return

        # ESC: navigate back one level (only when command input is NOT focused)
        if event.key == "escape" and not inp.has_focus:
            current = self.query_one(ContentSwitcher).current
            parent = _BACK_SCREEN.get(current)
            if parent:
                self.query_one(ContentSwitcher).current = parent
                self._focus_main_content()
                event.stop()

    # ── Completions selected ──────────────────────────────────────────────────

    @on(ListView.Selected, "#completions")
    def _completion_picked(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, CompletionItem):
            self.query_one("#completions").display = False
            self.query_one("#cmd-input", Input).clear()
            self.post_message(CommandIssued(item.cmd))

    # ── Command routing ───────────────────────────────────────────────────────

    @on(CommandIssued)
    def _route_command(self, event: CommandIssued) -> None:
        match event.command:
            case "/connect":
                self._cmd_connect()
            case "/exit":
                self.exit()
            case "/help":
                self._cmd_help()
                self._focus_main_content()
            case "/sites":
                self.query_one(ContentSwitcher).current = "sites"
                self._focus_main_content()
            case "/sitemenu":
                if self._current_site_id:
                    self.query_one(ContentSwitcher).current = "sitemenu"
                    self._focus_main_content()
                else:
                    self.notify("No site selected yet — use /connect first", severity="warning")

    # ── /connect ──────────────────────────────────────────────────────────────

    @work
    async def _cmd_connect(self) -> None:
        result: Optional[tuple[str, str]] = await self.push_screen_wait(LoginScreen())
        if result is None:
            self._focus_main_content()
            return
        url, key = result
        url_history.add(url)   # persist for next session
        if self._client is not None:
            await self._client.close()
        self._client = UnifiClient(url, key)
        self.notify("Connecting to Unifi Controller…", severity="information", timeout=3)
        self._load_sites()

    # ── /help ─────────────────────────────────────────────────────────────────

    def _cmd_help(self) -> None:
        lines = ["[bold]Available commands:[/bold]\n"]
        for cmd, desc in COMMANDS.items():
            lines.append(f"  [bold cyan]{cmd}[/bold cyan]  {desc}")
        self.notify("\n".join(lines), timeout=8, title="Help")

    # ── Focus helper ──────────────────────────────────────────────────────────

    def _focus_main_content(self) -> None:
        current = self.query_one(ContentSwitcher).current
        table_map = {
            "sites":    "#sites-table",
            "sitemenu": "#sitemenu-table",
            "devices":  "#devices-table",
            "clients":  "#clients-table",
            "networks": "#networks-table",
        }
        scroll_map = {
            "detail":         "#detail-scroll",
            "client-detail":  "#client-detail-scroll",
            "network-detail": "#network-detail-scroll",
        }
        if current in table_map:
            try:
                self.query_one(table_map[current], DataTable).focus()
            except Exception:
                pass
        elif current in scroll_map:
            try:
                self.query_one(scroll_map[current]).focus()
            except Exception:
                pass

    # ── Site row selected → show site menu ───────────────────────────────────

    @on(DataTable.RowSelected, "#sites-table")
    def _site_row_selected(self, event: DataTable.RowSelected) -> None:
        site_id = str(event.row_key.value)
        site_name = next(
            (s.get("name") or site_id for s in self._sites if s.get("id") == site_id),
            site_id,
        )
        self._current_site_id   = site_id
        self._current_site_name = site_name
        sm = self.query_one("#sitemenu", SiteMenuView)
        sm.set_site(site_name)
        self.query_one(ContentSwitcher).current = "sitemenu"
        self._focus_main_content()

    # ── Site menu item selected ────────────────────────────────────────────────

    @on(DataTable.RowSelected, "#sitemenu-table")
    def _sitemenu_selected(self, event: DataTable.RowSelected) -> None:
        match str(event.row_key.value):
            case "devices":
                self._load_devices(self._current_site_id, self._current_site_name)
            case "clients":
                self._load_clients(self._current_site_id, self._current_site_name)
            case "networks":
                self._load_networks(self._current_site_id, self._current_site_name)

    # ── Device row selected ───────────────────────────────────────────────────

    @on(DataTable.RowSelected, "#devices-table")
    def _device_row_selected(self, event: DataTable.RowSelected) -> None:
        dev_key = str(event.row_key.value)
        device = next(
            (d for d in self._devices
             if (d.get("id") or d.get("mac")) == dev_key),
            None,
        )
        if device is None:
            self.notify("Device data not found", severity="warning")
            return
        dv = self.query_one("#detail", DeviceDetailView)
        dv.show_device(device)
        self.query_one(ContentSwitcher).current = "detail"
        try:
            self.query_one("#detail-scroll").focus()
        except Exception:
            pass

    @on(DataTable.RowSelected, "#clients-table")
    def _client_row_selected(self, event: DataTable.RowSelected) -> None:
        client_id = str(event.row_key.value)
        client = next(
            (c for c in self._clients if c.get("id") == client_id),
            None,
        )
        if client is None:
            self.notify("Client data not found", severity="warning")
            return
        cdv = self.query_one("#client-detail", ClientDetailView)
        cdv.show_client(client, self._devices)
        self.query_one(ContentSwitcher).current = "client-detail"

    @on(DataTable.RowSelected, "#networks-table")
    def _network_row_selected(self, event: DataTable.RowSelected) -> None:
        network_id = str(event.row_key.value)
        self._load_network_detail(network_id)

    # ── Worker: load sites ────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _load_sites(self) -> None:
        assert self._client is not None
        try:
            sites = await self._client.get_sites()
        except httpx.HTTPStatusError as exc:
            self.notify(
                f"HTTP {exc.response.status_code}: {exc.response.text[:120]}",
                severity="error", timeout=10,
            )
            return
        except Exception as exc:
            self.notify(f"Connection failed: {exc}", severity="error", timeout=10)
            return

        self._sites = sites
        self.query_one("#sites", SitesView).populate(sites)
        self.query_one(ContentSwitcher).current = "sites"
        self.notify(f"Loaded [bold]{len(sites)}[/bold] site(s)", severity="information")
        self._focus_main_content()

    # ── Worker: load devices for a site ──────────────────────────────────────

    @work(exclusive=True)
    async def _load_devices(self, site_id: str, site_name: str) -> None:
        assert self._client is not None
        self.notify(f"Loading devices for [bold]{site_name}[/bold]…", timeout=3)
        try:
            devices = await self._client.get_devices(site_id)
        except httpx.HTTPStatusError as exc:
            self.notify(
                f"HTTP {exc.response.status_code}: {exc.response.text[:120]}",
                severity="error", timeout=10,
            )
            return
        except Exception as exc:
            self.notify(f"Request failed: {exc}", severity="error", timeout=10)
            return

        self._devices = devices
        dv = self.query_one("#devices", DevicesView)
        dv.set_site(site_name)
        dv.populate(devices)
        self.query_one(ContentSwitcher).current = "devices"
        self.notify(
            f"[bold]{len(devices)}[/bold] device(s) on [bold]{site_name}[/bold]",
            severity="information",
        )
        self._focus_main_content()

    # ── Worker: load clients for a site ──────────────────────────────────────

    @work(exclusive=True)
    async def _load_clients(self, site_id: str, site_name: str) -> None:
        assert self._client is not None
        self.notify(f"Loading clients for [bold]{site_name}[/bold]…", timeout=3)
        try:
            clients = await self._client.get_clients(site_id)
        except httpx.HTTPStatusError as exc:
            self.notify(
                f"HTTP {exc.response.status_code}: {exc.response.text[:120]}",
                severity="error", timeout=10,
            )
            return
        except Exception as exc:
            self.notify(f"Request failed: {exc}", severity="error", timeout=10)
            return

        self._clients = clients
        cv = self.query_one("#clients", ClientsView)
        cv.set_site(site_name)
        cv.populate(clients, self._devices)
        self.query_one(ContentSwitcher).current = "clients"
        self.notify(
            f"[bold]{len(clients)}[/bold] client(s) on [bold]{site_name}[/bold]",
            severity="information",
        )
        self._focus_main_content()

    # ── Worker: load networks for a site ─────────────────────────────────────

    @work(exclusive=True)
    async def _load_networks(self, site_id: str, site_name: str) -> None:
        assert self._client is not None
        self.notify(f"Loading networks for [bold]{site_name}[/bold]…", timeout=3)
        try:
            networks = await self._client.get_networks(site_id)
        except httpx.HTTPStatusError as exc:
            self.notify(
                f"HTTP {exc.response.status_code}: {exc.response.text[:120]}",
                severity="error", timeout=10,
            )
            return
        except Exception as exc:
            self.notify(f"Request failed: {exc}", severity="error", timeout=10)
            return

        self._networks = networks
        nv = self.query_one("#networks", NetworksView)
        nv.set_site(site_name)
        nv.populate(networks)
        self.query_one(ContentSwitcher).current = "networks"
        self.notify(
            f"[bold]{len(networks)}[/bold] network(s) on [bold]{site_name}[/bold]",
            severity="information",
        )
        self._focus_main_content()

    @work(exclusive=True)
    async def _load_network_detail(self, network_id: str) -> None:
        assert self._client is not None
        # Try cached first for quick display, then fetch full detail
        cached = next((n for n in self._networks if n.get("id") == network_id), None)
        if cached:
            ndv = self.query_one("#network-detail", NetworkDetailView)
            ndv.show_network(cached)
            self.query_one(ContentSwitcher).current = "network-detail"

        try:
            full = await self._client.get_network(self._current_site_id, network_id)
        except Exception as exc:
            if cached is None:
                self.notify(f"Failed to load network detail: {exc}", severity="error", timeout=10)
            return

        ndv = self.query_one("#network-detail", NetworkDetailView)
        ndv.show_network(full)
        if self.query_one(ContentSwitcher).current != "network-detail":
            self.query_one(ContentSwitcher).current = "network-detail"

    async def on_unmount(self) -> None:
        if self._client is not None:
            await self._client.close()


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    UnifiBrowserApp().run()
