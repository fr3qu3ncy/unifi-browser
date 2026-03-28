"""
Badge helpers, time formatters, and detail-panel renderers for Unifi Browser.
"""
from __future__ import annotations

import json as _json
from datetime import datetime, timezone

from rich.text import Text


# ─────────────────────────────────────────────────────────────────────────────
#  Shared row formatters (used by all _render_*_detail functions)
# ─────────────────────────────────────────────────────────────────────────────

def row(label: str, value: object, colour: str = "#e2e2e2", width: int = 24) -> str:
    """One key/value line for a detail panel."""
    val = str(value) if value not in (None, "", {}, []) else "—"
    return f"  [dim]{label:<{width}}[/dim] [{colour}]{val}[/{colour}]\n"


def bool_row(label: str, value: object, width: int = 24) -> str:
    """A row whose value is rendered as green Yes / red No."""
    if value is True:
        return f"  [dim]{label:<{width}}[/dim] [bright_green]Yes[/bright_green]\n"
    if value is False:
        return f"  [dim]{label:<{width}}[/dim] [red]No[/red]\n"
    return f"  [dim]{label:<{width}}[/dim] [dim]—[/dim]\n"


# ─────────────────────────────────────────────────────────────────────────────
#  Badge helpers
# ─────────────────────────────────────────────────────────────────────────────

def status_badge(status: str) -> Text:
    """Coloured dot + label for device/client status."""
    _STYLES: dict[str, tuple[str, str]] = {
        "connected":       ("●", "bright_green"),
        "disconnected":    ("●", "red"),
        "online":          ("●", "bright_green"),
        "offline":         ("●", "red"),
        "adopting":        ("●", "cyan"),
        "updating":        ("●", "yellow"),
        "rebooting":       ("●", "yellow"),
        "unknown":         ("●", "dim"),
        "pendingadoption": ("●", "cyan"),
    }
    icon, colour = _STYLES.get(status.lower(), ("●", "dim"))
    t = Text()
    t.append(f"{icon} ", style=colour)
    t.append(status)
    return t


def firmware_badge(status: str) -> Text:
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


def client_type_badge(type_str: str) -> Text:
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


def mgmt_badge(management: str) -> Text:
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


def enabled_badge(enabled: object) -> Text:
    t = Text()
    if enabled is True:
        t.append("✓", style="bright_green")
    else:
        t.append("✗", style="red")
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  Time formatters
# ─────────────────────────────────────────────────────────────────────────────

def fmt_bool(v: object) -> str:
    if v is True:
        return "Yes"
    if v is False:
        return "No"
    return "—"


def time_ago(iso_str: str) -> str:
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


def uptime(startup_time_str: str) -> str:
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


# ─────────────────────────────────────────────────────────────────────────────
#  Detail panel renderers
# ─────────────────────────────────────────────────────────────────────────────

def render_device_detail(dev: dict) -> str:
    """Build a Rich-markup string with all device details in labelled sections."""
    state   = dev.get("state") or "—"
    fw_able = dev.get("firmwareUpdatable")
    fw_label = "updateAvailable" if fw_able else "upToDate" if fw_able is not None else "—"
    s_colour  = "bright_green" if state.upper() == "ONLINE" else ("red" if state.upper() == "OFFLINE" else "yellow")
    fw_colour = "green" if fw_label == "upToDate" else ("yellow" if fw_label == "updateAvailable" else "dim")

    lines = []

    lines.append("[bold cyan]  Identity[/bold cyan]\n")
    lines.append(row("Name",             dev.get("name")))
    lines.append(row("ID",               dev.get("id")))
    lines.append(row("MAC Address",      dev.get("macAddress")))
    lines.append(row("Model",            dev.get("model")))
    lines.append("\n")

    lines.append("[bold cyan]  Status[/bold cyan]\n")
    lines.append(row("State",            state,    s_colour))
    lines.append(row("Supported",        fmt_bool(dev.get("supported"))))
    lines.append(row("Firmware Version", dev.get("firmwareVersion")))
    lines.append(row("Firmware Update",  fw_label, fw_colour))
    lines.append("\n")

    lines.append("[bold cyan]  Network[/bold cyan]\n")
    lines.append(row("IP Address",       dev.get("ipAddress")))
    lines.append("\n")

    lines.append("[bold cyan]  Capabilities[/bold cyan]\n")
    features   = dev.get("features") or []
    interfaces = dev.get("interfaces") or []
    lines.append(row("Features",         ", ".join(features) if features else "—"))
    lines.append(row("Interfaces",       ", ".join(interfaces) if interfaces else "—"))
    lines.append("\n")

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


