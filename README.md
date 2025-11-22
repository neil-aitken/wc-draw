# wc-draw

World Cup draw simulator with support for multiple rule scenarios and large-scale probability analysis.

## Features
- **Full draw simulation** for 2026 World Cup (48 teams, 12 groups)
- **Scenario analysis** across different rule interpretations
- **UEFA constraint support** (group winner separation)
- **Dynamic pot assignment** (playoff seeding by FIFA ranking)
- **Large-scale seed scanning** for probability analysis
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

## Teams CSV Format

The `teams.csv` file defines all teams and their attributes:

```csv
name,confederation,pot,host,fixed_group,allowed_confederations,fifa_ranking,uefa_group_winner
Spain,UEFA,1,false,,,1,true
England,UEFA,1,false,,,4,true
...
UEFA Playoff A,UEFA | CONMEBOL,4,false,,UEFA | CONMEBOL,,false
```

### Required Fields

- **name**: Team name or playoff path identifier
- **confederation**: Primary confederation (UEFA, CONMEBOL, CAF, AFC, CONCACAF, OFC)
- **pot**: Pot number (1-4) based on FIFA rankings
- **host**: Boolean indicating if team is a host nation
- **fixed_group**: Group letter (A-L) for host nations, empty otherwise
- **allowed_confederations**: For playoff paths, pipe-separated list of possible confederations
- **fifa_ranking**: FIFA ranking number (used for dynamic pot assignment)
- **uefa_group_winner**: Boolean indicating if team won a UEFA qualifying group

### Playoff Paths

Playoff paths are placeholder teams with uncertain confederation:
- Use pipe-separated confederations: `UEFA | CONMEBOL`
- Leave `fifa_ranking` empty unless using playoff seeding feature
- Set `uefa_group_winner=false` (paths cannot be group winners)

### UEFA Group Winners

Teams marked with `uefa_group_winner=true` are subject to the separation constraint when enabled:
- At most one UEFA group winner per World Cup group
- Currently 12 UEFA group winners (one per group)
- Requires playoff seeding to work (otherwise mathematically impossible)

## CLI

This project includes a CLI for running draws and inspecting team data.

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

### Feature Toggles

The draw simulator supports two optional features that change draw behavior:

#### UEFA Group Winner Separation

Enforces that at most one UEFA qualifying group winner appears in each World Cup group:

```bash
make draw ARGS="--uefa-group-winners-separated --uefa-playoffs-seeded --seed 42"
```

**Important**: This constraint requires `--uefa-playoffs-seeded` to work. Using it alone is impossible due to over-constrained pot 4.

#### UEFA Playoff Seeding

Assigns UEFA playoff paths to pots 2-3 based on FIFA rankings instead of keeping them all in pot 4:

```bash
make draw ARGS="--uefa-playoffs-seeded --seed 42"
```

This feature:
- Moves UEFA Playoff A (Italy, rank 12) → Pot 2
- Moves UEFA Playoff D (Czechia, rank 21) → Pot 2
- Moves UEFA Playoff B (Ukraine, rank 28) → Pot 3
- Moves UEFA Playoff C (Slovakia, rank 25) → Pot 3
- Reduces pot 4 from 8 to 4 teams (0 UEFA teams)

### Combined Features

Both features work together to enable the UEFA constraint:

```bash
make draw ARGS="--uefa-group-winners-separated --uefa-playoffs-seeded --seed 42"
```

This combination has a 100% success rate with the default retry limit.

## Scenario Analysis

The project supports analyzing draw probabilities across 3 viable rule scenarios. See [SCENARIO_ANALYSIS.md](SCENARIO_ANALYSIS.md) for detailed instructions.

### Quick Start

1. **Scan all scenarios** (10,000 seeds each):
   ```bash
   python3 scripts/seed_scan_scenarios.py --start 0 --end 10000 --workers 8
   ```

2. **Aggregate statistics**:
   ```bash
   python3 scripts/aggregate_scenario_stats.py
   ```

3. **Analyze in Jupyter**:
   ```bash
   jupyter notebook notebooks/scenario_comparison.ipynb
   ```

### The 3 Viable Scenarios

1. **Baseline**: Standard FIFA rules (both flags off)
2. **Playoff Seeding**: Dynamic pot assignment only
3. **Both Features**: Winner separation + playoff seeding

**Note**: The 4th combination (winner separation alone) is impossible and automatically skipped.

### Output Files

- `seed_scan_baseline.jsonl` - Baseline scenario results
- `seed_scan_playoff_seeding.jsonl` - Playoff seeding scenario results
- `seed_scan_both_features.jsonl` - Combined features scenario results
- `scenario_stats.json` - Aggregated statistics for all scenarios

See [SCENARIO_ANALYSIS.md](SCENARIO_ANALYSIS.md) for:
- Detailed usage instructions
- Performance tuning tips
- Large-scale scan guidance (100k+ seeds)
- Analysis examples and troubleshooting

## Migration Guide

If you have an existing `teams.csv` from an earlier version, see [MIGRATION.md](MIGRATION.md) for upgrade instructions.

## Notes

- The default retry limit is 5,000 attempts (increased from 500 for reliability)
- The draw algorithm uses multiple fallback strategies (alternate pot ordering, global backtracking)
- Success rates: Baseline ~100%, Playoff Seeding ~100%, Both Features ~100% (with default retries)
