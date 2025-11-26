# Scenario Analysis Scripts - Quick Reference

## Overview

These scripts enable large-scale Monte Carlo simulation of World Cup draw scenarios with different constraint configurations.

## Scripts

### 1. `seed_scan_large.py`
Main script for running seed scans with configurable constraints.

**Features:**
- Multi-process parallel execution
- Configurable constraints (UEFA, FIFA official)
- JSONL output (one line per seed)
- Resume capability (appends to existing files)

**Usage:**
```bash
python3 scripts/seed_scan_large.py \
  --start 0 \
  --end 10000 \
  --workers 8 \
  --output seed_scan_baseline.jsonl
```

**Options:**
- `--start N` - Starting seed (inclusive)
- `--end N` - Ending seed (exclusive)
- `--workers N` - Number of parallel workers
- `--uefa-playoffs-seeded` - Enable dynamic pot assignment
- `--uefa-group-winners-separated` - Separate UEFA group winners
- `--fifa-official-constraints` - Enable FIFA's top 4 bracket separation
- `--output FILE` - Output JSONL file

### 2. `aggregate_scenario_stats.py`
Aggregates statistics from JSONL files into comparative analysis.

**Usage:**
```bash
python3 scripts/aggregate_scenario_stats.py \
  --baseline seed_scan_baseline.jsonl \
  --playoff-seeding seed_scan_playoff_seeding.jsonl \
  --both-features seed_scan_both_features.jsonl \
  --fifa-official seed_scan_fifa_official.jsonl \
  --output scenario_stats.json
```

**Output format:**
```json
{
  "baseline": {
    "total_runs": 10000,
    "success_rate": 1.0,
    "teams": {
      "Spain": {
        "group_pct": {"A": 0.0, "B": 0.0, "C": 11.2, ...},
        "pair_pct": {"Argentina": 8.3, ...}
      }
    }
  }
}
```

### 3. `run_scenario_scans.sh`
Convenience script to run all scenarios at once.

**Usage:**
```bash
# Run with defaults (10,000 seeds, 8 workers)
./scripts/run_scenario_scans.sh

# Custom configuration
./scripts/run_scenario_scans.sh 50000 12
```

**Scenarios executed:**
1. **Baseline** - No features (pure random draw with confederation rules)
2. **Playoff Seeding** - UEFA playoffs seeded by ranking
3. **Both Features** - Playoff seeding + UEFA group winner separation
4. **FIFA Official** - Top 4 bracket separation constraints

## Workflow

### Quick Test (100 seeds)
```bash
./scripts/run_scenario_scans.sh 100 4
python3 scripts/aggregate_scenario_stats.py
```

### Production Run (50,000+ seeds)
```bash
# Run overnight with 12 workers
nohup ./scripts/run_scenario_scans.sh 50000 12 > scan.log 2>&1 &

# Monitor progress
tail -f scan.log

# Aggregate when complete
python3 scripts/aggregate_scenario_stats.py
```

### Custom Scenario
```bash
# Example: FIFA constraints with large seed range
python3 scripts/seed_scan_large.py \
  --start 0 \
  --end 100000 \
  --workers 16 \
  --fifa-official-constraints \
  --output fifa_large_scan.jsonl
```

## Performance

- **Baseline:** ~10-20 draws/sec per worker
- **FIFA Official:** ~10-20 draws/sec per worker (no retries needed!)
- **Both Features:** ~5-10 draws/sec per worker (some deadlocks)

**Recommended:**
- Use `cpu_count - 1` workers for local runs
- For cloud: scale to available cores
- Monitor memory: ~100MB per worker

## Output Files

### JSONL Format (seed_scan_*.jsonl)
```jsonl
{"meta": {"start": 0, "end": 10000, ...}}
{"seed": 0, "success": true, "groups": {...}, "fallback": null}
{"seed": 1, "success": true, "groups": {...}, "fallback": null}
...
```

### Stats Format (scenario_stats.json)
- Group probabilities per team per scenario
- Pairwise co-occurrence probabilities
- Success rates and metadata

## Analysis Examples

### Compare Team Distribution
```python
import json

with open("scenario_stats.json") as f:
    stats = json.load(f)

# Scotland in baseline vs FIFA official
baseline = stats["baseline"]["teams"]["Scotland"]["group_pct"]
fifa = stats["fifa_official"]["teams"]["Scotland"]["group_pct"]

for group in sorted(baseline.keys()):
    print(f"Group {group}: {baseline[group]:.1f}% → {fifa[group]:.1f}%")
```

### Success Rate Comparison
```python
for scenario, data in stats.items():
    print(f"{scenario}: {data['success_rate']*100:.2f}%")
```

## Notes

- **Position Mapping:** Results include FIFA's official position-to-pot mappings
- **Reproducibility:** Same seed always produces same draw (with same config)
- **Hosts:** Mexico (A), Canada (B), USA (D) pre-allocated in all scenarios
- **Validation:** All constraints validated after each draw

## Troubleshooting

**Low success rate:**
- Increase `--max-attempts` (default: 2000)
- Increase `--retry-attempts` (default: 10000)
- Check constraint compatibility

**Slow performance:**
- Reduce worker count (too many can cause contention)
- Use faster storage for output files
- Monitor CPU/memory usage

**Memory issues:**
- Reduce `--chunk-size` (default: 1000)
- Use fewer workers
- Process in smaller batches
