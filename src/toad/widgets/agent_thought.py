from __future__ import annotations

from textual.reactive import var
from textual.widgets import Markdown
from textual.widgets.markdown import MarkdownStream


class AgentThought(Markdown):
    """The agent's 'thoughts'."""

    _stream: var[MarkdownStream | None] = var(None)

    def watch_loading(self, loading: bool) -> None:
        self.set_class(loading, "-loading")

    @property
    def stream(self) -> MarkdownStream:
        if self._stream is None:
            self._stream = self.get_stream(self)
        return self._stream

    async def append_fragment(self, fragment: str) -> None:
        self.loading = False
        await self.stream.write(fragment)
