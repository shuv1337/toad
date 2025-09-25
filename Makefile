
run := TEXTUAL=devtools uv run toad

.PHONY: run
run:
	$(run)

.PHONY: gemini-acp
gemini-acp:
	$(run) acp "gemini --experimental-acp" --project-dir ~/sandbox

.PHONY: claude-acp
claude-acp:
	$(run) acp "claude-code-acp"
