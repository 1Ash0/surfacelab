.PHONY: check test install

install:
	uv sync --all-groups

check:
	uv run ruff check src/ tests/
	uv run pyright
	uv run pytest tests/ -x -q

test:
	uv run pytest tests/ -x -q
