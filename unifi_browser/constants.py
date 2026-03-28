"""
Global constants for Unifi Browser.
"""
from __future__ import annotations

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

DEFAULT_API_URL        = "https://unifi.local/"
REMOTE_DEFAULT_API_URL = "https://api.ui.com/v1/"

# Slash-command registry: command → description
COMMANDS: dict[str, str] = {
    "/connect":        "Connect — defaults to the current tab (local or remote)",
    "/connect local":  "Connect to a Local Unifi Controller",
    "/connect remote": "Connect to Unifi Cloud (remote)",
    "/local":          "Switch to Local tab",
    "/remote":         "Switch to Remote tab",
    "/isp":            "ISP Metrics (remote mode — shows all hosts)",
    "/sites":          "Go back to the sites list",
    "/sitemenu":       "Go back to the site menu",
    "/help":           "Show available commands",
    "/exit":           "Exit Unifi Browser",
}

# Back-navigation map for LOCAL screens: current screen id → parent screen id
BACK_SCREEN: dict[str, str] = {
    "sitemenu":       "sites",
    "devices":        "sitemenu",
    "clients":        "sitemenu",
    "networks":       "sitemenu",
    "wifi":           "sitemenu",
    "wans":           "sitemenu",
    "detail":         "devices",
    "client-detail":  "clients",
    "network-detail": "networks",
    "wifi-detail":    "wifi",
}

# Back-navigation map for REMOTE screens (r- prefixed)
REMOTE_BACK_SCREEN: dict[str, str] = {
    "r-sitemenu":        "r-sites",
    "r-devices":         "r-sitemenu",
    "r-clients":         "r-sitemenu",
    "r-networks":        "r-sitemenu",
    "r-wifi":            "r-sitemenu",
    "r-wans":            "r-sitemenu",
    "r-controller":      "r-sitemenu",
    "r-hosts":           "r-sites",
    "r-host-detail":     "r-hosts",
    "r-isp-metrics":     "r-sites",
    "r-detail":          "r-devices",
    "r-client-detail":   "r-clients",
    "r-network-detail":  "r-networks",
    "r-wifi-detail":     "r-wifi",
}
