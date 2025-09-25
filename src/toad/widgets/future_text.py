from __future__ import annotations

from typing import ClassVar
from time import monotonic

from textual.content import Content
from textual.widgets import Static


class FutureText(Static):
    """Text which appears one letter at time, like the movies."""

    BARS: ClassVar[list[str]] = ["▉", "▊", "▋", "▌", "▍", "▎", "▏", " "]

    def __init__(
        self,
        text: Content,
        *,
        speed: float = 20.0,
        cursor_style="$text-error",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        self.text = text
        self.cursor_style = cursor_style
        self.speed = speed
        self.start_time = monotonic()
        super().__init__(name=name, id=id, classes=classes)

    @property
    def time(self) -> float:
        return monotonic() - self.start_time

    def on_mount(self) -> None:
        self.start_time = monotonic()

        self.set_interval(1 / 60, self._update_text)

    def _update_text(self) -> None:
        text = self.text
        speed_time = self.time * self.speed
        progress, fractional_progress = divmod(speed_time, 1)
        end = progress >= len(text)
        cursor_progress = 0 if end else int(fractional_progress * 8)
        text = text[: round(progress)]

        if end:
            opacity = 100 - (int((self.time - len(text)) * 100) % 100)
        else:
            opacity = 100

        bar_character = self.BARS[7 - cursor_progress]
        text += Content.assemble(
            (bar_character, f"reverse $text-error {int(opacity)}%"),
            (bar_character, f"$text-error {int(opacity)}%"),
        )
        self.update(text)


if __name__ == "__main__":
    from textual.app import App, ComposeResult

    TEXT = """Have you ever [i]wondered[/i] why the cursor in terminals is so [blink]jerky[/]?

No? [dim](me either)[/dim].

But it doesn't have to be!

[$text-success]Look how smooooooooooooooth this is![/]

Textual is a lot of fun to play with sometimes... 🙂🙂🙂"""

    class TextApp(App):
        CSS = """
        Screen {
            padding: 2 4;
            FutureText {
                width: auto;
                max-width: 1fr;
                height: auto;
                border: $success;
            }
        }
        """

        def compose(self) -> ComposeResult:
            yield FutureText(Content.from_markup(TEXT))

    TextApp().run()
