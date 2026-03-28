"""
UnifiBrowserApp — the Textual application and its controller logic.
Supports both Local (direct controller) and Remote (Unifi Cloud) modes.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

import httpx
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.widgets import ContentSwitcher, DataTable

from unifi_browser.api.client import UnifiClient, url_history
from unifi_browser.api.remote_client import RemoteUnifiClient, remote_url_history
from unifi_browser.constants import BACK_SCREEN, COMMANDS, REMOTE_BACK_SCREEN
from unifi_browser.views.clients import ClientDetailView, ClientsView
from unifi_browser.views.devices import DeviceDetailView, DevicesView
from unifi_browser.views.networks import NetworkDetailView, NetworksView
from unifi_browser.views.wans import WansView
from unifi_browser.views.remote.hosts import RemoteControllerDetailView, RemoteHostDetailView, RemoteHostsView
from unifi_browser.views.remote.isp_metrics import IspMetricsView
from unifi_browser.views.remote.clients import RemoteClientDetailView, RemoteClientsView
from unifi_browser.views.remote.devices import RemoteDeviceDetailView, RemoteDevicesView
from unifi_browser.views.remote.networks import RemoteNetworkDetailView, RemoteNetworksView
from unifi_browser.views.remote.site_menu import RemoteSiteMenuView
from unifi_browser.views.remote.sites import RemoteSitesView
from unifi_browser.views.remote.welcome import RemoteWelcomeView
from unifi_browser.views.remote.wifi import RemoteWifiDetailView, RemoteWifiView
from unifi_browser.views.remote.wans import RemoteWansView
from unifi_browser.views.site_menu import SiteMenuView
from unifi_browser.views.sites import SitesView
from unifi_browser.views.welcome import WelcomeView
from unifi_browser.views.wifi import WifiDetailView, WifiView
from unifi_browser.widgets.command_bar import BottomArea, CommandBar, CommandIssued, CompletionListView
from unifi_browser.widgets.help_screen import HelpScreen
from unifi_browser.widgets.login import LoginScreen
from unifi_browser.widgets.tab_bar import TabBar


class UnifiBrowserApp(App):
    """Unifi Browser — navigate your Unifi estate from the terminal."""

    CSS_PATH = Path(__file__).parent.parent / "app.tcss"
    TITLE = "Unifi Browser"

    # ── Local state ────────────────────────────────────────────────────────────
    _client:          Optional[UnifiClient] = None
    _sites:           list[dict] = []
    _devices:         list[dict] = []
    _clients:         list[dict] = []
    _networks:        list[dict] = []
    _wifi_broadcasts: list[dict] = []
    _wans:            list[dict] = []
    _current_site_id:   str = ""
    _current_site_name: str = ""

    # ── Remote state ───────────────────────────────────────────────────────────
    _remote_client:             Optional[RemoteUnifiClient] = None
    _remote_sites:              list[dict] = []
    _remote_devices:            list[dict] = []
    _remote_clients:            list[dict] = []
    _remote_networks:           list[dict] = []
    _remote_wifi_broadcasts:    list[dict] = []
    _remote_wans:               list[dict] = []
    _remote_hosts:              list[dict] = []
    _remote_selected_host_id:   str = ""
    _remote_selected_site_id:   str = ""   # network-API site ID
    _remote_selected_site_name: str = ""

    # ── Mode ───────────────────────────────────────────────────────────────────
    _active_mode: str = "local"

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield TabBar(id="tab-bar")
        yield ContentSwitcher(
            # Local views
            WelcomeView(id="welcome"),
            SitesView(id="sites"),
            SiteMenuView(id="sitemenu"),
            DevicesView(id="devices"),
            DeviceDetailView(id="detail"),
            ClientsView(id="clients"),
            ClientDetailView(id="client-detail"),
            NetworksView(id="networks"),
            NetworkDetailView(id="network-detail"),
            WifiView(id="wifi"),
            WifiDetailView(id="wifi-detail"),
            WansView(id="wans"),
            # Remote views
            RemoteWelcomeView(id="r-welcome"),
            RemoteSitesView(id="r-sites"),
            RemoteSiteMenuView(id="r-sitemenu"),
            RemoteDevicesView(id="r-devices"),
            RemoteDeviceDetailView(id="r-detail"),
            RemoteClientsView(id="r-clients"),
            RemoteClientDetailView(id="r-client-detail"),
            RemoteNetworksView(id="r-networks"),
            RemoteNetworkDetailView(id="r-network-detail"),
            RemoteWifiView(id="r-wifi"),
            RemoteWifiDetailView(id="r-wifi-detail"),
            RemoteWansView(id="r-wans"),
            RemoteHostsView(id="r-hosts"),
            RemoteHostDetailView(id="r-host-detail"),
            RemoteControllerDetailView(id="r-controller"),
            IspMetricsView(id="r-isp-metrics"),
            initial="welcome",
            id="content",
        )
        with BottomArea(id="bottom-area"):
            yield CompletionListView(id="completions")
            yield CommandBar(id="command-bar")

    # ── Mode switching ────────────────────────────────────────────────────────

    def _switch_mode(self, mode: str) -> None:
        """Switch the active tab and update the ContentSwitcher."""
        self._active_mode = mode
        tab_bar = self.query_one(TabBar)
        tab_bar.active = mode
        switcher = self.query_one(ContentSwitcher)
        # Navigate to the appropriate "home" screen for this mode
        if mode == "local":
            current = switcher.current or ""
            if not current.startswith("r-") and current:
                pass  # stay on current local screen
            else:
                switcher.current = "sites" if self._client else "welcome"
        else:
            current = switcher.current or ""
            if current.startswith("r-") and current:
                pass  # stay on current remote screen
            else:
                switcher.current = "r-sites" if self._remote_client else "r-welcome"
        self._focus_main_content()

    # ── Global key handling ───────────────────────────────────────────────────

    def on_key(self, event: events.Key) -> None:
        inp = self.query_one("#cmd-input")

        if event.character == "/" and not inp.has_focus:
            inp.value = "/"
            inp.focus()
            self.call_after_refresh(lambda: setattr(inp, "cursor_position", 1))
            event.stop()
            return

        # Tab switching — fires when input is not focused
        if not inp.has_focus:
            if event.key == "l":
                self._switch_mode("local")
                event.stop()
                return
            if event.key == "r":
                self._switch_mode("remote")
                event.stop()
                return
            # I = ISP Metrics shortcut (remote mode, when connected)
            if event.key == "i" and self._active_mode == "remote" and self._remote_client:
                self._load_isp_metrics()
                event.stop()
                return
            # H = All Hosts shortcut (remote mode, when connected)
            if event.key == "h" and self._active_mode == "remote" and self._remote_client:
                self._load_remote_hosts()
                event.stop()
                return

        if event.key == "escape" and not inp.has_focus:
            current = self.query_one(ContentSwitcher).current
            # Check remote back-nav first, then local
            parent = REMOTE_BACK_SCREEN.get(current) or BACK_SCREEN.get(current)
            if parent:
                self.query_one(ContentSwitcher).current = parent
                self._focus_main_content()
                event.stop()

    # ── Tab bar clicks ────────────────────────────────────────────────────────

    @on(TabBar.TabSelected)
    def _tab_selected(self, event: TabBar.TabSelected) -> None:
        self._switch_mode(event.mode)

    # ── Completions selected ──────────────────────────────────────────────────

    @on(CompletionListView.Selected, "#completions")
    def _completion_picked(self, event: CompletionListView.Selected) -> None:
        from unifi_browser.widgets.command_bar import CompletionItem
        item = event.item
        if isinstance(item, CompletionItem):
            self.query_one("#completions").display = False
            self.query_one("#cmd-input").clear()
            self.post_message(CommandIssued(item.cmd))

    # ── Command routing ───────────────────────────────────────────────────────

    @on(CommandIssued)
    def _route_command(self, event: CommandIssued) -> None:
        cmd = event.command
        match cmd:
            case "/connect":
                # Default to whichever tab is currently active
                self._cmd_connect(self._active_mode)
            case "/connect local":
                self._switch_mode("local")
                self._cmd_connect("local")
            case "/connect remote":
                self._switch_mode("remote")
                self._cmd_connect("remote")
            case "/local":
                self._switch_mode("local")
                self._focus_main_content()
            case "/remote":
                self._switch_mode("remote")
                self._focus_main_content()
            case "/isp":
                if self._active_mode != "remote":
                    self.notify("ISP Metrics requires remote mode — press R first", severity="warning")
                elif not self._remote_client:
                    self.notify("Not connected to remote — use /connect remote", severity="warning")
                else:
                    self._load_isp_metrics()
            case "/exit":
                self.exit()
            case "/help":
                self._cmd_help()
            case "/sites":
                if self._active_mode == "remote":
                    if self._remote_client:
                        self.query_one(ContentSwitcher).current = "r-sites"
                    else:
                        self.notify("Not connected to remote — use /connect remote", severity="warning")
                else:
                    if self._client:
                        self.query_one(ContentSwitcher).current = "sites"
                    else:
                        self.notify("Not connected — use /connect", severity="warning")
                self._focus_main_content()
            case "/sitemenu":
                if self._active_mode == "remote":
                    if self._remote_selected_site_id:
                        self.query_one(ContentSwitcher).current = "r-sitemenu"
                        self._focus_main_content()
                    else:
                        self.notify("No remote site selected yet", severity="warning")
                else:
                    if self._current_site_id:
                        self.query_one(ContentSwitcher).current = "sitemenu"
                        self._focus_main_content()
                    else:
                        self.notify("No site selected yet — use /connect first", severity="warning")

    # ── /connect ──────────────────────────────────────────────────────────────

    @work
    async def _cmd_connect(self, mode: str = "local") -> None:
        result: Optional[tuple[str, str]] = await self.push_screen_wait(LoginScreen(mode=mode))
        if result is None:
            self._focus_main_content()
            return
        url, key = result
        if mode == "remote":
            remote_url_history.add(url)
            if self._remote_client is not None:
                await self._remote_client.close()
            self._remote_client = RemoteUnifiClient(url, key)
            self.notify("Connecting to Unifi Cloud…", severity="information", timeout=2)
            self._load_remote_sites()
        else:
            url_history.add(url)
            if self._client is not None:
                await self._client.close()
            self._client = UnifiClient(url, key)
            self.notify("Connecting to Unifi Controller…", severity="information", timeout=2)
            self._load_sites()

    # ── /help ─────────────────────────────────────────────────────────────────

    @work
    async def _cmd_help(self) -> None:
        await self.push_screen_wait(HelpScreen())
        self._focus_main_content()

    # ── Focus helper ──────────────────────────────────────────────────────────

    def _focus_main_content(self) -> None:
        current = self.query_one(ContentSwitcher).current
        table_map = {
            "sites":       "#sites-table",
            "sitemenu":    "#sitemenu-table",
            "devices":     "#devices-table",
            "clients":     "#clients-table",
            "networks":    "#networks-table",
            "wifi":        "#wifi-table",
            "wans":        "#wans-table",
            "r-sites":     "#r-sites-table",
            "r-sitemenu":  "#r-sitemenu-table",
            "r-devices":   "#r-devices-table",
            "r-clients":   "#r-clients-table",
            "r-networks":  "#r-networks-table",
            "r-wifi":      "#r-wifi-table",
            "r-wans":      "#r-wans-table",
            "r-hosts":     "#r-hosts-table",
        }
        scroll_map = {
            "detail":              "#detail-scroll",
            "client-detail":       "#client-detail-scroll",
            "network-detail":      "#network-detail-scroll",
            "wifi-detail":         "#wifi-detail-scroll",
            "r-detail":            "#r-detail-scroll",
            "r-client-detail":     "#r-client-detail-scroll",
            "r-network-detail":    "#r-network-detail-scroll",
            "r-wifi-detail":       "#r-wifi-detail-scroll",
            "r-isp-metrics":       "#r-isp-scroll",
            "r-controller":        "#r-controller-scroll",
            "r-host-detail":       "#r-host-detail-scroll",
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

    # ── Error-handling wrapper ────────────────────────────────────────────────

    async def _api_call(self, coro) -> Any | None:
        """Await *coro*, notify on error, and return None on failure."""
        try:
            return await coro
        except httpx.HTTPStatusError as exc:
            self.notify(
                f"HTTP {exc.response.status_code}: {exc.response.text[:120]}",
                severity="error", timeout=10,
            )
        except Exception as exc:
            self.notify(f"Request failed: {exc}", severity="error", timeout=10)
        return None

    # ════════════════════════════════════════════════════════════════════════
    #  LOCAL event handlers
    # ════════════════════════════════════════════════════════════════════════

    @on(DataTable.RowSelected, "#sites-table")
    def _site_row_selected(self, event: DataTable.RowSelected) -> None:
        site_id = str(event.row_key.value)
        site_name = next(
            (s.get("name") or site_id for s in self._sites if s.get("id") == site_id),
            site_id,
        )
        self._current_site_id   = site_id
        self._current_site_name = site_name
        self.query_one("#sitemenu", SiteMenuView).set_site(site_name)
        self.query_one(ContentSwitcher).current = "sitemenu"

    @on(DataTable.RowSelected, "#sitemenu-table")
    def _sitemenu_selected(self, event: DataTable.RowSelected) -> None:
        match str(event.row_key.value):
            case "devices":
                self._load_devices(self._current_site_id, self._current_site_name)
            case "clients":
                self._load_clients(self._current_site_id, self._current_site_name)
            case "networks":
                self._load_networks(self._current_site_id, self._current_site_name)
            case "wifi":
                self._load_wifi(self._current_site_id, self._current_site_name)
            case "wans":
                self._load_wans(self._current_site_id, self._current_site_name)

    @on(DataTable.RowSelected, "#devices-table")
    def _device_row_selected(self, event: DataTable.RowSelected) -> None:
        dev_key = str(event.row_key.value)
        device = next(
            (d for d in self._devices if (d.get("id") or d.get("mac")) == dev_key),
            None,
        )
        if device is None:
            self.notify("Device data not found", severity="warning")
            return
        self.query_one("#detail", DeviceDetailView).show_device(device)
        self.query_one(ContentSwitcher).current = "detail"

    @on(DataTable.RowSelected, "#clients-table")
    def _client_row_selected(self, event: DataTable.RowSelected) -> None:
        client_id = str(event.row_key.value)
        client = next((c for c in self._clients if c.get("id") == client_id), None)
        if client is None:
            self.notify("Client data not found", severity="warning")
            return
        self.query_one("#client-detail", ClientDetailView).show_client(client, self._devices)
        self.query_one(ContentSwitcher).current = "client-detail"

    @on(DataTable.RowSelected, "#networks-table")
    def _network_row_selected(self, event: DataTable.RowSelected) -> None:
        self._load_network_detail(str(event.row_key.value))

    @on(DataTable.RowSelected, "#wifi-table")
    def _wifi_row_selected(self, event: DataTable.RowSelected) -> None:
        self._load_wifi_detail(str(event.row_key.value))

    # ════════════════════════════════════════════════════════════════════════
    #  REMOTE event handlers
    # ════════════════════════════════════════════════════════════════════════

    @on(DataTable.RowSelected, "#r-sites-table")
    def _remote_site_row_selected(self, event: DataTable.RowSelected) -> None:
        site_id = str(event.row_key.value)  # this is the siteId (cloud API)
        site = next((s for s in self._remote_sites if s.get("siteId") == site_id), None)
        if site is None:
            self.notify("Site data not found", severity="warning")
            return
        host_id    = site.get("hostId", "")
        site_name  = (
            (site.get("meta") or {}).get("desc")
            or (site.get("_hostInfo") or {}).get("reportedState", {}).get("hostname")
            or site_id
        )
        self._remote_selected_host_id   = host_id
        self._remote_selected_site_name = site_name
        self._remote_selected_site_id   = ""  # resolved async below
        self._load_remote_site_menu(host_id, site_name)

    @on(DataTable.RowSelected, "#r-sitemenu-table")
    def _remote_sitemenu_selected(self, event: DataTable.RowSelected) -> None:
        match str(event.row_key.value):
            case "r-devices":
                self._load_remote_devices()
            case "r-clients":
                self._load_remote_clients()
            case "r-networks":
                self._load_remote_networks()
            case "r-wifi":
                self._load_remote_wifi()
            case "r-wans":
                self._load_remote_wans()
            case "r-controller":
                self._load_remote_controller()

    @on(DataTable.RowSelected, "#r-devices-table")
    def _remote_device_row_selected(self, event: DataTable.RowSelected) -> None:
        dev_key = str(event.row_key.value)
        device = next(
            (d for d in self._remote_devices if (d.get("id") or d.get("mac")) == dev_key),
            None,
        )
        if device is None:
            self.notify("Device data not found", severity="warning")
            return
        self.query_one("#r-detail", RemoteDeviceDetailView).show_device(device)
        self.query_one(ContentSwitcher).current = "r-detail"

    @on(DataTable.RowSelected, "#r-clients-table")
    def _remote_client_row_selected(self, event: DataTable.RowSelected) -> None:
        client_id = str(event.row_key.value)
        client = next((c for c in self._remote_clients if c.get("id") == client_id), None)
        if client is None:
            self.notify("Client data not found", severity="warning")
            return
        self.query_one("#r-client-detail", RemoteClientDetailView).show_client(
            client, self._remote_devices
        )
        self.query_one(ContentSwitcher).current = "r-client-detail"

    @on(DataTable.RowSelected, "#r-networks-table")
    def _remote_network_row_selected(self, event: DataTable.RowSelected) -> None:
        self._load_remote_network_detail(str(event.row_key.value))

    @on(DataTable.RowSelected, "#r-wifi-table")
    def _remote_wifi_row_selected(self, event: DataTable.RowSelected) -> None:
        self._load_remote_wifi_detail(str(event.row_key.value))

    @on(DataTable.RowSelected, "#r-hosts-table")
    def _remote_host_row_selected(self, event: DataTable.RowSelected) -> None:
        host_id = str(event.row_key.value)
        host = next((h for h in self._remote_hosts if h.get("id") == host_id), None)
        if host is None:
            self.notify("Host data not found", severity="warning")
            return
        dv = self.query_one("#r-host-detail", RemoteHostDetailView)
        dv.show_host(host)
        self.query_one(ContentSwitcher).current = "r-host-detail"
        self._focus_main_content()

    # ════════════════════════════════════════════════════════════════════════
    #  LOCAL workers
    # ════════════════════════════════════════════════════════════════════════

    @work(exclusive=True)
    async def _load_sites(self) -> None:
        assert self._client is not None
        sites = await self._api_call(self._client.get_sites())
        if sites is None:
            return
        self._sites = sites
        self.query_one("#sites", SitesView).populate(sites)
        self.query_one(ContentSwitcher).current = "sites"
        self.query_one(TabBar).local_connected = True
        self.notify(f"Loaded [bold]{len(sites)}[/bold] site(s)", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_devices(self, site_id: str, site_name: str) -> None:
        assert self._client is not None
        self.notify(f"Loading devices for [bold]{site_name}[/bold]…", timeout=2)
        devices = await self._api_call(self._client.get_devices(site_id))
        if devices is None:
            return
        self._devices = devices
        dv = self.query_one("#devices", DevicesView)
        dv.set_site(site_name)
        dv.populate(devices)
        self.query_one(ContentSwitcher).current = "devices"
        self.notify(f"[bold]{len(devices)}[/bold] device(s) on [bold]{site_name}[/bold]", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_clients(self, site_id: str, site_name: str) -> None:
        assert self._client is not None
        self.notify(f"Loading clients for [bold]{site_name}[/bold]…", timeout=2)
        clients, devices = await asyncio.gather(
            self._api_call(self._client.get_clients(site_id)),
            self._api_call(self._client.get_devices(site_id)),
        )
        if clients is None:
            return
        self._clients = clients
        if devices is not None:
            self._devices = devices
        cv = self.query_one("#clients", ClientsView)
        cv.set_site(site_name)
        cv.populate(clients, self._devices)
        self.query_one(ContentSwitcher).current = "clients"
        self.notify(f"[bold]{len(clients)}[/bold] client(s) on [bold]{site_name}[/bold]", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_networks(self, site_id: str, site_name: str) -> None:
        assert self._client is not None
        self.notify(f"Loading networks for [bold]{site_name}[/bold]…", timeout=2)
        networks = await self._api_call(self._client.get_networks(site_id))
        if networks is None:
            return
        self._networks = networks
        nv = self.query_one("#networks", NetworksView)
        nv.set_site(site_name)
        nv.populate(networks)
        self.query_one(ContentSwitcher).current = "networks"
        self.notify(f"[bold]{len(networks)}[/bold] network(s) on [bold]{site_name}[/bold]", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_network_detail(self, network_id: str) -> None:
        assert self._client is not None
        cached = next((n for n in self._networks if n.get("id") == network_id), None)
        if cached:
            self.query_one("#network-detail", NetworkDetailView).show_network(cached)
            self.query_one(ContentSwitcher).current = "network-detail"
        full = await self._api_call(self._client.get_network(self._current_site_id, network_id))
        if full is None:
            return
        self.query_one("#network-detail", NetworkDetailView).show_network(full)
        self.query_one(ContentSwitcher).current = "network-detail"

    @work(exclusive=True)
    async def _load_wifi(self, site_id: str, site_name: str) -> None:
        assert self._client is not None
        self.notify(f"Loading WiFi for [bold]{site_name}[/bold]…", timeout=2)
        broadcasts = await self._api_call(self._client.get_wifi_broadcasts(site_id))
        if broadcasts is None:
            return
        self._wifi_broadcasts = broadcasts
        wv = self.query_one("#wifi", WifiView)
        wv.set_site(site_name)
        wv.populate(broadcasts)
        self.query_one(ContentSwitcher).current = "wifi"
        self.notify(f"[bold]{len(broadcasts)}[/bold] WiFi broadcast(s) on [bold]{site_name}[/bold]", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_wifi_detail(self, broadcast_id: str) -> None:
        assert self._client is not None
        cached = next((b for b in self._wifi_broadcasts if b.get("id") == broadcast_id), None)
        if cached:
            self.query_one("#wifi-detail", WifiDetailView).show_wifi(cached)
            self.query_one(ContentSwitcher).current = "wifi-detail"
        full = await self._api_call(
            self._client.get_wifi_broadcast(self._current_site_id, broadcast_id)
        )
        if full is None:
            return
        self.query_one("#wifi-detail", WifiDetailView).show_wifi(full)
        self.query_one(ContentSwitcher).current = "wifi-detail"

    @work(exclusive=True)
    async def _load_wans(self, site_id: str, site_name: str) -> None:
        assert self._client is not None
        self.notify(f"Loading WAN interfaces for [bold]{site_name}[/bold]…", timeout=2)
        wans = await self._api_call(self._client.get_wans(site_id))
        if wans is None:
            return
        self._wans = wans
        wv = self.query_one("#wans", WansView)
        wv.set_site(site_name)
        wv.populate(wans)
        self.query_one(ContentSwitcher).current = "wans"
        self.notify(f"[bold]{len(wans)}[/bold] WAN interface(s) on [bold]{site_name}[/bold]", severity="information", timeout=2)

    # ════════════════════════════════════════════════════════════════════════
    #  REMOTE workers
    # ════════════════════════════════════════════════════════════════════════

    @work(exclusive=True)
    async def _load_remote_sites(self) -> None:
        assert self._remote_client is not None
        self.notify("Loading Unifi Cloud sites…", timeout=3)
        sites = await self._api_call(self._remote_client.get_sites())
        if sites is None:
            return
        self._remote_sites = sites
        self.query_one("#r-sites", RemoteSitesView).populate(sites)
        self.query_one(ContentSwitcher).current = "r-sites"
        self.query_one(TabBar).remote_connected = True
        self.notify(f"Loaded [bold]{len(sites)}[/bold] remote site(s)", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_remote_site_menu(self, host_id: str, site_name: str) -> None:
        """Resolve the network-API site ID from the host, then show the site menu."""
        assert self._remote_client is not None
        self.notify(f"Loading site [bold]{site_name}[/bold]…", timeout=3)
        network_sites = await self._api_call(self._remote_client.get_network_sites(host_id))
        if network_sites is None:
            return
        # Pick the first available network site (most hosts have exactly one)
        if not network_sites:
            self.notify("No network sites found for this host", severity="warning")
            return
        network_site_id = network_sites[0].get("id", "")
        self._remote_selected_site_id = network_site_id
        sm = self.query_one("#r-sitemenu", RemoteSiteMenuView)
        sm.set_site(site_name)
        self.query_one(ContentSwitcher).current = "r-sitemenu"

    @work(exclusive=True)
    async def _load_remote_devices(self) -> None:
        assert self._remote_client is not None
        host_id = self._remote_selected_host_id
        site_id = self._remote_selected_site_id
        site_name = self._remote_selected_site_name
        self.notify(f"Loading remote devices for [bold]{site_name}[/bold]…", timeout=2)
        devices = await self._api_call(self._remote_client.get_devices(host_id, site_id))
        if devices is None:
            return
        self._remote_devices = devices
        dv = self.query_one("#r-devices", RemoteDevicesView)
        dv.set_site(site_name)
        dv.populate(devices)
        self.query_one(ContentSwitcher).current = "r-devices"
        self.notify(f"[bold]{len(devices)}[/bold] remote device(s)", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_remote_clients(self) -> None:
        assert self._remote_client is not None
        host_id   = self._remote_selected_host_id
        site_id   = self._remote_selected_site_id
        site_name = self._remote_selected_site_name
        self.notify(f"Loading remote clients for [bold]{site_name}[/bold]…", timeout=2)
        clients, devices = await asyncio.gather(
            self._api_call(self._remote_client.get_clients(host_id, site_id)),
            self._api_call(self._remote_client.get_devices(host_id, site_id)),
        )
        if clients is None:
            return
        self._remote_clients = clients
        if devices is not None:
            self._remote_devices = devices
        cv = self.query_one("#r-clients", RemoteClientsView)
        cv.set_site(site_name)
        cv.populate(clients, self._remote_devices)
        self.query_one(ContentSwitcher).current = "r-clients"
        self.notify(f"[bold]{len(clients)}[/bold] remote client(s)", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_remote_networks(self) -> None:
        assert self._remote_client is not None
        host_id   = self._remote_selected_host_id
        site_id   = self._remote_selected_site_id
        site_name = self._remote_selected_site_name
        self.notify(f"Loading remote networks for [bold]{site_name}[/bold]…", timeout=2)
        networks = await self._api_call(self._remote_client.get_networks(host_id, site_id))
        if networks is None:
            return
        self._remote_networks = networks
        nv = self.query_one("#r-networks", RemoteNetworksView)
        nv.set_site(site_name)
        nv.populate(networks)
        self.query_one(ContentSwitcher).current = "r-networks"
        self.notify(f"[bold]{len(networks)}[/bold] remote network(s)", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_remote_network_detail(self, network_id: str) -> None:
        assert self._remote_client is not None
        host_id = self._remote_selected_host_id
        site_id = self._remote_selected_site_id
        cached = next((n for n in self._remote_networks if n.get("id") == network_id), None)
        if cached:
            self.query_one("#r-network-detail", RemoteNetworkDetailView).show_network(cached)
            self.query_one(ContentSwitcher).current = "r-network-detail"
        full = await self._api_call(
            self._remote_client.get_network(host_id, site_id, network_id)
        )
        if full is None:
            return
        self.query_one("#r-network-detail", RemoteNetworkDetailView).show_network(full)
        self.query_one(ContentSwitcher).current = "r-network-detail"

    @work(exclusive=True)
    async def _load_remote_wifi(self) -> None:
        assert self._remote_client is not None
        host_id   = self._remote_selected_host_id
        site_id   = self._remote_selected_site_id
        site_name = self._remote_selected_site_name
        self.notify(f"Loading remote WiFi for [bold]{site_name}[/bold]…", timeout=2)
        broadcasts = await self._api_call(
            self._remote_client.get_wifi_broadcasts(host_id, site_id)
        )
        if broadcasts is None:
            return
        self._remote_wifi_broadcasts = broadcasts
        wv = self.query_one("#r-wifi", RemoteWifiView)
        wv.set_site(site_name)
        wv.populate(broadcasts)
        self.query_one(ContentSwitcher).current = "r-wifi"
        self.notify(f"[bold]{len(broadcasts)}[/bold] remote WiFi broadcast(s)", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_remote_wifi_detail(self, broadcast_id: str) -> None:
        assert self._remote_client is not None
        host_id = self._remote_selected_host_id
        site_id = self._remote_selected_site_id
        cached = next((b for b in self._remote_wifi_broadcasts if b.get("id") == broadcast_id), None)
        if cached:
            self.query_one("#r-wifi-detail", RemoteWifiDetailView).show_wifi(cached)
            self.query_one(ContentSwitcher).current = "r-wifi-detail"
        full = await self._api_call(
            self._remote_client.get_wifi_broadcast(host_id, site_id, broadcast_id)
        )
        if full is None:
            return
        self.query_one("#r-wifi-detail", RemoteWifiDetailView).show_wifi(full)
        self.query_one(ContentSwitcher).current = "r-wifi-detail"

    @work(exclusive=True)
    async def _load_remote_wans(self) -> None:
        assert self._remote_client is not None
        host_id   = self._remote_selected_host_id
        site_id   = self._remote_selected_site_id
        site_name = self._remote_selected_site_name
        self.notify(f"Loading remote WAN interfaces for [bold]{site_name}[/bold]…", timeout=2)
        wans = await self._api_call(self._remote_client.get_wans(host_id, site_id))
        if wans is None:
            return
        self._remote_wans = wans
        wv = self.query_one("#r-wans", RemoteWansView)
        wv.set_site(site_name)
        wv.populate(wans)
        self.query_one(ContentSwitcher).current = "r-wans"
        self.notify(f"[bold]{len(wans)}[/bold] remote WAN interface(s)", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_remote_hosts(self) -> None:
        assert self._remote_client is not None
        self.notify("Loading all Unifi Cloud hosts…", timeout=2)
        hosts = await self._api_call(self._remote_client.get_hosts())
        if hosts is None:
            return
        self._remote_hosts = hosts
        hv = self.query_one("#r-hosts", RemoteHostsView)
        hv.populate(hosts)
        self.query_one(ContentSwitcher).current = "r-hosts"
        self.notify(f"[bold]{len(hosts)}[/bold] host(s) loaded", severity="information", timeout=2)

    @work(exclusive=True)
    async def _load_remote_controller(self) -> None:
        assert self._remote_client is not None
        host_id = self._remote_selected_host_id
        if not host_id:
            self.notify("No host selected", severity="warning")
            return
        self.notify("Loading controller info…", timeout=2)
        host = await self._api_call(self._remote_client.get_host(host_id))
        if host is None:
            return
        dv = self.query_one("#r-controller", RemoteControllerDetailView)
        dv.show_host(host)
        self.query_one(ContentSwitcher).current = "r-controller"
        self._focus_main_content()

    # ── ISP Metrics ───────────────────────────────────────────────────────────

    @work
    async def _load_isp_metrics(self, type_: str = "5m", duration: str = "24h") -> None:
        assert self._remote_client is not None
        view = self.query_one("#r-isp-metrics", IspMetricsView)
        data = await self._api_call(self._remote_client.get_isp_metrics(type_, duration))
        if data is None:
            return
        view.populate(data, type_, duration)
        self.query_one(ContentSwitcher).current = "r-isp-metrics"
        self._focus_main_content()

    @on(IspMetricsView.ReloadRequested)
    def _on_isp_reload(self, event: IspMetricsView.ReloadRequested) -> None:
        self._load_isp_metrics(event.type_, event.duration)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def on_unmount(self) -> None:
        if self._client is not None:
            await self._client.close()
        if self._remote_client is not None:
            await self._remote_client.close()
