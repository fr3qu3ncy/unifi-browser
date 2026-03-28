"""
Abstract base classes for Unifi Browser views.

DetailView   — scrollable key/value detail panel (device, client, network)
SiteListView — a title + DataTable list (sites, devices, clients, networks)
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import DataTable, Static


class DetailView(Container):
    """Base for all scrollable detail-panel views.

    Subclasses must set:
        TITLE_ID  — CSS id for the title Static (e.g. "detail-title")
        SCROLL_ID — CSS id for the VerticalScroll container
        BODY_ID   — CSS id for the body Static inside the scroll

    The Textual CSS class ``detail-view`` is added automatically so a single
    stylesheet rule covers all subclasses.
    """

    TITLE_ID:  str = "detail-title"
    SCROLL_ID: str = "detail-scroll"
    BODY_ID:   str = "detail-body"

    DEFAULT_CSS = "DetailView { height: 100%; }"

    def compose(self) -> ComposeResult:
        yield Static("", id=self.TITLE_ID)
        with VerticalScroll(id=self.SCROLL_ID):
            yield Static("", id=self.BODY_ID)

    def on_show(self) -> None:
        try:
            self.query_one(f"#{self.SCROLL_ID}").focus()
        except Exception:
            pass

    def _set_title(self, markup: str) -> None:
        self.query_one(f"#{self.TITLE_ID}", Static).update(markup)

    def _set_body(self, markup: str) -> None:
        self.query_one(f"#{self.BODY_ID}", Static).update(markup)


class SiteListView(Container):
    """Base for list views that display a title + DataTable.

    Subclasses must set:
        COLUMNS   — column header tuple/list
        TABLE_ID  — CSS id for the DataTable
        TITLE_ID  — CSS id for the title Static
        _HINT     — hint text appended after the site name in the title
    """

    COLUMNS:  tuple[str, ...] = ()
    TABLE_ID: str = ""
    TITLE_ID: str = ""
    _HINT:    str = "ESC to go back"

    def compose(self) -> ComposeResult:
        yield Static("", id=self.TITLE_ID)
        yield DataTable(id=self.TABLE_ID, cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(*self.COLUMNS)

    def on_show(self) -> None:
        self.query_one(DataTable).focus()

    def set_site(self, site_name: str) -> None:
        """Update the title bar with the active site name."""
        self.query_one(f"#{self.TITLE_ID}", Static).update(
            f"◈  {self._SECTION}  [dim]─[/dim]  [bold cyan]{site_name}[/bold cyan]"
            f"  [dim]— {self._HINT}[/dim]"
        )

    # Subclasses override this to name their section.
    _SECTION: str = ""