def render_client_detail(client: dict, devices: list[dict]) -> str:
    """Build a Rich-markup string with all client details."""
    dev_names: dict[str, str] = {
        d.get("id", ""): (d.get("name") or d.get("id", "—")) for d in devices
    }
    uplink_id   = client.get("uplinkDeviceId") or ""
    uplink_name = dev_names.get(uplink_id) or uplink_id or "—"
    type_str    = client.get("type") or ""
    access      = (client.get("access") or {}).get("type") or "—"

    lines = []

    lines.append("[bold cyan]  Identity[/bold cyan]\n")
    lines.append(row("Name",        client.get("name")))
    lines.append(row("ID",          client.get("id")))
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
    lines.append(row("Connected",    time_ago(client.get("connectedAt") or "")))
    lines.append(row("Connected At", client.get("connectedAt")))
    lines.append(row("Access Type",  access))
    lines.append("\n")

    return "".join(lines)


def render_network_detail(net: dict) -> str:
    """Build a Rich-markup string with all network details including IPv4/DHCP config."""
    W = 30  # label column width for this denser view

    lines = []

    lines.append("[bold cyan]  Identity[/bold cyan]\n")
    lines.append(row("Name",        net.get("name"),    width=W))
    lines.append(row("ID",          net.get("id"),      width=W))
    lines.append(row("VLAN ID",     net.get("vlanId"),  width=W))
    mgmt = net.get("management") or ""
    if mgmt == "GATEWAY":
        lines.append(f"  [dim]{'Management':<{W}}[/dim] [bright_green]⬡ Gateway[/bright_green]\n")
    elif mgmt == "UNMANAGED":
        lines.append(f"  [dim]{'Management':<{W}}[/dim] [yellow]○ Unmanaged[/yellow]\n")
    else:
        lines.append(row("Management", mgmt, width=W))
    lines.append(bool_row("Default", net.get("default"), width=W))
    lines.append(bool_row("Enabled", net.get("enabled"), width=W))
    lines.append("\n")

    lines.append("[bold cyan]  Features[/bold cyan]\n")
    lines.append(bool_row("Isolation",       net.get("isolationEnabled"),       width=W))
    lines.append(bool_row("Cellular Backup", net.get("cellularBackupEnabled"),  width=W))
    lines.append(bool_row("Internet Access", net.get("internetAccessEnabled"),  width=W))
    lines.append(bool_row("mDNS Forwarding", net.get("mdnsForwardingEnabled"),  width=W))
    lines.append("\n")

    ipv4 = net.get("ipv4Configuration") or {}
    if ipv4:
        lines.append("[bold cyan]  IPv4 Configuration[/bold cyan]\n")
        prefix = ipv4.get("prefixLength")
        lines.append(row("Host IP Address", ipv4.get("hostIpAddress"),      width=W))
        lines.append(row("Prefix Length",   f"/{prefix}" if prefix is not None else "—", width=W))
        lines.append(bool_row("Auto-Scale", ipv4.get("autoScaleEnabled"),   width=W))
        lines.append("\n")

        dhcp = ipv4.get("dhcpConfiguration") or {}
        if dhcp:
            lines.append("[bold cyan]  DHCP Configuration[/bold cyan]\n")
            lines.append(row("Mode", dhcp.get("mode"), width=W))
            ip_range = dhcp.get("ipAddressRange") or {}
            if ip_range:
                lines.append(row("Range Start", ip_range.get("start"), width=W))
                lines.append(row("Range End",   ip_range.get("stop"),  width=W))
            lease_secs = dhcp.get("leaseTimeSeconds")
            if lease_secs is not None:
                hours, rem = divmod(int(lease_secs), 3600)
                mins = rem // 60
                lease_label = f"{hours}h {mins}m" if hours else f"{mins}m"
                lines.append(row("Lease Time", f"{lease_label} ({lease_secs}s)", width=W))
            else:
                lines.append(row("Lease Time", None, width=W))
            lines.append(row("Domain Name",  dhcp.get("domainName"),                   width=W))
            lines.append(bool_row("Conflict Detection", dhcp.get("pingConflictDetectionEnabled"), width=W))
            lines.append("\n")

    meta = net.get("metadata") or {}
    if meta:
        lines.append("[bold cyan]  Metadata[/bold cyan]\n")
        origin = meta.get("origin") or "—"
        origin_label = {"USER_DEFINED": "User", "SYSTEM_DEFINED": "System"}.get(origin, origin)
        lines.append(row("Origin",       origin_label,             width=W))
        lines.append(bool_row("Configurable", meta.get("configurable"), width=W))
        lines.append("\n")

    return "".join(lines)


