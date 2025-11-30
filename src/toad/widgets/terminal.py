import asyncio
from time import monotonic
from typing import Callable

from textual.cache import LRUCache

from textual import events
from textual.reactive import reactive
from textual.selection import Selection
from textual.style import Style
from textual.geometry import Region, Size
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.timer import Timer


from toad import ansi


# Time required to double tab escape
ESCAPE_TAP_DURATION = 400 / 1000


class Terminal(ScrollView, can_focus=True):
    CURSOR_STYLE = Style.parse("reverse")

    hide_cursor = reactive(False)

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        minimum_terminal_width: int = -1,
        size: tuple[int, int] | None = None,
        get_terminal_dimensions: Callable[[], tuple[int, int]] | None = None,
    ):
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.minimum_terminal_width = minimum_terminal_width
        self._get_terminal_dimensions = get_terminal_dimensions

        self.state = ansi.TerminalState()

        if size is None:
            self._width: int = (
                80 if minimum_terminal_width < 0 else minimum_terminal_width
            )
            self._height: int = 24
        else:
            width, height = size
            self._width = width
            self._height = height
            if minimum_terminal_width == -1:
                self.minimum_terminal_width = width

        self.max_window_width = 0
        self._escape_time = monotonic()
        self._escaping = False
        self._escape_reset_timer: Timer | None = None
        self._finalized: bool = False
        self.current_directory: str | None = None

        self._terminal_render_cache: LRUCache[tuple, Strip] = LRUCache(1024)

    @property
    def is_finalized(self) -> bool:
        return self._finalized

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def finalize(self) -> None:
        """FInalize the terminal.

        The finalized terminal will reject new writes.
        Adds the TCSS class `-finalizes`
        """
        self._finalized = True
        self.add_class("-finalized")

    def get_selection(self, selection: Selection) -> tuple[str, str] | None:
        """Get the text under the selection.

        Args:
            selection: Selection information.

        Returns:
            Tuple of extracted text and ending (typically "\n" or " "), or `None` if no text could be extracted.
        """
        text = "\n".join(
            line_record.content.plain for line_record in self.state.buffer.lines
        )
        return selection.extract(text), "\n"

    def _on_resize(self, event: events.Resize) -> None:
        if self._get_terminal_dimensions is None:
            width, height = self.scrollable_content_region.size
        else:
            width, height = self._get_terminal_dimensions()
        print("RESIZE", width, height)
        self.update_size(width, height)

    def update_size(self, width: int, height: int) -> None:
        print("UPDATE SIZE", width, height)
        self._terminal_render_cache.grow(height * 2)
        # width = width or 80
        # if window_width == self._width:
        #     return
        # self._width = window_width
        # self.max_window_width = max(self.max_window_width, window_width)
        # if self.minimum_terminal_width == -1 and window_width:
        #     self.minimum_terminal_width = window_width
        # width = max(
        #     self.minimum_terminal_width,
        #     max(min(self.state.max_line_width, self.max_window_width), window_width),
        # )
        self._width = width or 80
        self._height = height or 24

        print("SETTING SIZE to", self._width, self._height)
        self.state.update_size(self._width, height)

        self._terminal_render_cache.clear()
        self.refresh()

    def on_mount(self) -> None:
        self.auto_links = False
        self.anchor()
        if self._get_terminal_dimensions is None:
            width, height = self.scrollable_content_region.size
        else:
            width, height = self._get_terminal_dimensions()
        self.update_size(width, height)

    def write(self, text: str) -> bool:
        """Write sequences to the terminal.

        Args:
            text: Text with ANSI escape sequences.

        Returns:
            `True` if the state visuals changed, `False` if no visual change.
        """
        from textual._profile import timer

        with timer(f"write {len(text)} characters"):
            scrollback_delta, alternate_delta = self.state.write(text)
        with timer("Update widget"):
            self._update_from_state(scrollback_delta, alternate_delta)
        print("WRITE WIDTH", self._width)
        return bool(scrollback_delta or alternate_delta)

    def _update_from_state(
        self, scrollback_delta: set[int] | None, alternate_delta: set[int] | None
    ) -> None:
        if self.state.current_directory:
            self.add_class("-finalized")
            self.current_directory = self.state.current_directory
        width = self.state.width
        height = self.state.scrollback_buffer.height
        if self.state.alternate_screen:
            height += self.state.alternate_buffer.height
        self.virtual_size = Size(min(self.state.buffer.max_line_width, width), height)
        if self._anchored and not self._anchor_released:
            self.scroll_y = self.max_scroll_y

        scroll_y = int(self.scroll_y)
        visible_lines = frozenset(range(scroll_y, scroll_y + height))

        if scrollback_delta is None and alternate_delta is None:
            self.refresh()
        else:
            window_width = self.region.width
            scrollback_height = self.state.scrollback_buffer.line_count
            if scrollback_delta is None:
                self.refresh(Region(0, 0, window_width, scrollback_height))
            else:
                refresh_lines = [
                    Region(0, y - scroll_y, window_width, 1)
                    for y in sorted(scrollback_delta & visible_lines)
                ]
                if refresh_lines:
                    self.refresh(*refresh_lines)
            alternate_height = self.state.alternate_buffer.line_count
            if alternate_delta is None:
                self.refresh(
                    Region(
                        0,
                        scrollback_height - scroll_y,
                        window_width,
                        scrollback_height + alternate_height,
                    )
                )
            else:
                alternate_delta = {
                    line_no + scrollback_height for line_no in alternate_delta
                }
                refresh_lines = [
                    Region(0, y - scroll_y, window_width, 1)
                    for y in sorted(alternate_delta & visible_lines)
                ]
                if refresh_lines:
                    self.refresh(*refresh_lines)

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        strip = self._render_line(scroll_x, scroll_y + y, self._width)
        return strip

    def on_focus(self) -> None:
        self.border_subtitle = "Tap [b]esc[/b] [i]twice[/i] to exit"

    def on_blur(self) -> None:
        self.border_subtitle = "Click to focus"

    def _render_line(self, x: int, y: int, width: int) -> Strip:
        selection = self.text_selection
        visual_style = self.visual_style
        rich_style = visual_style.rich_style

        state = self.state
        buffer = state.scrollback_buffer
        buffer_offset = 0
        if y >= len(buffer.folded_lines) and state.alternate_screen:
            buffer_offset = len(buffer.folded_lines)
            buffer = state.alternate_buffer
        try:
            folded_line = buffer.folded_lines[y - buffer_offset]
            line_no, line_offset, offset, line, updates = folded_line
        except IndexError:
            return Strip.blank(width, rich_style)

        line_record = buffer.lines[line_no]
        cache_key: tuple | None = (
            self.state.alternate_screen,
            y,
            line_record.updates,
            updates,
        )
        cache_key = None  # REMOVE

        if (
            not self.hide_cursor
            and state.show_cursor
            and buffer.cursor_line == y - buffer_offset
        ):
            if buffer.cursor_offset >= len(line):
                line = line.pad_right(buffer.cursor_offset - len(line) + 1)
            line_cursor_offset = buffer.cursor_offset
            line = line.stylize(
                self.CURSOR_STYLE, line_cursor_offset, line_cursor_offset + 1
            )
            cache_key = None

        if (
            not selection
            and cache_key is not None
            and (strip := self._terminal_render_cache.get(cache_key))
        ):
            strip = strip.crop(x, x + width)
            strip = strip.adjust_cell_length(
                width, (visual_style + line_record.style).rich_style
            )
            strip = strip.apply_offsets(x + offset, line_no)
            return strip

        if selection is not None and (select_span := selection.get_span(line_no)):
            unfolded_content = line_record.content.expand_tabs(8)
            start, end = select_span
            if end == -1:
                end = len(unfolded_content)
            selection_style = self.screen.get_visual_style("screen--selection")
            unfolded_content = unfolded_content.stylize(selection_style, start, end)
            try:
                folded_line = self.state._fold_line(line_no, unfolded_content, width)
                line = folded_line[line_offset].content
                cache_key = None
            except IndexError:
                pass

        strip = Strip(line.render_segments(visual_style), cell_length=line.cell_length)

        if cache_key is not None:
            self._terminal_render_cache[cache_key] = strip

        strip = strip.crop(x, x + width)
        strip = strip.adjust_cell_length(
            width, (visual_style + line_record.style).rich_style
        )
        strip = strip.apply_offsets(x + offset, line_no)

        return strip

    def _reset_escaping(self) -> None:
        if self._escaping:
            self.write_process_stdin(self.state.key_escape())
        self._escaping = False

    def on_key(self, event: events.Key):
        event.prevent_default()
        event.stop()

        if event.key == "escape":
            if self._escaping:
                if monotonic() < self._escape_time + ESCAPE_TAP_DURATION:
                    self.blur()
                    self._escaping = False
                    return
                else:
                    self.write_process_stdin(self.state.key_escape())
            else:
                self._escaping = True
                self._escape_time = monotonic()
                self._escape_reset_timer = self.set_timer(
                    ESCAPE_TAP_DURATION, self._reset_escaping
                )
                return
        else:
            self._reset_escaping()
            if self._escape_reset_timer is not None:
                self._escape_reset_timer.stop()

        if (stdin := self.state.key_event_to_stdin(event)) is not None:
            self.write_process_stdin(stdin)

    def on_paste(self, event: events.Paste) -> None:
        for character in event.text:
            print(repr(character))
            self.write_process_stdin(character)

    def write_process_stdin(self, input: str) -> None:
        pass


if __name__ == "__main__":
    from textual.app import App, ComposeResult

    TEST = (
        "\033[31mThis is red text\033[0m\n"
        "\033[32mThis is green text\033[0m\n"
        "\033[33mThis is yellow text\033[0m\n"
        "\033[34mThis is blue text\033[0m\n"
        "\033[35mThis is magenta text\033[0m\n"
        "\033[36mThis is cyan text\033[0m\n"
        "\033[1mThis is bold text\033[0m\n"
        "\033[4mThis is underlined text\033[0m\n"
        "\033[1;31mThis is bold red text\033[0m\n"
        "\033[42mThis has a green background\033[0m\n"
        "\033[97;44mWhite text on blue background\033[0m"
    )

    class TApp(App):
        def compose(self) -> ComposeResult:
            yield Terminal()

        def on_mount(self) -> None:
            terminal = self.query_one(Terminal)
            terminal.write(TEST)

    app = TApp()
    app.run()
