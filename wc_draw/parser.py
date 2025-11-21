import csv

from dataclasses import dataclass
from typing import Optional, List
from wc_draw.slot import Slot
import re


def _unescape_unicode_escapes(s: str) -> str:
    r"""Replace explicit \uXXXX and \UXXXXXXXX escapes in a string with
    their actual Unicode characters, without touching already-decoded
    characters. This avoids double-decoding mojibake when the input mixes
    literal emoji and backslash-escapes.

    Examples:
      '\\U0001F3F4' -> '🏴'
      '\\u00AE' -> '®'
    """
    if not s or ("\\u" not in s and "\\U" not in s):
        return s

    def _repl(m) -> str:
        tok = m.group(0)
        code = int(tok[2:], 16)
        try:
            return chr(code)
        except Exception:
            return tok

    return re.sub(r"\\U[0-9a-fA-F]{8}|\\u[0-9a-fA-F]{4}", _repl, s)


@dataclass
class Team:
    name: str
    confederation: str
    pot: int
    host: bool
    fixed_group: Optional[str] = None
    flag: Optional[str] = None
    fifa_ranking: int = 0  # FIFA world ranking (0 = unranked/unknown)
    uefa_group_winner: bool = False  # Won a UEFA qualifying group


def parse_teams_config(filepath: str) -> dict[int, List[Team]]:
    pots: dict[int, List[Team]] = {}
    with open(filepath, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue  # Skip comments and empty lines

            # CSV schema: name, confederation, pot, host, fixed_group, flag,
            #             candidates, fifa_ranking, uefa_group_winner
            # Note: candidates column is for slots (placeholder teams)
            # Support backward compatibility with older formats
            if len(row) >= 9:
                (
                    name,
                    confederation,
                    pot,
                    host,
                    fixed_group,
                    flag,
                    _candidates,
                    fifa_ranking,
                    uefa_group_winner,
                ) = row[:9]
            elif len(row) >= 8:
                (
                    name,
                    confederation,
                    pot,
                    host,
                    fixed_group,
                    flag,
                    _candidates,
                    fifa_ranking,
                ) = row[:8]
                uefa_group_winner = "false"
            elif len(row) >= 6:
                name, confederation, pot, host, fixed_group, flag = row[:6]
                fifa_ranking = "0"
                uefa_group_winner = "false"
            elif len(row) == 5:
                name, confederation, pot, host, fixed_group = row
                flag = None
                fifa_ranking = "0"
                uefa_group_winner = "false"
            elif len(row) == 4:
                name, confederation, pot, host = row
                fixed_group = None
                flag = None
                fifa_ranking = "0"
                uefa_group_winner = "false"
            else:
                raise ValueError(f"Invalid row format: {row}")

            team = Team(
                name=name.strip(),
                confederation=confederation.strip(),
                pot=int(pot),
                host=host.strip().lower() == "true",
                fixed_group=fixed_group.strip() if fixed_group and fixed_group.strip() else None,
                flag=flag.strip() if flag and flag.strip() else None,
                fifa_ranking=(
                    int(fifa_ranking.strip()) if fifa_ranking and fifa_ranking.strip() else 0
                ),
                uefa_group_winner=(
                    uefa_group_winner.strip().lower() == "true" if uefa_group_winner else False
                ),
            )
            # If the CSV stores explicit unicode escape sequences (e.g. "\U0001F3F4..."),
            # replace those escapes only (leave literal emoji alone) to avoid
            # double-decoding issues that cause mojibake.
            if team.flag and ("\\u" in team.flag or "\\U" in team.flag):
                team.flag = _unescape_unicode_escapes(team.flag)

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
                    # parse flags/candidates flexibly: older files put candidates at
                    # index 5; newer schema adds a flag column at index 5 and
                    # candidates at index 6. Detect which is present.
                    flags = None
                    candidates = None
                    if len(row) >= 6 and row[5].strip():
                        if ";" in row[5]:
                            # old-style: candidates in column 5
                            candidates = [c.strip() for c in row[5].split(";") if c.strip()]
                        else:
                            # new-style: flags in column 5
                            flags = row[5].strip()
                    if len(row) >= 7 and row[6].strip():
                        candidates = [c.strip() for c in row[6].split(";") if c.strip()]
                    # allow multiple confederations separated by '|', e.g. 'CAF|OFC|CONCACAF'
                    if confederation:
                        allowed_confeds = [c.strip() for c in confederation.split("|") if c.strip()]
                    else:
                        allowed_confeds = []
                    # If flags contains explicit escape sequences, replace them
                    # safely without touching existing emoji characters.
                    if flags and ("\\u" in flags or "\\U" in flags):
                        flags = _unescape_unicode_escapes(flags)

                    # Normalize: ensure subdivision tag sequences (which end with
                    # U+E007F) are separated from adjacent emoji by a '/'
                    # so terminals don't combine sequences unexpectedly.
                    if flags and "\ue007F" in flags:
                        import re

                        # ensure there's a '/' after the CANCEL TAG if not present
                        flags = re.sub(r"\uE007F(?!/)", "\ue007F/", flags)
                        # ensure there's a '/' before a BLACK FLAG tag sequence if not present
                        flags = re.sub(r"(?<!/)(\U0001F3F4)", r"/\1", flags)

                    slot = Slot(
                        name=name,
                        pot=pot,
                        allowed_confederations=allowed_confeds,
                        candidates=candidates,
                        fixed_group=(row[4].strip() if len(row) >= 5 and row[4].strip() else None),
                        flags=flags,
                    )
                    slots.append(slot)
    return slots
