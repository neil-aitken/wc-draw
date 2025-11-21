test:
	uv run pytest

lint:
	uv run ruff check

format: 
	uv run ruff format

all: test lint format
