
run := uv run toad

.PHONY: run
run:
	$(run)

.PHONY: acp
acp:
	$(run) acp "gemini --experimental-acp"
