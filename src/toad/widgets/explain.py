from textual.app import ComposeResult
from textual import work
from textual import containers
from textual.widgets import Markdown
from textual import getters

import llm


SYSTEM = """\
You are a helpful programming assistant. You will explain the user's requested programming topic clearly an succinctly.
"""


class Explain(containers.VerticalScroll):
    BORDER_TITLE = "Explain"
    BINDINGS = [("escape", "dismiss", "Dismiss explainer")]

    content = getters.query_one(Markdown)

    def compose(self) -> ComposeResult:
        yield Markdown()

    async def action_dismiss(self) -> None:
        self.display = False
        await self.content.update("")
        self.screen.focus()

    def on_mount(self) -> None:
        self.content.anchor()

    # async def on_blur(self) -> None:
    #     self.display = False
    #     await self.content.update("")

    @work(thread=True)
    def send_prompt(self, prompt: str) -> None:
        """Get the response in a thread."""
        self.focus()
        self.display = True
        self.model = llm.get_model("gpt-4o")
        llm_response = self.model.prompt(prompt, system=SYSTEM)
        content = self.content
        for chunk in llm_response:
            self.app.call_from_thread(content.append, chunk)
