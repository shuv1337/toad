from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.reactive import var, reactive
from textual import getters
from textual.widgets import Footer
from textual import containers

from toad.widgets.throbber import Throbber
from toad.widgets.conversation import Conversation
from toad.widgets.explain import Explain
from toad.widgets.version import Version


class MainScreen(Screen, can_focus=False):
    AUTO_FOCUS = "Conversation Prompt TextArea"

    BINDING_GROUP_TITLE = "Screen"
    busy_count = var(0)
    throbber: getters.query_one[Throbber] = getters.query_one("#throbber")
    conversation = getters.query_one(Conversation)

    column = reactive(False)
    column_width = reactive(100)

    def compose(self) -> ComposeResult:
        yield Version("Toad v0.1")
        with containers.Center():
            yield Explain()
            yield Conversation()
            yield Footer()

    def action_focus_prompt(self) -> None:
        self.conversation.focus_prompt()

    def watch_column(self, column: bool) -> None:
        self.set_class(column, "-column")
        self.conversation.styles.max_width = (
            max(10, self.column_width) if column else None
        )

    def watch_column_width(self, column_width: int) -> None:
        self.conversation.styles.max_width = (
            max(10, column_width) if self.column else None
        )
