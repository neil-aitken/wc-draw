#!/usr/bin/env python3
"""Test harness for draw_v2 module with performance metrics."""

import sys
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from wc_draw.parser import parse_teams_config
from wc_draw.pot_assignment import assign_pots
from wc_draw.config import DrawConfig
from wc_draw.draw_v2 import (
    run_draw,
    LookaheadConfig,
    validate_draw,
)


@dataclass
class DrawResult:
    """Result of a single draw attempt."""

    seed: int
    success: bool
    time_ms: float
    error: Optional[str] = None
    quadrant_violations: int = 0


def run_single_draw(seed: int, pots: dict, lookahead_config: LookaheadConfig) -> DrawResult:
    """Run a single draw and return the result."""
    start = time.time()
    try:
        result, _ = run_draw(pots, seed=seed, lookahead=lookahead_config)
        elapsed = (time.time() - start) * 1000
        # Validate the draw for quadrant violations
        violations = validate_draw(result)
        quadrant_violations = sum(1 for v in violations if "separation" in v.lower())
        return DrawResult(
            seed=seed, success=True, time_ms=elapsed, quadrant_violations=quadrant_violations
        )
    except RuntimeError as e:
        elapsed = (time.time() - start) * 1000
        return DrawResult(seed=seed, success=False, time_ms=elapsed, error=str(e))


