test:
	uv run pytest -m "not slow"

lint:
	uv run ruff check

lint-fix:
	uv run ruff check --fix

format: 
	uv run ruff format

all: test lint format

cli:
	uv run python -m wc_draw.cli $(ARGS)

draw:
	# Run the full draw for pots 1..4 (use ARGS to pass --seed or other flags)
	uv run python -m wc_draw.cli --draw-all $(ARGS)

test-all:
	uv run pytest

.PHONY: help
help:
	@echo "Usage: make <target> [ARGS=\"...\"]"
	@echo "Available targets:"
	@echo "  test        - run unit tests only (excludes slow tests)"
	@echo "  test-all    - run all tests including slow harness tests"
	@echo "  lint        - run ruff linting (uv run ruff check)"
	@echo "  lint-fix    - auto-fix safe linting errors (uv run ruff check --fix)"
	@echo "  format      - auto-format code with ruff (uv run ruff format)"
	@echo "  all         - run test, lint, format"
	@echo "  cli         - run the project CLI (forward ARGS to CLI)"
	@echo "                 e.g. make cli ARGS=\"--draw-pot1 --seed 42\""
	@echo "  draw        - run the draw for pots 1..3 (forward ARGS to CLI)"
	@echo "                 e.g. make draw ARGS=\"--seed 42\""