def render_host_detail(host: dict) -> str:
    """Build a Rich-markup string with all controller/host details."""
    W = 30
    rs = host.get("reportedState") or {}
    hw = host.get("hardware") or {}
    loc = host.get("location") or {}
    lines = []

    lines.append("[bold #e6a817]  Identity[/bold #e6a817]\n")
    lines.append(row("Name",         rs.get("name") or rs.get("hostname"), width=W))
    lines.append(row("Hostname",     rs.get("hostname"),      width=W))
    lines.append(row("Host ID",      host.get("id"),           width=W))
    lines.append(row("Type",         host.get("type"),         width=W))
    lines.append(row("MAC",          rs.get("mac"),            width=W))
    lines.append("\n")

    lines.append("[bold #e6a817]  Network[/bold #e6a817]\n")
    lines.append(row("IP Address",           host.get("ipAddress") or rs.get("ip"), width=W))
    lines.append(row("LAN IP",               rs.get("ip"),                          width=W))
    lines.append(row("Direct Connect Domain",rs.get("directConnectDomain"),          width=W))
    lines.append(row("Mgmt Port",            rs.get("mgmt_port"),                   width=W))
    lines.append("\n")

    lines.append("[bold #e6a817]  Software[/bold #e6a817]\n")
    lines.append(row("Firmware Version", rs.get("version"),             width=W))
    lines.append(row("Release Channel",  rs.get("releaseChannel"),       width=W))
    lines.append(row("Timezone",         rs.get("timezone"),             width=W))
    lines.append(row("Country Code",     rs.get("country"),              width=W))
    lines.append("\n")

    lines.append("[bold #e6a817]  Status[/bold #e6a817]\n")
    state = rs.get("state") or "—"
    if state == "connected":
        state_fmt = "[bright_green]● connected[/bright_green]"
    elif state == "disconnected":
        state_fmt = "[red]○ disconnected[/red]"
    else:
        state_fmt = f"[yellow]{state}[/yellow]"
    lines.append(f"  [dim]{'State':<{W}}[/dim] {state_fmt}\n")
    ctrl_status = rs.get("controllerStatus") or host.get("controllerStatus")
    if ctrl_status:
        if ctrl_status == "CONNECTED":
            lines.append(f"  [dim]{'Controller Status':<{W}}[/dim] [bright_green]● CONNECTED[/bright_green]\n")
        else:
            lines.append(f"  [dim]{'Controller Status':<{W}}[/dim] [yellow]{ctrl_status}[/yellow]\n")
    lines.append(bool_row("Cloud Blocked", host.get("isBlocked"),        width=W))

    device_state = rs.get("deviceState")
    if device_state:
        lines.append(row("Device State",    device_state,                width=W))

    if loc:
        lines.append("\n")
        lines.append("[bold #e6a817]  Location[/bold #e6a817]\n")
        lines.append(row("Text",    loc.get("text"),    width=W))
        lines.append(row("Address", loc.get("address"), width=W))
        lines.append(row("Lat/Lon",
            f"{loc.get('lat')}, {loc.get('lon')}" if loc.get('lat') else None, width=W))

    if hw:
        lines.append("\n")
        lines.append("[bold #e6a817]  Hardware[/bold #e6a817]\n")
        lines.append(row("Model",    hw.get("name") or hw.get("shortname"), width=W))
        lines.append(row("Hostname", hw.get("hostname"),                    width=W))

    return "".join(lines)


