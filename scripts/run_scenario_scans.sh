#!/bin/bash
# Run seed scans for all scenarios
#
# Usage:
#   ./scripts/run_scenario_scans.sh [NUM_SEEDS] [NUM_WORKERS]
#
# Example:
#   ./scripts/run_scenario_scans.sh 10000 8

set -e

NUM_SEEDS=${1:-10000}
NUM_WORKERS=${2:-8}

echo "Running scenario seed scans with $NUM_SEEDS seeds using $NUM_WORKERS workers"
echo "=" | awk '{for(i=0;i<70;i++)printf"=";printf"\n"}'

# Baseline (no features)
echo ""
echo "1. Baseline (no features)..."
python3 scripts/seed_scan_large.py \
  --start 0 \
  --end $NUM_SEEDS \
  --workers $NUM_WORKERS \
  --output seed_scan_baseline.jsonl

# Playoff seeding only
echo ""
echo "2. Playoff seeding only..."
python3 scripts/seed_scan_large.py \
  --start 0 \
  --end $NUM_SEEDS \
  --workers $NUM_WORKERS \
  --uefa-playoffs-seeded \
  --output seed_scan_playoff_seeding.jsonl

# Both UEFA features
echo ""
echo "3. Both UEFA features (playoff seeding + group winners separated)..."
python3 scripts/seed_scan_large.py \
  --start 0 \
  --end $NUM_SEEDS \
  --workers $NUM_WORKERS \
  --uefa-playoffs-seeded \
  --uefa-group-winners-separated \
  --output seed_scan_both_features.jsonl

# FIFA official constraints
echo ""
echo "4. FIFA official constraints..."
python3 scripts/seed_scan_large.py \
  --start 0 \
  --end $NUM_SEEDS \
  --workers $NUM_WORKERS \
  --fifa-official-constraints \
  --output seed_scan_fifa_official.jsonl

echo ""
echo "=" | awk '{for(i=0;i<70;i++)printf"=";printf"\n"}'
echo "✓ All scenario scans complete!"
echo ""
echo "To aggregate statistics, run:"
echo "  python3 scripts/aggregate_scenario_stats.py"
