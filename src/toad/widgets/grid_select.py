from dataclasses import dataclass

from textual import containers
from textual.binding import Binding
from textual import events
from textual.message import Message
from textual.reactive import reactive
from textual.layouts.grid import GridLayout
from textual.widget import Widget


class GridSelect(containers.ItemGrid, can_focus=True):
    highlighted = reactive(0)

    CURSOR_GROUP = Binding.Group("Move selection", compact=False)
    BINDINGS = [
        Binding("up", "cursor_up", "Cursor Up", group=CURSOR_GROUP),
        Binding("down", "cursor_down", "Cursor Down", group=CURSOR_GROUP),
        Binding("left", "cursor_left", "Cursor Left", group=CURSOR_GROUP),
        Binding("right", "cursor_right", "Cursor Right", group=CURSOR_GROUP),
        Binding("enter", "select", "Select"),
    ]

    @dataclass
    class Selected(Message):
        selected_widget: Widget

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes, min_column_width=30)

    @property
    def grid_size(self) -> tuple[int, int] | None:
        assert isinstance(self.layout, GridLayout)
        return self.layout.grid_size

    def on_focus(self):
        self.reveal_highlight()

    def reveal_highlight(self):
        try:
            highlighted_widget = self.children[self.highlighted]
        except IndexError:
            pass
        else:
            if not self.screen.can_view_entire(highlighted_widget):
                self.screen.scroll_to_center(highlighted_widget, origin_visible=True)

    def watch_highlighted(self, old_highlighted: int, highlighted: int) -> None:
        try:
            self.children[old_highlighted].remove_class("-highlight")
        except IndexError:
            pass
        try:
            highlighted_widget = self.children[highlighted]
            highlighted_widget.add_class("-highlight")
        except IndexError:
            pass
        self.reveal_highlight()

    def validate_highlighted(self, highlighted: int) -> int:
        if highlighted < 0:
            return 0
        if highlighted >= len(self.children):
            return len(self.children) - 1
        return highlighted

    def action_cursor_up(self):
        if (grid_size := self.grid_size) is None:
            return
        width, height = grid_size
        if self.highlighted >= width:
            self.highlighted -= width

    def action_cursor_down(self):
        if (grid_size := self.grid_size) is None:
            return
        width, height = grid_size
        if self.highlighted + width < len(self.children):
            self.highlighted += width

    def action_cursor_left(self):
        self.highlighted -= 1

    def action_cursor_right(self):
        self.highlighted += 1

    def on_click(self, event: events.Click) -> None:
        highlighted_widget: Widget | None = None
        try:
            highlighted_widget = self.children[self.highlighted]
        except IndexError:
            pass
        if event.widget in self.children:
            if highlighted_widget is event.widget:
                self.action_select()
            else:
                self.highlighted = self.children.index(event.widget)

    def action_select(self):
        try:
            highlighted_widget = self.children[self.highlighted]
        except IndexError:
            pass
        else:
            self.post_message(self.Selected(highlighted_widget))


if __name__ == "__main__":
    from textual.app import App, ComposeResult
    from textual import widgets

    class GridApp(App):
        CSS = """
        .grid-item {
            width: 1fr;
            padding: 0 1;
            # background: blue 20%;        
            border: blank;


            &.-highlight {
                border: tall $primary;
                background: $panel;
            }
        }
        """

        def compose(self) -> ComposeResult:
            yield widgets.Footer()
            with GridSelect():
                for n in range(50):
                    yield widgets.Label(
                        f"#{n} Where there is a Will, there is a Way!",
                        classes="grid-item",
                    )

    GridApp().run()