def format_frequencies(freqs: list) -> str:
    """Format a list of GHz values as '2.4 · 5 · 6 GHz'."""
    if not freqs:
        return "—"
    return " · ".join(str(f) for f in sorted(freqs)) + " GHz"


def sparkline(values: list[float], width: int = 60) -> str:
    """Render a list of floats as a Unicode block-character sparkline."""
    if not values:
        return "—"
    # Downsample if needed
    if len(values) > width:
        step = len(values) / width
        values = [values[int(i * step)] for i in range(width)]
    blocks = "▁▂▃▄▅▆▇█"
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return "▄" * len(values)
    result = ""
    for v in values:
        idx = int((v - min_v) / (max_v - min_v) * 7)
        result += blocks[min(idx, 7)]
    return result


def fmt_kbps(kbps: float | None) -> str:
    """Format kbps as human-readable Mbps / Gbps."""
    if kbps is None:
        return "—"
    mbps = kbps / 1000
    if mbps >= 1000:
        return f"{mbps / 1000:.2f} Gbps"
    return f"{mbps:.0f} Mbps"


def render_isp_metrics(entries: list[dict], type_: str, duration: str) -> str:
    """Build a Rich-markup string for the ISP Metrics view."""
    W = 22
    lines = []

    for i, entry in enumerate(entries):
        host_id = entry.get("hostId", "—")
        periods = entry.get("periods", [])
        short_host = host_id[:40] + "…" if len(host_id) > 40 else host_id

        if not periods:
            lines.append(f"[bold #e6a817]  Host {i + 1}[/bold #e6a817]  [dim]{short_host}[/dim]\n")
            lines.append("  [dim]No data for this period[/dim]\n\n")
            continue

        # Latest data from the most recent period
        latest_period = periods[-1]
        wan = latest_period.get("data", {}).get("wan", {})
        ts  = latest_period.get("metricTime", "")

        isp_name = wan.get("ispName") or "—"
        isp_asn  = wan.get("ispAsn")  or "—"

        # ── Header ────────────────────────────────────────────────────────────
        lines.append(f"[bold #e6a817]  ◈  {isp_name}[/bold #e6a817]  [dim](ASN {isp_asn})[/dim]\n")
        lines.append(f"  [dim]{host_id[:72]}[/dim]\n\n")

        # ── Latest snapshot ───────────────────────────────────────────────────
        lines.append("[bold cyan]  Latest Snapshot[/bold cyan]")
        if ts:
            lines.append(f"  [dim]{ts.replace('T', ' ').replace('Z', ' UTC')}[/dim]")
        lines.append("\n")

        dl   = wan.get("download_kbps")
        ul   = wan.get("upload_kbps")
        lat  = wan.get("avgLatency")
        mlat = wan.get("maxLatency")
        loss = wan.get("packetLoss")
        up   = wan.get("uptime")

        lines.append(row("Download",     fmt_kbps(dl),                              colour="#e6a817", width=W))
        lines.append(row("Upload",       fmt_kbps(ul),                              colour="#e6a817", width=W))
        lines.append(row("Avg Latency",  f"{lat} ms"  if lat  is not None else "—", colour="#e6a817", width=W))
        lines.append(row("Max Latency",  f"{mlat} ms" if mlat is not None else "—", colour="#e6a817", width=W))

        if loss is not None:
            loss_colour = "bright_green" if loss == 0 else ("yellow" if loss < 1 else "red")
            lines.append(row("Packet Loss",  f"{loss:.1f}%", colour=loss_colour, width=W))
        else:
            lines.append(row("Packet Loss", None, width=W))

        if up is not None:
            up_colour = "bright_green" if up >= 99 else ("yellow" if up >= 95 else "red")
            lines.append(row("Uptime",       f"{up:.1f}%",  colour=up_colour,    width=W))
        lines.append("\n")

        # ── Aggregate stats ───────────────────────────────────────────────────
        all_dl   = [p["data"]["wan"].get("download_kbps", 0) for p in periods if p.get("data", {}).get("wan")]
        all_ul   = [p["data"]["wan"].get("upload_kbps",   0) for p in periods if p.get("data", {}).get("wan")]
        all_lat  = [p["data"]["wan"].get("avgLatency",    0) for p in periods if p.get("data", {}).get("wan")]
        all_loss = [p["data"]["wan"].get("packetLoss",    0) for p in periods if p.get("data", {}).get("wan")]

        n = len(all_dl)
        if n > 0:
            lines.append(f"[bold cyan]  Aggregates[/bold cyan]  [dim]over {n} {type_} periods ({duration})[/dim]\n")
            avg_dl = sum(all_dl) / n
            avg_ul = sum(all_ul) / n
            avg_lat = sum(all_lat) / n
            lines.append(row("Avg Download",  fmt_kbps(avg_dl),  colour="#e6a817", width=W))
            lines.append(row("Avg Upload",    fmt_kbps(avg_ul),  colour="#e6a817", width=W))
            lines.append(row("Avg Latency",   f"{avg_lat:.1f} ms", colour="#e6a817", width=W))
            lines.append(row("Max Latency",   f"{max(p['data']['wan'].get('maxLatency', 0) for p in periods if p.get('data', {}).get('wan'))} ms", colour="#e6a817", width=W))
            total_loss = sum(all_loss) / n
            loss_colour = "bright_green" if total_loss == 0 else ("yellow" if total_loss < 1 else "red")
            lines.append(row("Avg Packet Loss", f"{total_loss:.2f}%", colour=loss_colour, width=W))
            lines.append("\n")

        # ── Sparklines ────────────────────────────────────────────────────────
        if all_dl:
            dl_spark = sparkline(all_dl)
            ul_spark = sparkline(all_ul)
            lat_spark = sparkline(all_lat)
            loss_spark = sparkline(all_loss) if any(v > 0 for v in all_loss) else "▁" * min(len(all_loss), 60)

            min_dl = fmt_kbps(min(all_dl)); max_dl = fmt_kbps(max(all_dl))
            min_ul = fmt_kbps(min(all_ul)); max_ul = fmt_kbps(max(all_ul))

            lines.append("[bold cyan]  Download trend[/bold cyan]\n")
            lines.append(f"  [#e6a817]{dl_spark}[/#e6a817]\n")
            lines.append(f"  [dim]min {min_dl}  ·  max {max_dl}[/dim]\n\n")

            lines.append("[bold cyan]  Upload trend[/bold cyan]\n")
            lines.append(f"  [#e6a817]{ul_spark}[/#e6a817]\n")
            lines.append(f"  [dim]min {min_ul}  ·  max {max_ul}[/dim]\n\n")

            lines.append("[bold cyan]  Latency trend[/bold cyan]\n")
            lines.append(f"  [#e6a817]{lat_spark}[/#e6a817]\n")
            lines.append(f"  [dim]min {min(all_lat):.0f} ms  ·  max {max(all_lat):.0f} ms[/dim]\n\n")

            lines.append("[bold cyan]  Packet loss trend[/bold cyan]\n")
            lines.append(f"  [#e6a817]{loss_spark}[/#e6a817]\n")
            lines.append(f"  [dim]min {min(all_loss):.2f}%  ·  max {max(all_loss):.2f}%[/dim]\n\n")

        if i < len(entries) - 1:
            lines.append("[dim]  ─────────────────────────────────────────────────────────────[/dim]\n\n")

    return "".join(lines)


