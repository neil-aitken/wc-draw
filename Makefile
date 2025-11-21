test:
	uv run pytest

lint:
	uv run ruff check

format: 
	uv run ruff format

all: test lint format

cli:
	uv run python -m wc_draw.cli $(ARGS)

draw:
	# Run the full draw for pots 1..4 (use ARGS to pass --seed or other flags)
	uv run python -m wc_draw.cli --draw-all $(ARGS)

.PHONY: help
help:
	@echo "Usage: make <target> [ARGS=\"...\"]"
	@echo "Available targets:"
	@echo "  test        - run the test suite (uv run pytest)"
	@echo "  lint        - run ruff linting (uv run ruff check)"
	@echo "  format      - auto-format code with ruff (uv run ruff format)"
	@echo "  all         - run test, lint, format"
	@echo "  cli         - run the project CLI (forward ARGS to CLI)"
	@echo "                 e.g. make cli ARGS=\"--draw-pot1 --seed 42\""
	@echo "  draw        - run the draw for pots 1..3 (forward ARGS to CLI)"
	@echo "                 e.g. make draw ARGS=\"--seed 42\""
