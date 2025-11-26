#!/usr/bin/env python3
"""
Validate a specific seed from the FIFA official draw simulation.

Usage:
    python validate_seed.py <seed_number> [jsonl_file]
    python validate_seed.py 2004
    python validate_seed.py 2004 seed_scan_fifa_official.jsonl
"""

import argparse
import json
import sys
from typing import Dict, List, Tuple


def load_confederations(csv_path: str = "teams.csv") -> Dict[str, str]:
    """Load team confederations from CSV file."""
    confeds = {}
    with open(csv_path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split(",")
            if len(parts) >= 3:
                name = parts[0].strip()
                confed = parts[1].strip()
                confeds[name] = confed
    return confeds


def find_seed_in_jsonl(seed: int, jsonl_path: str) -> Dict:
    """Find and return the draw result for a specific seed."""
    with open(jsonl_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("seed") == seed:
                return data
    return None


def validate_draw(groups: Dict[str, List[str]], confeds: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validate FIFA draw constraints for a set of groups.

    Returns:
        Tuple of (is_valid, list_of_violations)
    """
    violations = []

    for group_name in sorted(groups.keys()):
        teams = groups[group_name]

        # Count confederations in this group
        confed_counts = {}
        for team in teams:
            confed = confeds.get(team, "UNKNOWN")

            # Handle multi-confederation placeholders (e.g., "AFC|CONMEBOL|CONCACAF")
            if "|" in confed:
                # For validation, we treat it as the first possible confederation
                base_confed = confed.split("|")[0].strip()
                confed_counts[base_confed] = confed_counts.get(base_confed, 0) + 1
            else:
                confed_counts[confed] = confed_counts.get(confed, 0) + 1

        # Check UEFA constraints (min 1, max 2 per group)
        uefa_count = confed_counts.get("UEFA", 0)
        if uefa_count == 0:
            violations.append(f"Group {group_name}: {uefa_count} UEFA teams (min 1 required)")
        if uefa_count > 2:
            violations.append(f"Group {group_name}: {uefa_count} UEFA teams (max 2 allowed)")

        # Check other confederations max 1 per group
        for confed, count in confed_counts.items():
            if confed != "UEFA" and count > 1:
                violations.append(f"Group {group_name}: {count} {confed} teams (max 1 allowed)")

    return len(violations) == 0, violations


def display_draw(groups: Dict[str, List[str]], confeds: Dict[str, str], verbose: bool = False):
    """Display the draw groups with confederations."""
    print("\nDraw Groups:")
    print("=" * 70)

    for group_name in sorted(groups.keys()):
        teams = groups[group_name]
        print(f"\nGroup {group_name}:")

        if verbose:
            # Show each team with confederation
            for i, team in enumerate(teams, 1):
                confed = confeds.get(team, "UNKNOWN")
                print(f"  {i}. {team:30} [{confed}]")

            # Count confederations
            confed_counts = {}
            for team in teams:
                confed = confeds.get(team, "UNKNOWN")
                if "|" in confed:
                    base_confed = confed.split("|")[0].strip()
                    confed_counts[base_confed] = confed_counts.get(base_confed, 0) + 1
                else:
                    confed_counts[confed] = confed_counts.get(confed, 0) + 1

            uefa_count = confed_counts.get("UEFA", 0)
            print(f"  → UEFA teams: {uefa_count}/2")
        else:
            # Compact display
            print(f"  {', '.join(teams)}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate a specific seed from FIFA official draw simulation"
    )
    parser.add_argument("seed", type=int, help="Seed number to validate")
    parser.add_argument(
        "jsonl_file",
        nargs="?",
        default="seed_scan_fifa_official.jsonl",
        help="Path to JSONL file (default: seed_scan_fifa_official.jsonl)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed group information"
    )
    parser.add_argument(
        "--csv",
        default="teams.csv",
        help="Path to teams CSV file (default: teams.csv)",
    )
    args = parser.parse_args()

    print(f"Validating Seed {args.seed}")
    print("=" * 70)

    # Load confederations
    try:
        confeds = load_confederations(args.csv)
        print(f"✓ Loaded {len(confeds)} teams from {args.csv}")
    except FileNotFoundError:
        print(f"✗ Error: Could not find {args.csv}")
        sys.exit(1)

    # Find seed in JSONL
    try:
        result = find_seed_in_jsonl(args.seed, args.jsonl_file)
        if result is None:
            print(f"✗ Error: Seed {args.seed} not found in {args.jsonl_file}")
            sys.exit(1)
        print(f"✓ Found seed {args.seed} in {args.jsonl_file}")
    except FileNotFoundError:
        print(f"✗ Error: Could not find {args.jsonl_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON in {args.jsonl_file}: {e}")
        sys.exit(1)

    # Check if draw was successful
    if not result.get("success", False):
        print(f"\n⚠️  Warning: Seed {args.seed} was marked as unsuccessful")
        if result.get("error"):
            print(f"   Error: {result['error']}")

    # Get groups
    groups = result.get("groups", {})
    if not groups:
        print("✗ Error: No groups found in result")
        sys.exit(1)

    print(f"✓ Draw contains {len(groups)} groups")

    # Display fallback info if present
    if result.get("fallback"):
        fallback = result["fallback"]
        print(f"\n⚠️  Fallback used: {fallback.get('type', 'unknown')}")
        if "ordering" in fallback:
            print(f"   Ordering: {fallback['ordering']}")

    # Display the draw
    display_draw(groups, confeds, args.verbose)

    # Validate constraints
    print("\n" + "=" * 70)
    print("Constraint Validation:")
    print("=" * 70)

    is_valid, violations = validate_draw(groups, confeds)

    if is_valid:
        print("\n✅ ALL CONSTRAINTS SATISFIED!")
        print("\nChecked constraints:")
        print("  ✓ UEFA teams: min 1, max 2 per group")
        print("  ✓ Non-UEFA confederations: max 1 per group")
    else:
        print("\n❌ CONSTRAINT VIOLATIONS FOUND!\n")
        for violation in violations:
            print(f"  ✗ {violation}")
        print(f"\nTotal violations: {len(violations)}")
        sys.exit(1)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
