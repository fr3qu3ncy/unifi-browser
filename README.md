# Unifi Browser

A terminal UI (TUI) application for browsing and inspecting your Unifi network configuration, built with Python and [Textual](https://textual.textualize.io/).

```
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
╚══════════════════════════════════════════════════════╝
```

---

## Requirements

- Python 3.10+
- Unifi controller firmware **>= 5.0.3** (earlier versions do not expose the REST API)

---

## Quick Start

**macOS / Linux**
```bash
git clone <repo-url>
cd unifi-browser
bash run.sh
```

**Windows (PowerShell)**
```powershell
git clone <repo-url>
cd unifi-browser
.\run.ps1
```

> If PowerShell blocks the script due to execution policy, run this once (as your user, no admin needed):
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

Both scripts will:
1. Create a Python virtual environment (`.venv/`) if one does not already exist
2. Activate it
3. Install all dependencies from `requirements.txt`
4. Launch the app

---

## Features

Unifi Browser supports two independent connection modes, displayed as tabs at the top of the screen:

| Mode       | Colour | Description |
|------------|--------|-------------|
| **Local**  | Cyan   | Connects directly to a Unifi Controller on your network |
| **Remote** | Amber  | Connects to the Unifi Cloud API (`api.ui.com`) |

You can connect to both simultaneously and switch between them at any time.

### Local screens
| Screen | Description |
|--------|-------------|
| Sites | List of sites on the local controller |
| Devices | Network infrastructure (switches, APs, gateways) |
| Clients | Connected wired and wireless clients |
| Networks | VLANs and network segments |
| WiFi | Wireless broadcast SSIDs |
| WAN Interfaces | WAN uplink interfaces |

### Remote screens
| Screen | Description |
|--------|-------------|
| Sites | All sites on your Unifi Cloud account (with host info) |
| Devices | Network devices per site |
| Clients | Connected clients per site |
| Networks | VLANs and network segments per site |
| WiFi | Wireless broadcast SSIDs per site |
| WAN Interfaces | WAN uplink interfaces per site |
| Controller | Details about the site's Unifi controller (host) |
| All Hosts | Every controller registered to your cloud account |
| ISP Metrics | Internet connection stats and sparkline graphs (5m/1h resolution) |

---

## Key Bindings

| Key | Action |
|-----|--------|
| `l` | Switch to Local tab |
| `r` | Switch to Remote tab |
| `i` | Open ISP Metrics (Remote mode) |
| `h` | Open All Hosts list (Remote mode) |
| `Tab` | Cycle ISP Metrics time range preset |
| `ESC` | Go back to the previous screen |
| `/` | Focus the command bar |

---

## Slash Commands

Type `/` to open the command bar (with autocomplete).

| Command | Description |
|---------|-------------|
| `/connect` | Connect — opens login for the current tab |
| `/connect local` | Connect to a Local Unifi Controller |
| `/connect remote` | Connect to Unifi Cloud |
| `/local` | Switch to Local tab |
| `/remote` | Switch to Remote tab |
| `/isp` | Open ISP Metrics (Remote mode) |
| `/sites` | Go back to the sites list |
| `/sitemenu` | Go back to the site menu |
| `/help` | Show in-app help |
| `/exit` | Exit the application |

---

## Obtaining API Keys

> **Both Local and Remote require firmware >= 5.0.3 on your Unifi controller.**

### Remote API Key (Unifi Cloud)

1. Sign in to [UniFi Site Manager](https://unifi.ui.com)
2. Navigate to the API configuration page:
   - **GA (General Availability):** API section
   - **EA (Early Access):** Settings → API Keys
3. Click **Create New API Key**
4. Copy the generated key — it is only displayed **once**, so store it securely

When connecting, use the default base URL: `https://api.ui.com/v1/`

### Local API Key

1. Sign in to your **local Unifi controller**
2. Navigate to **Settings → Integrations**
3. Click **Create New API Key**
4. Copy the generated key — it is only displayed **once**, so store it securely

When connecting, enter your controller's base URL, e.g. `https://unifi.local/`  
(Self-signed certificates are accepted automatically for local connections.)

---

## ISP Metrics (Remote only)

Available via `/isp` or the `I` key. Shows per-host internet connection stats with sparkline graphs.

Press `Tab` to cycle through three time range presets:

| Preset | Resolution | Duration |
|--------|-----------|----------|
| `5m · 24h` | 5-minute samples | Last 24 hours |
| `1h · 7d` | Hourly samples | Last 7 days |
| `1h · 30d` | Hourly samples | Last 30 days |

Metrics displayed: ISP name, ASN, average/max latency, download throughput, upload throughput, packet loss, uptime.

---

## Project Structure

```
unifi-browser/
├── main.py                        # Entry point
├── run.sh                         # Launch script — macOS/Linux (creates venv, installs deps)
├── run.ps1                        # Launch script — Windows PowerShell
├── app.tcss                       # Textual stylesheet
├── requirements.txt
└── unifi_browser/
    ├── app.py                     # Main Textual app + all event routing
    ├── constants.py               # Commands, back-nav maps, defaults
    ├── helpers.py                 # Render helpers, sparklines, formatters
    ├── api/
    │   ├── client.py              # Local UnifiClient (httpx)
    │   └── remote_client.py       # Remote RemoteUnifiClient (httpx)
    ├── views/
    │   ├── base.py                # DetailView / SiteListView base classes
    │   ├── welcome.py             # Local welcome screen
    │   ├── sites.py               # Local sites list
    │   ├── site_menu.py           # Local site navigation menu
    │   ├── devices.py             # Local devices + detail
    │   ├── clients.py             # Local clients + detail
    │   ├── networks.py            # Local networks + detail
    │   ├── wifi.py                # Local WiFi + detail
    │   ├── wans.py                # Local WAN interfaces
    │   └── remote/
    │       ├── welcome.py         # Remote welcome screen
    │       ├── sites.py           # Remote sites list
    │       ├── site_menu.py       # Remote site navigation menu
    │       ├── devices.py         # Remote devices + detail
    │       ├── clients.py         # Remote clients + detail
    │       ├── networks.py        # Remote networks + detail
    │       ├── wifi.py            # Remote WiFi + detail
    │       ├── wans.py            # Remote WAN interfaces
    │       ├── hosts.py           # All hosts list + host/controller detail
    │       └── isp_metrics.py     # ISP metrics with sparklines
    └── widgets/
        ├── command_bar.py         # Slash-command input with autocomplete
        ├── help_screen.py         # /help modal
        ├── login.py               # Login dialog (local & remote)
        └── tab_bar.py             # Local/Remote tab bar
```

---

## License

MIT
