#!/usr/bin/env python3
"""
Fast draw analysis - run many draws without lookahead, validate after completion.
Save results for pattern analysis.
"""

import sys
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from wc_draw.parser import parse_teams_config
from wc_draw.pot_assignment import assign_pots
from wc_draw.config import DrawConfig
from wc_draw.draw_v2 import (
    run_draw,
    LookaheadConfig,
    validate_draw,
    _is_caf_team,
)


@dataclass
class DrawAnalysis:
    seed: int
    completed: bool
    valid: bool
    violations: List[str]
    time_ms: float
    pot2_caf_groups: List[str]
    pot2_uefa_groups: List[str]
    pot4_caf_groups: List[str]
    groups_without_uefa: List[str]


def run_single_analysis(seed: int, pots: dict) -> DrawAnalysis:
    """Run a single draw with no lookahead and analyze the result."""
    start = time.time()

    config = LookaheadConfig(
        l1_uefa_minimum=False,
        l2_inter_path_1=False,
        l3_inter_path_2=False,
        l4_non_uefa_diversity=False,
        l5_bipartite_matching=False,
        l6_pot4_caf_landing=False,
    )

    try:
        result = run_draw(pots, seed=seed, lookahead=config)
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return DrawAnalysis(
            seed=seed,
            completed=False,
            valid=False,
            violations=[str(e)],
            time_ms=elapsed,
            pot2_caf_groups=[],
            pot2_uefa_groups=[],
            pot4_caf_groups=[],
            groups_without_uefa=[],
        )

    elapsed = (time.time() - start) * 1000

    if result is None:
        return DrawAnalysis(
            seed=seed,
            completed=False,
            valid=False,
            violations=["Draw failed to complete"],
            time_ms=elapsed,
            pot2_caf_groups=[],
            pot2_uefa_groups=[],
            pot4_caf_groups=[],
            groups_without_uefa=[],
        )

    groups, _ = result

    # Validate the draw
    violations = validate_draw(groups)

    # Analyze placements
    pot2_caf_groups = []
    pot2_uefa_groups = []
    pot4_caf_groups = []
    groups_without_uefa = []

    for group_name, teams in groups.items():
        has_uefa = any("UEFA" in t.confederation for t in teams)
        if not has_uefa:
            groups_without_uefa.append(group_name)

        for t in teams:
            if t.pot == 2:
                if _is_caf_team(t):
                    pot2_caf_groups.append(group_name)
                elif "UEFA" in t.confederation:
                    pot2_uefa_groups.append(group_name)
            elif t.pot == 4 and _is_caf_team(t):
                pot4_caf_groups.append(group_name)

    return DrawAnalysis(
        seed=seed,
        completed=True,
        valid=len(violations) == 0,
        violations=violations,
        time_ms=elapsed,
        pot2_caf_groups=sorted(pot2_caf_groups),
        pot2_uefa_groups=sorted(pot2_uefa_groups),
        pot4_caf_groups=sorted(pot4_caf_groups),
        groups_without_uefa=sorted(groups_without_uefa),
    )


def worker(args: Tuple[int, dict]) -> DrawAnalysis:
    """Worker function for parallel execution."""
    seed, pots = args
    return run_single_analysis(seed, pots)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze draws without lookahead")
    parser.add_argument("-n", "--num-seeds", type=int, default=1000, help="Number of seeds to test")
    parser.add_argument("-t", "--threads", type=int, default=8, help="Number of parallel threads")
    parser.add_argument(
        "-o", "--output", type=str, default="draw_analysis.json", help="Output file"
    )
    args = parser.parse_args()

    # Load teams
    teams_by_pot = parse_teams_config("teams.csv")
    config = DrawConfig()
    pots = assign_pots(teams_by_pot, config)

    print(f"Running {args.num_seeds} draws with {args.threads} threads (no lookahead)")
    print("-" * 60)

    start_time = time.time()
    results: List[DrawAnalysis] = []

    with ProcessPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(worker, (seed, pots)): seed for seed in range(args.num_seeds)}

        completed_count = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed_count += 1

            if completed_count % 100 == 0:
                print(f"  Progress: {completed_count}/{args.num_seeds}")

    results.sort(key=lambda x: x.seed)

    elapsed = time.time() - start_time

    # Summarize
    completed = sum(1 for r in results if r.completed)
    valid = sum(1 for r in results if r.valid)

    print("-" * 60)
    print(f"Completed: {completed}/{args.num_seeds} ({100 * completed / args.num_seeds:.1f}%)")
    print(f"Valid: {valid}/{args.num_seeds} ({100 * valid / args.num_seeds:.1f}%)")
    print(f"Total time: {elapsed:.1f}s")
    print(f"Avg time per draw: {1000 * elapsed / args.num_seeds:.1f}ms")

    # Analyze failures
    incomplete = [r for r in results if not r.completed]
    invalid = [r for r in results if r.completed and not r.valid]

    if incomplete:
        print(f"\nIncomplete draws ({len(incomplete)}):")
        print(f"  First 10 seeds: {[r.seed for r in incomplete[:10]]}")

    if invalid:
        print(f"\nInvalid draws ({len(invalid)}):")

        violation_counts: Dict[str, int] = {}
        for r in invalid:
            for v in r.violations:
                if "has no UEFA team" in v:
                    key = "Missing UEFA"
                elif "multiple" in v.lower():
                    key = "Duplicate confederation"
                else:
                    key = v[:50]
                violation_counts[key] = violation_counts.get(key, 0) + 1

        print("  Violation types:")
        for v, count in sorted(violation_counts.items(), key=lambda x: -x[1]):
            print(f"    {v}: {count}")

        print("\n  Pattern analysis (invalid draws):")

        no_uefa_counts: Dict[str, int] = {}
        for r in invalid:
            for g in r.groups_without_uefa:
                no_uefa_counts[g] = no_uefa_counts.get(g, 0) + 1
        if no_uefa_counts:
            print("    Groups most often without UEFA:")
            for g, count in sorted(no_uefa_counts.items(), key=lambda x: -x[1])[:5]:
                print(f"      {g}: {count} times")

        pot4_caf_in_no_uefa = 0
        for r in invalid:
            for g in r.pot4_caf_groups:
                if g in r.groups_without_uefa:
                    pot4_caf_in_no_uefa += 1
        if pot4_caf_in_no_uefa > 0:
            print(f"    pot 4 CAF in no-UEFA groups: {pot4_caf_in_no_uefa} times")

    # Save results
    output_data = {
        "summary": {
            "num_seeds": args.num_seeds,
            "completed": completed,
            "valid": valid,
            "elapsed_seconds": elapsed,
        },
        "results": [asdict(r) for r in results],
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to {args.output}")

    if invalid:
        print(f"\nFirst 10 invalid seeds: {[r.seed for r in invalid[:10]]}")


if __name__ == "__main__":
    main()
