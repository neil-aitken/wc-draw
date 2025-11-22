#!/usr/bin/env python3
"""Aggregate statistics from scenario JSONL files.

This script reads the JSONL output from seed_scan_scenarios.py and produces
per-scenario draw statistics similar to draw_stats.json, but with scenario labels.

Output format:
{
  "baseline": {
    "total_runs": N,
    "success_rate": 0.XX,
    "teams": {...}
  },
  "playoff_seeding": {...},
  "both_features": {...}
}

Usage:
  python3 scripts/aggregate_scenario_stats.py \\
    --baseline seed_scan_baseline.jsonl \\
    --playoff-seeding seed_scan_playoff_seeding.jsonl \\
    --both-features seed_scan_both_features.jsonl \\
    --output scenario_stats.json
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any


def aggregate_jsonl(path: Path) -> Dict[str, Any]:
    """Read a JSONL file and aggregate draw statistics."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    total_runs = 0
    successes = 0
    # team -> group -> count
    group_counts = defaultdict(lambda: defaultdict(int))
    # team -> opponent -> count
    pair_counts = defaultdict(lambda: defaultdict(int))

    with open(path, "r") as fh:
        for line in fh:
            obj = json.loads(line)
            # Skip metadata header
            if "meta" in obj:
                continue

            total_runs += 1
            if not obj.get("success", False):
                continue

            successes += 1
            groups = obj.get("groups", {})

            # Aggregate group occupancy
            for group_label, team_names in groups.items():
                for team_name in team_names:
                    group_counts[team_name][group_label] += 1

            # Aggregate pairwise co-occurrence (undirected)
            for group_label, team_names in groups.items():
                for i, team1 in enumerate(team_names):
                    for team2 in team_names[i + 1 :]:
                        pair_counts[team1][team2] += 1
                        pair_counts[team2][team1] += 1

    # Convert counts to percentages
    teams_stats = {}
    for team in group_counts:
        group_pct = {
            grp: (count / successes * 100.0) if successes > 0 else 0.0
            for grp, count in group_counts[team].items()
        }
        pair_pct = {
            opp: (count / successes * 100.0) if successes > 0 else 0.0
            for opp, count in pair_counts[team].items()
        }
        teams_stats[team] = {
            "group_pct": group_pct,
            "pair_pct": pair_pct,
        }

    return {
        "total_runs": total_runs,
        "successes": successes,
        "success_rate": (successes / total_runs) if total_runs > 0 else 0.0,
        "teams": teams_stats,
    }


def main():
    parser = argparse.ArgumentParser(description="Aggregate statistics from scenario JSONL files")
    parser.add_argument(
        "--baseline",
        type=str,
        default="seed_scan_baseline.jsonl",
        help="Path to baseline JSONL",
    )
    parser.add_argument(
        "--playoff-seeding",
        type=str,
        default="seed_scan_playoff_seeding.jsonl",
        help="Path to playoff seeding JSONL",
    )
    parser.add_argument(
        "--both-features",
        type=str,
        default="seed_scan_both_features.jsonl",
        help="Path to both features JSONL",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scenario_stats.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    scenarios = {
        "baseline": Path(args.baseline),
        "playoff_seeding": Path(args.playoff_seeding),
        "both_features": Path(args.both_features),
    }

    print("Aggregating scenario statistics...")
    print("=" * 70)

    results = {}
    for scenario_name, path in scenarios.items():
        print(f"\nProcessing {scenario_name}: {path}")
        try:
            stats = aggregate_jsonl(path)
            results[scenario_name] = stats
            print(f"  ✓ Total runs: {stats['total_runs']}")
            print(f"  ✓ Successes: {stats['successes']}")
            print(f"  ✓ Success rate: {stats['success_rate']:.2%}")
            print(f"  ✓ Teams: {len(stats['teams'])}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            raise

    output_path = Path(args.output)
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True))
    print("\n" + "=" * 70)
    print(f"✓ Wrote aggregated statistics to {output_path}")


if __name__ == "__main__":
    main()
