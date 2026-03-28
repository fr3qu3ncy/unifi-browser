"""
CommandBar, BottomArea, CompletionListView, CompletionItem, and CommandIssued message.
"""
from __future__ import annotations

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.widgets import Input, Label, ListItem, ListView

from unifi_browser.constants import COMMANDS


class CommandIssued(Message):
    """Posted when the user submits a valid slash command."""

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command


class CompletionItem(ListItem):
    def __init__(self, cmd: str, desc: str) -> None:
        super().__init__(Label(f"  [bold]{cmd}[/bold]  [dim]{desc}[/dim]  "))
        self.cmd = cmd


class BottomArea(Container):
    """Single dock:bottom container. Height is managed programmatically to avoid
    Textual layout issues with `height: auto` on docked widgets."""

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


class CommandInput(Input):
    """Input that lets l/r bubble up to the app for tab-switching when the field is empty."""

    def _on_key(self, event: events.Key) -> None:
        # When nothing has been typed yet, let l/r be handled by the App
        # (which maps them to Local/Remote tab switching).
        if event.character in ("l", "r") and not self.value:
            return  # don't insert; event bubbles to app.on_key
        super()._on_key(event)


class CommandBar(Container):
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label("❯", id="cmd-prompt"),
            CommandInput(placeholder="Type / for commands…", id="cmd-input"),
            id="cmd-row",
        )

    def on_mount(self) -> None:
        pass  # Input is focused only when user presses /

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
            self.app._focus_main_content()
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
