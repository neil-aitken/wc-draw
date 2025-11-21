# wc-draw

A new Python project managed with uv.

## Features
- Environment management with uv
- Testing with pytest
- Linting and formatting with ruff
- Automated workflow with Makefile
- Dev environment setup via devcontainer

## Setup

1. Install [uv](https://github.com/astral-sh/uv):
   ```bash
   pip install uv
   ```
2. Clone the repository and open in VS Code (recommended for devcontainer support).
3. The devcontainer will automatically set up the Python environment and install dependencies on first open.
4. If not using devcontainer, install dependencies manually:
   ```bash
   uv pip install -r requirements.txt
   uv pip install -e .
   ```

## Usage

### Makefile targets

- Run all checks (test, lint, format):
  ```bash
  make all
  ```
- Run tests:
  ```bash
  make test
  ```
- Lint code:
  ```bash
  make lint
  ```
- Format code:
  ```bash
  make format
  ```

### Manual commands

- Run tests:
  ```bash
  uv run pytest
  ```
- Lint code:
  ```bash
  uv run ruff check
  ```
- Format code:
  ```bash
  uv run ruff format
  ```

## Development Environment

- The project supports VS Code devcontainers for reproducible development environments.
- All dependencies and environment setup are handled automatically via the devcontainer configuration.
- Custom scripts and tools can be added to the Makefile for automation.

## Contributing

- Ensure all checks pass with `make all` before submitting changes.
- Follow code style enforced by ruff and format code with `make format`.

## CLI

This project includes a small CLI helper to inspect pots and placeholder slots defined in `teams.csv`.

- Run the CLI (defaults to `teams.csv` in the repo):
  ```bash
  uv run python -m wc_draw.cli
  ```

- Show slots (placeholder playoff/inter-confederation paths):
  ```bash
  uv run python -m wc_draw.cli --slots
  ```

- Output machine-readable JSON (useful for tests or automation):
  ```bash
  uv run python -m wc_draw.cli --json
  ```

- Specify a different teams file:
  ```bash
  uv run python -m wc_draw.cli --teams path/to/teams.csv
  ```

- Run the pot1 draw and show group assignments (A..L):
  ```bash
  uv run python -m wc_draw.cli --draw-pot1
  ```

- Provide a deterministic RNG seed for reproducible draws:
  ```bash
  uv run python -m wc_draw.cli --draw-pot1 --seed 42
  ```

- If you prefer to run via the Makefile, pass arguments using the `ARGS` variable. Example:
  ```bash
  make cli ARGS="--draw-pot1 --seed 42"
  ```

The JSON output contains two keys: `pots` (mapping pot numbers to lists of team names) and `slots` (list of slot objects with `name`, `pot`, `allowed_confederations`, `candidates`, and `fixed_group`).

## Draw helper (pots 1..3)

The CLI now supports running the draw for pots 1 through 3 together. This will:
- Run the pot1 draw (hosts are placed into fixed groups first).
- Place pot2 and pot3 teams while enforcing confederation separation rules (UEFA max 2 per group; non-UEFA max 1).

Examples:

- Run a deterministic draw for pots 1..3 using a seed:
  ```bash
  make draw ARGS="--seed 42"
  ```

- Run the same via the CLI directly:
  ```bash
  uv run python -m wc_draw.cli --draw-pots --seed 42
  ```

Notes:
- The current `--json` output returns only `pots` and `slots`. If you need machine-readable drawn groups, pass `--draw-pots` and capture the CLI output, or ask to add drawn groups to the JSON output.
- The `make draw` target currently runs pots 1..3. Pot4 (and a full `--draw-all`) can be added next — I can implement that if you'd like.