def format_security_type(sec_type: str) -> str:
    """Human-friendly security type label."""
    return {
        "WPA3_PERSONAL":         "WPA3",
        "WPA2_PERSONAL":         "WPA2",
        "WPA2_WPA3_PERSONAL":    "WPA2/WPA3",
        "WPA2_ENTERPRISE":       "WPA2 Enterprise",
        "WPA3_ENTERPRISE":       "WPA3 Enterprise",
        "OPEN":                  "Open",
    }.get(sec_type, sec_type or "—")


def render_wifi_detail(wifi: dict, show_passphrase: bool = False) -> str:
    """Build a Rich-markup string for a WiFi broadcast detail panel."""
    W = 28

    lines = []

    # ── Identity ─────────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Identity[/bold cyan]\n")
    lines.append(row("Name",        wifi.get("name"),       width=W))
    lines.append(row("ID",          wifi.get("id"),         width=W))
    lines.append(row("Type",        wifi.get("type"),       width=W))
    origin = (wifi.get("metadata") or {}).get("origin") or "—"
    origin_label = {"USER_DEFINED": "User", "SYSTEM_DEFINED": "System"}.get(origin, origin)
    lines.append(row("Origin",      origin_label,           width=W))
    lines.append("\n")

    # ── Status ───────────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Status[/bold cyan]\n")
    lines.append(bool_row("Enabled",   wifi.get("enabled"),  width=W))
    lines.append(bool_row("Hide SSID", wifi.get("hideName"), width=W))
    freqs = wifi.get("broadcastingFrequenciesGHz") or []
    lines.append(row("Frequencies",  format_frequencies(freqs), width=W))
    lines.append("\n")

    # ── Network ──────────────────────────────────────────────────────────────
    net = wifi.get("network") or {}
    lines.append("[bold cyan]  Network[/bold cyan]\n")
    lines.append(row("Network Type", net.get("type"), width=W))
    if net.get("networkId"):
        lines.append(row("Network ID", net.get("networkId"), width=W))
    lines.append("\n")

    # ── Security ─────────────────────────────────────────────────────────────
    sec = wifi.get("securityConfiguration") or {}
    lines.append("[bold cyan]  Security[/bold cyan]\n")
    lines.append(row("Type",         format_security_type(sec.get("type") or ""), width=W))

    passphrase = sec.get("passphrase")
    if passphrase is not None:
        if show_passphrase:
            lines.append(
                f"  [dim]{'Passphrase':<{W}}[/dim] [bright_green]{passphrase}[/bright_green]"
                "  [dim italic](press P to hide)[/dim italic]\n"
            )
        else:
            masked = "●" * min(len(passphrase), 12)
            lines.append(
                f"  [dim]{'Passphrase':<{W}}[/dim] [dim]{masked}[/dim]"
                "  [dim italic](press P to reveal)[/dim italic]\n"
            )

    lines.append(bool_row("Fast Roaming",  sec.get("fastRoamingEnabled"),  width=W))
    rekey = sec.get("groupRekeyIntervalSeconds")
    if rekey is not None:
        hours, rem = divmod(int(rekey), 3600)
        rekey_label = f"{hours}h" if hours else f"{rem // 60}m"
        lines.append(row("Group Rekey",   f"{rekey_label} ({rekey}s)", width=W))
    if sec.get("pmfMode"):
        lines.append(row("PMF Mode",      sec.get("pmfMode"),           width=W))

    sae = sec.get("saeConfiguration") or {}
    if sae:
        lines.append(row("SAE Anticlogging", f"{sae.get('anticloggingThresholdSeconds')}s", width=W))
        lines.append(row("SAE Sync Time",    f"{sae.get('syncTimeSeconds')}s",             width=W))
    lines.append("\n")

    # ── Hotspot ──────────────────────────────────────────────────────────────
    hotspot = wifi.get("hotspotConfiguration") or {}
    if hotspot:
        lines.append("[bold cyan]  Hotspot[/bold cyan]\n")
        lines.append(row("Type", hotspot.get("type"), width=W))
        lines.append("\n")

    # ── Advanced ─────────────────────────────────────────────────────────────
    lines.append("[bold cyan]  Advanced[/bold cyan]\n")
    lines.append(bool_row("Client Isolation",   wifi.get("clientIsolationEnabled"),         width=W))
    lines.append(bool_row("Band Steering",      wifi.get("bandSteeringEnabled"),             width=W))
    lines.append(bool_row("MLO",                wifi.get("mloEnabled"),                      width=W))
    lines.append(bool_row("UAPSD",              wifi.get("uapsdEnabled"),                    width=W))
    lines.append(bool_row("ARP Proxy",          wifi.get("arpProxyEnabled"),                 width=W))
    lines.append(bool_row("BSS Transition",     wifi.get("bssTransitionEnabled"),            width=W))
    lines.append(bool_row("Multicast→Unicast",  wifi.get("multicastToUnicastConversionEnabled"), width=W))
    lines.append(bool_row("Advertise Device",   wifi.get("advertiseDeviceName"),             width=W))
    lines.append("\n")

    return "".join(lines)
