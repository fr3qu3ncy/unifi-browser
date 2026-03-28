"""
LoginScreen modal for entering Unifi Controller credentials.
"""
from __future__ import annotations

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from unifi_browser.api.client import url_history
from unifi_browser.api.remote_client import REMOTE_DEFAULT_API_URL, remote_url_history


class LoginScreen(ModalScreen[Optional[tuple[str, str]]]):
    """Modal form for entering Unifi Controller credentials.

    Pass ``mode="remote"`` for the cloud login variant.
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, mode: str = "local") -> None:
        super().__init__()
        self._mode = mode

    def compose(self) -> ComposeResult:
        is_remote = self._mode == "remote"
        history   = remote_url_history if is_remote else url_history
        dialog_id = "remote-login-dialog" if is_remote else "login-dialog"
        title_id  = "remote-login-title"  if is_remote else "login-title"
        tag       = "◈  Connect to Unifi Cloud" if is_remote else "◈  Connect to Unifi Controller"
        url_label = "Cloud API URL"  if is_remote else "Local Controller URL"
        key_label = "Cloud API Key"  if is_remote else "Local API Key"
        key_ph    = "Paste your cloud API key here" if is_remote else "Paste your local API key here"

        with Center():
            with Middle():
                with Vertical(id=dialog_id):
                    yield Static(tag, id=title_id)
                    yield Label(url_label)
                    yield Input(value=history.last, id="url-input")
                    if history.urls:
                        yield Label("Recent", id="history-label")
                        yield ListView(
                            *[ListItem(Label(u), id=f"hist-{i}") for i, u in enumerate(history.urls)],
                            id="url-history",
                        )
                    yield Label(key_label)
                    yield Input(
                        placeholder=key_ph,
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
