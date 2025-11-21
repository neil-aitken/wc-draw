import argparse
import json
from pathlib import Path
from typing import Iterable

from .parser import parse_teams_config, parse_slots_config


def format_pots(pots: dict) -> str:
    lines = []
    for pot in sorted(pots.keys()):
        teams = pots[pot]
        names = [t.name for t in teams]
        lines.append(f"Pot {pot} ({len(names)}): {', '.join(names)}")
    return "\n".join(lines)


def format_slots(slots: Iterable) -> str:
    lines = []
    for s in slots:
        parts = [f"{s.name} (pot {s.pot})"]
        if s.allowed_confederations:
            parts.append(f"allowed: {','.join(s.allowed_confederations)}")
        if s.candidates:
            parts.append(f"candidates: {', '.join(s.candidates)}")
        if s.fixed_group:
            parts.append(f"fixed_group: {s.fixed_group}")
        lines.append(" - " + " | ".join(parts))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="World Cup draw helper CLI")
    parser.add_argument("--teams", type=Path, default=None, help="Path to teams CSV file")
    parser.add_argument("--slots", action="store_true", help="Show placeholder slots")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args(argv)

    teams_file = args.teams
    if teams_file is None:
        teams_file = Path(__file__).resolve().parents[1] / "teams.csv"

    pots = parse_teams_config(str(teams_file))
    slots = parse_slots_config(str(teams_file))

    if args.json:
        out = {
            "pots": {str(k): [t.name for t in v] for k, v in pots.items()},
            "slots": [
                {
                    "name": s.name,
                    "pot": s.pot,
                    "allowed_confederations": s.allowed_confederations,
                    "candidates": s.candidates,
                    "fixed_group": s.fixed_group,
                }
                for s in slots
            ],
        }
        print(json.dumps(out, indent=2))
        return

    print(format_pots(pots))
    if args.slots:
        print("\nSlots:")
        print(format_slots(slots))


if __name__ == "__main__":
    main()
