#!/bin/bash
# Full scenario analysis script
# Run with: nohup bash run_full_analysis.sh > analysis.log 2>&1 &

set -e  # Exit on error

WORKERS=8
START=0
END=10000

echo "=========================================="
echo "World Cup Draw Scenario Analysis"
echo "=========================================="
echo "Start time: $(date)"
echo "Seed range: $START to $END"
echo "Workers: $WORKERS"
echo ""

# Step 1: Run all 3 scenario scans
echo "Step 1/2: Running scenario scans..."
python3 scripts/seed_scan_scenarios.py \
  --start $START \
  --end $END \
  --workers $WORKERS

echo ""
echo "Scenario scans complete at $(date)"
echo ""

# Step 2: Aggregate statistics
echo "Step 2/2: Aggregating statistics..."
python3 scripts/aggregate_scenario_stats.py \
  --baseline seed_scan_baseline.jsonl \
  --playoff-seeding seed_scan_playoff_seeding.jsonl \
  --both-features seed_scan_both_features.jsonl \
  --output scenario_stats.json

echo ""
echo "=========================================="
echo "Analysis complete at $(date)"
echo "=========================================="
echo ""
echo "Output files:"
echo "  - seed_scan_baseline.jsonl"
echo "  - seed_scan_playoff_seeding.jsonl"
echo "  - seed_scan_both_features.jsonl"
echo "  - scenario_stats.json"
echo ""
echo "Next steps:"
echo "  jupyter notebook notebooks/scenario_comparison.ipynb"