def run_test(num_seeds: int = 100, lookahead_config: LookaheadConfig = None, num_threads: int = 8):
    """Run draw simulations in parallel and report statistics."""

    # Load teams
    teams_by_pot = parse_teams_config("teams.csv")
    config = DrawConfig()
    pots = assign_pots(teams_by_pot, config)

    if lookahead_config is None:
        # Default: essential constraints only (L3, L6-L9)
        # L1, L2, L4 proven redundant via ablation testing
        lookahead_config = LookaheadConfig(
            l1_uefa_minimum=False,  # Redundant: covered by L7
            l2_inter_path_1=False,  # Redundant: covered by L9
            l3_inter_path_2=True,
            l4_non_uefa_diversity=False,  # Redundant: covered by L3/L7/L9
            l6_pot4_caf_landing=True,
            l7_uefa_slots=True,
            l8_concacaf_slots=True,
            l9_caf_slots=True,
        )

    print(f"Running {num_seeds} draws with {num_threads} parallel processes")
    print(f"Lookahead config: {lookahead_config}")
    print("-" * 60)

    results: List[DrawResult] = []
    failures: List[DrawResult] = []
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=num_threads) as executor:
        # Submit all draws
        futures = {
            executor.submit(run_single_draw, seed, pots, lookahead_config): seed
            for seed in range(num_seeds)
        }

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            if not result.success:
                failures.append(result)
                print(f"  FAIL seed {result.seed}: {result.error or 'no solution'}")

            # Progress update every 10%
            if completed % max(1, num_seeds // 10) == 0:
                print(f"  Progress: {completed}/{num_seeds} ({completed * 100 // num_seeds}%)")

    total_time = time.time() - start_time

    # Aggregate results
    success_count = sum(1 for r in results if r.success)
    total_draw_time = sum(r.time_ms for r in results)
    avg_time = total_draw_time / num_seeds

    # Count quadrant violations
    quadrant_violation_count = sum(1 for r in results if r.success and r.quadrant_violations > 0)

    print("-" * 60)
    print(f"Results: {success_count}/{num_seeds} = {success_count / num_seeds * 100:.1f}%")
    if quadrant_violation_count > 0:
        valid_draws = success_count - quadrant_violation_count
        print(
            f"Quadrant valid: {valid_draws}/{success_count} = "
            f"{valid_draws / success_count * 100:.1f}% of successful draws"
        )
    print(f"Wall time: {total_time:.2f}s")
    print(f"Avg draw time: {avg_time:.1f}ms")
    print(f"Total CPU time: {total_draw_time / 1000:.2f}s")

    if failures:
        print(f"\nFailed seeds: {sorted(r.seed for r in failures)}")

    return success_count, num_seeds


def run_single_seed_verbose(seed: int, lookahead_config: LookaheadConfig):
    """Run a single seed with verbose output for debugging."""
    from wc_draw.draw_v2 import run_draw

    # Load teams
    teams_by_pot = parse_teams_config("teams.csv")
    config = DrawConfig()
    pots = assign_pots(teams_by_pot, config)

    print(f"Testing seed {seed}")
    print(f"Lookahead config: {lookahead_config}")
    print("-" * 60)

    start = time.time()
    try:
        result = run_draw(pots, seed=seed, lookahead=lookahead_config)
        elapsed = (time.time() - start) * 1000

        if result is None:
            print(f"FAIL: No valid draw found ({elapsed:.1f}ms)")
            return False

        print(f"SUCCESS ({elapsed:.1f}ms)")
        print("-" * 60)

        # Print the draw result
        for group_name in sorted(result.keys()):
            teams = result[group_name]
            print(f"Group {group_name}:")
            for t in teams:
                print(f"  Pot {t.pot}: {t.name} ({t.confederation})")

        return True

    except RuntimeError as e:
        elapsed = (time.time() - start) * 1000
        print(f"FAIL: {e} ({elapsed:.1f}ms)")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test draw_v2 performance")
    parser.add_argument(
        "-n", "--num-seeds", type=int, default=100, help="Number of seeds to test (default: 100)"
    )
    parser.add_argument(
        "-t", "--threads", type=int, default=8, help="Number of parallel threads (default: 8)"
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=None, help="Test a specific seed with verbose output"
    )
    parser.add_argument(
        "--no-lookahead", action="store_true", help="Disable all lookahead constraints"
    )
    parser.add_argument("--l1", action="store_true", help="Enable L1 UEFA minimum")
    parser.add_argument("--l2", action="store_true", help="Enable L2 Inter Path 1")
    parser.add_argument("--l3", action="store_true", help="Enable L3 Inter Path 2")
    parser.add_argument("--l4", action="store_true", help="Enable L4 non-UEFA diversity")
    parser.add_argument("--l6", action="store_true", help="Enable L6 pot4 CAF landing")
    parser.add_argument("--l7", action="store_true", help="Enable L7 UEFA slots")
    parser.add_argument("--l8", action="store_true", help="Enable L8 CONCACAF slots")
    parser.add_argument("--l9", action="store_true", help="Enable L9 CAF slots")
    parser.add_argument("--all", action="store_true", help="Enable all constraints (L1-L4, L6-L9)")
    # Options to disable specific constraints (used with --all)
    parser.add_argument("--no-l1", action="store_true", help="Disable L1 (with --all)")
    parser.add_argument("--no-l2", action="store_true", help="Disable L2 (with --all)")
    parser.add_argument("--no-l3", action="store_true", help="Disable L3 (with --all)")
    parser.add_argument("--no-l4", action="store_true", help="Disable L4 (with --all)")
    parser.add_argument("--no-l6", action="store_true", help="Disable L6 (with --all)")
    parser.add_argument("--no-l7", action="store_true", help="Disable L7 (with --all)")
    parser.add_argument("--no-l8", action="store_true", help="Disable L8 (with --all)")
    parser.add_argument("--no-l9", action="store_true", help="Disable L9 (with --all)")

    args = parser.parse_args()

    # Build lookahead config
    if args.no_lookahead:
        lookahead = LookaheadConfig()
    elif args.all or any([args.l1, args.l2, args.l3, args.l4, args.l6, args.l7, args.l8, args.l9]):
        lookahead = LookaheadConfig(
            l1_uefa_minimum=(args.l1 or args.all) and not args.no_l1,
            l2_inter_path_1=(args.l2 or args.all) and not args.no_l2,
            l3_inter_path_2=(args.l3 or args.all) and not args.no_l3,
            l4_non_uefa_diversity=(args.l4 or args.all) and not args.no_l4,
            l6_pot4_caf_landing=(args.l6 or args.all) and not args.no_l6,
            l7_uefa_slots=(args.l7 or args.all) and not args.no_l7,
            l8_concacaf_slots=(args.l8 or args.all) and not args.no_l8,
            l9_caf_slots=(args.l9 or args.all) and not args.no_l9,
        )
    else:
        # Default: all constraints enabled
        lookahead = None

    # Single seed mode
    if args.seed is not None:
        if lookahead is None:
            # Default: essential constraints only (L3, L6-L9)
            lookahead = LookaheadConfig(
                l1_uefa_minimum=False,  # Redundant
                l2_inter_path_1=False,  # Redundant
                l3_inter_path_2=True,
                l4_non_uefa_diversity=False,  # Redundant
                l6_pot4_caf_landing=True,
                l7_uefa_slots=True,
                l8_concacaf_slots=True,
                l9_caf_slots=True,
            )
        run_single_seed_verbose(args.seed, lookahead)
        return

    run_test(args.num_seeds, lookahead, args.threads)


if __name__ == "__main__":
    main()
