#!/usr/bin/env python3
"""Run seed scans for all 3 viable scenarios.

This script orchestrates running seed_scan_large.py for each viable scenario:
1. Baseline (both flags off)
2. Playoff seeding only
3. Both features combined (winners separated + playoff seeding)

The impossible 4th combination (winners separated alone) is skipped.

Usage:
  python3 scripts/seed_scan_scenarios.py --start 0 --end 10000 --workers 8

This will create 3 output files:
  - seed_scan_baseline.jsonl
  - seed_scan_playoff_seeding.jsonl
  - seed_scan_both_features.jsonl
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run seed scans for all 3 viable draw scenarios")
    parser.add_argument("--start", type=int, default=0, help="Start seed (inclusive)")
    parser.add_argument("--end", type=int, default=10000, help="End seed (exclusive)")
    parser.add_argument("--workers", type=int, default=8, help="Number of worker processes")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=5000,
        help="Primary max attempts for run_full_draw",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=10000,
        help="Retry attempts if primary fails",
    )
    args = parser.parse_args()

    # Define the 3 viable scenarios
    scenarios = [
        {
            "name": "baseline",
            "output": "seed_scan_baseline.jsonl",
            "flags": [],
            "description": "Baseline (standard FIFA rules)",
        },
        {
            "name": "playoff_seeding",
            "output": "seed_scan_playoff_seeding.jsonl",
            "flags": ["--uefa-playoffs-seeded"],
            "description": "UEFA playoff seeding only",
        },
        {
            "name": "both_features",
            "output": "seed_scan_both_features.jsonl",
            "flags": ["--uefa-group-winners-separated", "--uefa-playoffs-seeded"],
            "description": "Both features (winner separation + playoff seeding)",
        },
    ]

    script_path = Path(__file__).parent / "seed_scan_large.py"
    if not script_path.exists():
        print(f"ERROR: {script_path} not found")
        sys.exit(1)

    print(f"Running seed scans for seeds {args.start}..{args.end}")
    print(f"Workers: {args.workers}, max_attempts: {args.max_attempts}")
    print("=" * 70)

    for scenario in scenarios:
        print(f"\nScenario: {scenario['description']}")
        print(f"Output: {scenario['output']}")

        cmd = [
            sys.executable,
            str(script_path),
            "--start",
            str(args.start),
            "--end",
            str(args.end),
            "--workers",
            str(args.workers),
            "--max-attempts",
            str(args.max_attempts),
            "--retry-attempts",
            str(args.retry_attempts),
            "--output",
            scenario["output"],
        ]
        cmd.extend(scenario["flags"])

        print(f"Command: {' '.join(cmd)}")
        print("-" * 70)

        try:
            subprocess.run(cmd, check=True, capture_output=False)
            print(f"✓ Completed {scenario['name']}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed {scenario['name']}: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n✗ Interrupted by user")
            sys.exit(1)

        print("=" * 70)

    print("\n✓ All 3 scenarios completed successfully")
    print("\nOutput files:")
    for scenario in scenarios:
        print(f"  - {scenario['output']}")


if __name__ == "__main__":
    main()
