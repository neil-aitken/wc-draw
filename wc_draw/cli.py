import argparse
import json
from pathlib import Path
from typing import Iterable

from .parser import parse_teams_config, parse_slots_config
from .draw import draw_pot1, draw_pot, run_full_draw
import random


def format_pots(pots: dict, slots_map: dict | None = None) -> str:
    lines = []
    for pot in sorted(pots.keys()):
        teams = pots[pot]
        flags = []
        for t in teams:
            raw = getattr(t, "flag", None) or t.name
            slot = slots_map.get(t.name) if slots_map else None
            if slot and getattr(slot, "flags", None):
                parts = [p.strip() for p in slot.flags.split("/")]
                out_parts = []
                for part in parts:
                    # Always emit the flag part; don't append candidate labels
                    out_parts.append(part)
                flagstr = "/".join(out_parts)
            else:
                # ensure there are no spaces around '/' in printed output
                flagstr = raw.replace(" / ", "/")
            flags.append(flagstr)
        lines.append(f"Pot {pot}: {', '.join(flags)}")
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
        if getattr(s, "flags", None):
            # show slashes without surrounding spaces (compact)
            parts.append(f"flags: {s.flags.replace(' / ', '/')}")
        lines.append(" - " + " | ".join(parts))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="World Cup draw helper CLI")
    parser.add_argument("--teams", type=Path, default=None, help="Path to teams CSV file")
    parser.add_argument("--slots", action="store_true", help="Show placeholder slots")
    parser.add_argument(
        "--draw",
        "--draw-all",
        action="store_true",
        dest="draw",
        help="Run the full draw for pots 1 through 4 (classic ordering: pot1, pot2, pot3, pot4)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for deterministic draws",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args(argv)

    teams_file = args.teams
    if teams_file is None:
        teams_file = Path(__file__).resolve().parents[1] / "teams.csv"

    pots = parse_teams_config(str(teams_file))
    slots = parse_slots_config(str(teams_file))
    # map slots by name for formatting helpers
    slots_map = {s.name: s for s in slots}

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

    # text output
    print(format_pots(pots, slots_map))

    if args.draw:
        # Delegate draw orchestration (seed creation + pot order) to draw module.
        groups, used_seed = run_full_draw(pots, seed=args.seed)
        print(f"Seed: {used_seed}")

        def fmt_team(t):
            raw = getattr(t, "flag", None) or t.name
            slot = slots_map.get(t.name)
            if slot and getattr(slot, "flags", None):
                parts = [p.strip() for p in slot.flags.split("/")]
                out_parts = []
                for part in parts:
                    out_parts.append(part)
                return "/".join(out_parts)
            return raw.replace("/", " / ")

        print("\nDraw:")
        for g in sorted(groups.keys()):
            team_flags = [fmt_team(t) for t in groups[g]]
            line = f"{g}: " + ", ".join(team_flags)
            print(line)

    if args.slots:
        print("\nSlots:")
        print(format_slots(slots))


if __name__ == "__main__":
    main()
