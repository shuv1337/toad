from dataclasses import dataclass
from rich.cells import cell_len

from textual import on, work
from textual.reactive import var
from textual.app import ComposeResult

from textual.actions import SkipAction
from textual.binding import Binding
from textual.geometry import Offset
from textual import getters
from textual.message import Message
from textual.widgets import OptionList, TextArea
from textual import containers
from textual.widgets.option_list import Option
from textual import events


from toad.widgets.markdown_textarea import MarkdownTextArea
from toad.widgets.condensed_path import CondensedPath
from toad.messages import UserInputSubmitted
from toad.slash_command import SlashCommand


class AutoCompleteOptions(OptionList, can_focus=False):
    pass


class PromptTextArea(MarkdownTextArea):
    BINDING_GROUP_TITLE = "Prompt"
    BINDINGS = [Binding("ctrl+j", "newline", "New line", key_display="⇧+enter")]

    auto_completes: var[list[Option]] = var(list)

    class Submitted(Message):
        def __init__(self, markdown: str) -> None:
            self.markdown = markdown
            super().__init__()

    def on_mount(self) -> None:
        self.highlight_cursor_line = False

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(UserInputSubmitted(self.text))
            self.clear()

    def action_newline(self) -> None:
        self.insert("\n")

    def action_cursor_up(self, select: bool = False):
        if self.auto_completes:
            self.post_message(Prompt.AutoCompleteMove(-1))
        else:
            super().action_cursor_up(select)

    def action_cursor_down(self, select: bool = False):
        if self.auto_completes:
            self.post_message(Prompt.AutoCompleteMove(+1))
        else:
            super().action_cursor_down(select)


class Prompt(containers.VerticalGroup):
    BINDINGS = [Binding("escape", "dismiss", "Dismiss", show=False)]
    prompt_text_area = getters.query_one(PromptTextArea)

    auto_completes: var[list[Option]] = var(list)
    slash_commands: var[list[SlashCommand]] = var(list)

    @dataclass
    class AutoCompleteMove(Message):
        direction: int

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

    @property
    def auto_complete(self) -> AutoCompleteOptions:
        return self.screen.query_one(AutoCompleteOptions)

    @property
    def text(self) -> str:
        return self.prompt_text_area.text

    def focus(self) -> None:
        self.query(MarkdownTextArea).focus()

    def append(self, text: str) -> None:
        self.query_one(MarkdownTextArea).insert(text)

    def watch_auto_completes(self, auto_complete: list[Option]) -> None:
        if auto_complete:
            self.auto_complete.set_options(auto_complete)
            self.auto_complete.action_cursor_down()
            self.auto_complete.display = True
        else:
            self.auto_complete.display = False
            self.auto_complete.clear_options()

    def set_auto_completes(self, auto_completes: list[Option] | None) -> None:
        self.auto_completes = auto_completes.copy() if auto_completes else []

    def show_auto_complete(self, show: bool) -> None:
        self.auto_complete.display = show
        cursor_row, cursor_column = self.prompt_text_area.selection.end
        line = self.prompt_text_area.document.get_line(cursor_row)
        post_cursor = line[cursor_column:]
        pre_cursor = line[:cursor_column]
        self.load_suggestions(pre_cursor, post_cursor)

    @on(MarkdownTextArea.CursorMove)
    def on_cursor_move(self, event: MarkdownTextArea.CursorMove) -> None:
        selection = event.selection
        if selection.end != selection.start:
            self.auto_complete.display = False
            return

        self.show_auto_complete(self.prompt_text_area.cursor_at_end_of_line)

        cursor_offset = self.prompt_text_area.cursor_screen_offset + (-2, 1)
        self.auto_complete.styles.offset = cursor_offset
        event.stop()

    @on(TextArea.Changed)
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        cursor_row, cursor_column = self.prompt_text_area.selection.end
        line = self.prompt_text_area.document.get_line(cursor_row)
        post_cursor = line[cursor_column:]
        pre_cursor = line[:cursor_column]
        self.load_suggestions(pre_cursor, post_cursor)

    @on(AutoCompleteMove)
    def on_auto_complete_move(self, event: AutoCompleteMove) -> None:
        if self.auto_complete.display:
            if event.direction == -1:
                self.auto_complete.action_cursor_up()
            else:
                self.auto_complete.action_cursor_down()

    def suggest(self, suggestion: str) -> None:
        if suggestion.startswith(self.text) and self.text != suggestion:
            self.prompt_text_area.suggestion = suggestion[len(self.text) :]

    @work(exclusive=True)
    async def load_suggestions(self, pre_cursor: str, post_cursor: str) -> None:
        if post_cursor:
            self.set_auto_completes(None)
            return
        pre_cursor = pre_cursor.casefold()
        post_cursor = post_cursor.casefold()
        suggestions: list[Option] = []

        if not pre_cursor:
            self.set_auto_completes(None)
            return

        command_length = (
            max(
                cell_len(slash_command.command) for slash_command in self.slash_commands
            )
            + 1
        )

        for slash_command in self.slash_commands:
            if str(slash_command).startswith(pre_cursor) and pre_cursor != str(
                slash_command
            ):
                suggestions.append(
                    Option(
                        slash_command.content.expand_tabs(command_length),
                        id=slash_command.command,
                    )
                )

        self.set_auto_completes(suggestions)

    @on(events.DescendantBlur, "PromptTextArea")
    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        self.auto_complete.display = False

    @on(events.DescendantFocus, "PromptTextArea")
    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        self.auto_complete.display = True

    def compose(self) -> ComposeResult:
        yield PromptTextArea().data_bind(Prompt.auto_completes)
        with containers.HorizontalGroup():
            yield CondensedPath()

    def action_dismiss(self) -> None:
        if self.auto_complete.display:
            self.auto_complete.display = False
        else:
            raise SkipAction()
