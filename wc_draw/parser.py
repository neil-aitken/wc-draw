import csv

from dataclasses import dataclass
from typing import Optional, List
from wc_draw.slot import Slot


@dataclass
class Team:
    name: str
    confederation: str
    pot: int
    host: bool
    fixed_group: Optional[str] = None


def parse_teams_config(filepath: str) -> dict:
    pots = {}
    with open(filepath, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue  # Skip comments and empty lines
            # Support rows with 4+ columns; extra columns are ignored here
            if len(row) >= 5:
                name, confederation, pot, host, fixed_group = row[:5]
            elif len(row) == 4:
                name, confederation, pot, host = row
                fixed_group = None
            else:
                raise ValueError(f"Invalid row format: {row}")
            team = Team(
                name=name.strip(),
                confederation=confederation.strip(),
                pot=int(pot),
                host=host.strip().lower() == "true",
                fixed_group=fixed_group.strip() if fixed_group and fixed_group.strip() else None,
            )
            pots.setdefault(team.pot, []).append(team)
    return pots


def parse_slots_config(filepath: str) -> List[Slot]:
    """Parse CSV and return a list of Slot objects for placeholder entries.

    Current heuristic: any row whose name contains "Playoff" is treated as a slot.
    The slot's allowed_confederations is populated from the confederation column.
    """
    slots: List[Slot] = []
    with open(filepath, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            # Support both 4- and 5-column rows
            if len(row) >= 4:
                name = row[0].strip()
                confederation = row[1].strip()
                pot = int(row[2])
                # If the name indicates a playoff / placeholder, create a Slot
                if "playoff" in name.lower() or "path" in name.lower():
                    # parse candidates column (semicolon-separated) if present
                    candidates = None
                    if len(row) >= 6 and row[5].strip():
                        candidates = [c.strip() for c in row[5].split(";") if c.strip()]
                    # allow multiple confederations separated by '|', e.g. 'CAF|OFC|CONCACAF'
                    if confederation:
                        allowed_confeds = [c.strip() for c in confederation.split("|") if c.strip()]
                    else:
                        allowed_confeds = []
                    slot = Slot(
                        name=name,
                        pot=pot,
                        allowed_confederations=allowed_confeds,
                        candidates=candidates,
                        fixed_group=(row[4].strip() if len(row) >= 5 and row[4].strip() else None),
                    )
                    slots.append(slot)
    return slots
