"""IspMetricsView — ISP connection info and time-series metrics."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.widgets import Static

from unifi_browser.helpers import render_isp_metrics

# Ordered preset options: (label, type_, duration)
_PRESETS: list[tuple[str, str, str]] = [
    ("5m · 24h",  "5m", "24h"),
    ("1h · 7d",   "1h", "7d"),
    ("1h · 30d",  "1h", "30d"),
]

_PRESET_DESCRIPTIONS: dict[str, str] = {
    "5m · 24h":  "5-minute resolution  ·  last 24 hours",
    "1h · 7d":   "hourly resolution  ·  last 7 days",
    "1h · 30d":  "hourly resolution  ·  last 30 days",
}


class IspMetricsView(Container):
    """Displays ISP info and time-series metrics with sparklines."""

    BINDINGS = [
        Binding("tab", "next_preset", "Cycle preset", show=True),
    ]

    class ReloadRequested(Message):
        """Posted when the user changes the preset."""
        def __init__(self, type_: str, duration: str) -> None:
            super().__init__()
            self.type_    = type_
            self.duration = duration

    _preset_idx: int       = 0
    _data:        list[dict] = []

    @property
    def _type(self) -> str:
        return _PRESETS[self._preset_idx][1]

    @property
    def _duration(self) -> str:
        return _PRESETS[self._preset_idx][2]

    @property
    def _label(self) -> str:
        return _PRESETS[self._preset_idx][0]

    def compose(self) -> ComposeResult:
        yield Static("", id="r-isp-title")
        yield Static("", id="r-isp-presets")
        yield Static("", id="r-isp-hint")
        yield VerticalScroll(
            Static("", id="r-isp-body"),
            id="r-isp-scroll",
        )

    def on_mount(self) -> None:
        self._update_header()

    def on_show(self) -> None:
        self.query_one("#r-isp-scroll").focus()

    def _update_header(self) -> None:
        # Title row
        self.query_one("#r-isp-title", Static).update(
            "◈  [bold]ISP Metrics[/bold]"
        )

        # Preset selector — all three options, active one highlighted
        parts = []
        for i, (label, _, _) in enumerate(_PRESETS):
            if i == self._preset_idx:
                parts.append(f"[bold #e6a817 reverse]  ❯ {label}  [/bold #e6a817 reverse]")
            else:
                parts.append(f"[dim]  {label}  [/dim]")
        preset_row = "   ".join(parts)
        self.query_one("#r-isp-presets", Static).update(preset_row)

        # Hint row — description of active preset + key hint
        desc = _PRESET_DESCRIPTIONS[self._label]
        self.query_one("#r-isp-hint", Static).update(
            f"  [dim italic]{desc}[/dim italic]"
            "   [dim]·   Press [/dim][bold]Tab[/bold][dim] to change time range   ·   ESC: back[/dim]"
        )

    def populate(self, data: list[dict], type_: str, duration: str) -> None:
        for i, (_, t, d) in enumerate(_PRESETS):
            if t == type_ and d == duration:
                self._preset_idx = i
                break
        self._data = data
        self._update_header()
        body = render_isp_metrics(data, type_, duration)
        self.query_one("#r-isp-body", Static).update(body)

    def action_next_preset(self) -> None:
        self._preset_idx = (self._preset_idx + 1) % len(_PRESETS)
        self._update_header()
        self.post_message(self.ReloadRequested(self._type, self._duration))
