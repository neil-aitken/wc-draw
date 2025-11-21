from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Slot:
    """Represents a draw slot that may be filled by an undecided qualifier.

    - `name`: human-readable identifier (e.g. "UEFA Playoff A").
    - `pot`: pot number the slot belongs to.
    - `allowed_confederations`: list of allowed source confederations (e.g. ["UEFA"]).
    - `candidates`: optional list of possible team names that could occupy the slot.
    - `fixed_group`: if the slot/host is pre-assigned to a group (e.g. hosts), otherwise None.
    """

    name: str
    pot: int
    allowed_confederations: List[str]
    candidates: Optional[List[str]] = None
    fixed_group: Optional[str] = None
    # concatenated flag emoji(s) for slot (e.g. combined flags for playoff candidates)
    flags: Optional[str] = None
