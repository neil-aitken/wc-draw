# Scenario Analysis Guide

This guide explains how to run draw probability analysis across different rule scenarios.

## Overview

The project supports analyzing 3 viable draw scenarios:

1. **Baseline** - Standard FIFA rules (both feature flags off)
2. **Playoff Seeding** - UEFA playoff paths seeded to pots 2-3 by FIFA ranking
3. **Both Features** - Winner separation constraint + playoff seeding

**Note**: The 4th combination (winner separation alone) is impossible due to over-constrained pot 4.

## Quick Start

### 1. Run Scenario Scans

Scan 10,000 seeds across all 3 scenarios (takes several minutes):

```bash
python3 scripts/seed_scan_scenarios.py --start 0 --end 10000 --workers 8
```

This creates 3 output files:
- `seed_scan_baseline.jsonl`
- `seed_scan_playoff_seeding.jsonl`
- `seed_scan_both_features.jsonl`

### 2. Aggregate Statistics

Process the JSONL files into aggregated stats:

```bash
python3 scripts/aggregate_scenario_stats.py \
  --baseline seed_scan_baseline.jsonl \
  --playoff-seeding seed_scan_playoff_seeding.jsonl \
  --both-features seed_scan_both_features.jsonl \
  --output scenario_stats.json
```

### 3. Analyze in Jupyter

Open the comparison notebook:

```bash
jupyter notebook notebooks/scenario_comparison.ipynb
```

The notebook provides:
- Scotland opponent probability comparison across scenarios
- Group distribution analysis
- Change detection (which opponents become more/less likely)
- Correlation analysis between scenarios

## Individual Scenario Scans

If you want to run scenarios separately:

### Baseline (Standard FIFA Rules)

```bash
python3 scripts/seed_scan_large.py \
  --start 0 --end 10000 \
  --workers 8 \
  --output seed_scan_baseline.jsonl
```

### Playoff Seeding Only

```bash
python3 scripts/seed_scan_large.py \
  --start 0 --end 10000 \
  --workers 8 \
  --uefa-playoffs-seeded \
  --output seed_scan_playoff_seeding.jsonl
```

### Both Features Combined

```bash
python3 scripts/seed_scan_large.py \
  --start 0 --end 10000 \
  --workers 8 \
  --uefa-group-winners-separated \
  --uefa-playoffs-seeded \
  --output seed_scan_both_features.jsonl
```

## Performance Tuning

The default `max_attempts=5000` provides 100% success rate for the "both features" scenario. For faster scans of baseline/playoff scenarios, you can reduce this:

```bash
python3 scripts/seed_scan_large.py \
  --start 0 --end 10000 \
  --workers 8 \
  --max-attempts 1000 \
  --output seed_scan_baseline.jsonl
```

## Output Format

### JSONL Files (seed_scan_*.jsonl)

Each line is a JSON object with:
- `seed`: Integer seed value
- `success`: Boolean (draw completed successfully)
- `error`: String error message (if failed)
- `used_seed`: Seed used for the draw
- `groups`: Dict mapping group letters to team name lists
- `fallback`: Metadata about fallback strategies used (if any)

Example:
```json
{
  "seed": 100,
  "success": true,
  "error": null,
  "used_seed": 100,
  "groups": {
    "A": ["Mexico", "Japan", "Paraguay", "UEFA Playoff B"],
    "B": ["Canada", "Iran", "Tunisia", "UEFA Playoff D"],
    ...
  },
  "fallback": null
}
```

### Aggregated Stats (scenario_stats.json)

Structure:
```json
{
  "baseline": {
    "total_runs": 10000,
    "successes": 10000,
    "success_rate": 1.0,
    "teams": {
      "Scotland": {
        "group_pct": {
          "A": 8.3,
          "B": 8.2,
          ...
        },
        "pair_pct": {
          "Argentina": 12.5,
          "Brazil": 11.8,
          ...
        }
      },
      ...
    }
  },
  "playoff_seeding": {...},
  "both_features": {...}
}
```

## Analysis Examples

### Scotland Opponent Analysis

```python
import json
import pandas as pd

with open("scenario_stats.json") as f:
    stats = json.load(f)

# Get Scotland's opponents in baseline scenario
baseline_opps = stats["baseline"]["teams"]["Scotland"]["pair_pct"]
baseline_df = pd.Series(baseline_opps).sort_values(ascending=False)

# Compare to both_features scenario
both_opps = stats["both_features"]["teams"]["Scotland"]["pair_pct"]
both_df = pd.Series(both_opps).sort_values(ascending=False)

# Calculate differences
diff = both_df - baseline_df
print("Biggest increases:")
print(diff.nlargest(10))
print("\nBiggest decreases:")
print(diff.nsmallest(10))
```

### Group Distribution Analysis

```python
# Scotland's group probabilities
baseline_groups = stats["baseline"]["teams"]["Scotland"]["group_pct"]
both_groups = stats["both_features"]["teams"]["Scotland"]["group_pct"]

# Compare distributions
import matplotlib.pyplot as plt
groups = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
baseline_vals = [baseline_groups.get(g, 0) for g in groups]
both_vals = [both_groups.get(g, 0) for g in groups]

plt.figure(figsize=(12, 6))
x = range(len(groups))
width = 0.35
plt.bar([i - width/2 for i in x], baseline_vals, width, label="Baseline")
plt.bar([i + width/2 for i in x], both_vals, width, label="Both Features")
plt.xlabel("Group")
plt.ylabel("Probability (%)")
plt.title("Scotland Group Distribution Comparison")
plt.xticks(x, groups)
plt.legend()
plt.show()
```

## Large-Scale Scans

For production analysis with 100,000+ seeds:

```bash
# Run overnight with nohup
nohup python3 scripts/seed_scan_scenarios.py \
  --start 0 --end 100000 \
  --workers 12 \
  > scenario_scan.log 2>&1 &

# Monitor progress
tail -f scenario_scan.log
```

The scanner prints progress every 1,000 seeds completed.

## Troubleshooting

### Low Success Rate

If you see success rates below 99% for "both_features" scenario:
- Increase `--max-attempts` (default is 5000)
- Increase `--retry-attempts` (default is 10000)

### Out of Memory

If workers crash with memory errors:
- Reduce `--workers`
- Reduce `--chunk-size` (default is 1000)

### Slow Performance

- Use more workers: `--workers $(nproc)` (all CPU cores)
- Run in smaller batches and combine JSONL files later
- Use baseline/playoff scenarios (faster than both_features)

## Implementation Details

### Dynamic Pot Assignment

When `--uefa-playoffs-seeded` is enabled:
- UEFA Playoff A (Italy, rank 12) → Pot 2
- UEFA Playoff D (Czechia, rank 21) → Pot 2
- UEFA Playoff B (Ukraine, rank 28) → Pot 3
- UEFA Playoff C (Slovakia, rank 25) → Pot 3

This reduces pot 4 from 8 teams to 4 teams (0 UEFA teams in pot 4).

### UEFA Constraint

When `--uefa-group-winners-separated` is enabled:
- At most one UEFA group winner per World Cup group
- Requires playoff seeding to work (otherwise impossible)
- 12 UEFA group winners placed across 12 groups (one per group)

### Fallback Strategies

The draw algorithm uses multiple fallback strategies when random placement fails:
1. **Alternate pot ordering**: Try pots in different sequences (2-4-3, 4-2-3, etc.)
2. **Global backtracking**: Systematic search when random attempts exhausted

These are tracked in the `fallback` field of each JSONL record.
