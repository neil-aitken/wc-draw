"""
FIFA's official group position assignments.

FIFA revealed that group positions don't directly correspond to pot numbers.
While each group still has exactly one team from each pot, the position mapping
varies by group. This affects venue assignments and travel patterns.

For example:
- Group A, Position 2 (A2) = Pot 3 team (not Pot 2)
- Group B, Position 2 (B2) = Pot 4 team (not Pot 2)

This is particularly relevant for match scheduling and venue assignments.
"""

from typing import Dict


# Mapping from (group, position) -> pot number
# Position 1 is always the Pot 1 team (or host for A, B, D)
# Positions 2-4 vary by group according to FIFA's published schedule
GROUP_POSITION_TO_POT: Dict[tuple[str, int], int] = {
    # Group A (Mexico host in position 1)
    ("A", 1): 1,  # Mexico (host)
    ("A", 2): 3,  # Pot 3 team
    ("A", 3): 2,  # Pot 2 team
    ("A", 4): 4,  # Pot 4 team
    # Group B (Canada host in position 1)
    ("B", 1): 1,  # Canada (host)
    ("B", 2): 4,  # Pot 4 team
    ("B", 3): 3,  # Pot 3 team
    ("B", 4): 2,  # Pot 2 team
    # Group C
    ("C", 1): 1,  # Pot 1 team
    ("C", 2): 2,  # Pot 2 team
    ("C", 3): 4,  # Pot 4 team
    ("C", 4): 3,  # Pot 3 team
    # Group D (USA host in position 1)
    ("D", 1): 1,  # United States (host)
    ("D", 2): 3,  # Pot 3 team
    ("D", 3): 2,  # Pot 2 team
    ("D", 4): 4,  # Pot 4 team
    # Group E
    ("E", 1): 1,  # Pot 1 team
    ("E", 2): 4,  # Pot 4 team
    ("E", 3): 3,  # Pot 3 team
    ("E", 4): 2,  # Pot 2 team
    # Group F
    ("F", 1): 1,  # Pot 1 team
    ("F", 2): 2,  # Pot 2 team
    ("F", 3): 4,  # Pot 4 team
    ("F", 4): 3,  # Pot 3 team
    # Group G
    ("G", 1): 1,  # Pot 1 team
    ("G", 2): 3,  # Pot 3 team
    ("G", 3): 2,  # Pot 2 team
    ("G", 4): 4,  # Pot 4 team
    # Group H
    ("H", 1): 1,  # Pot 1 team
    ("H", 2): 4,  # Pot 4 team
    ("H", 3): 3,  # Pot 3 team
    ("H", 4): 2,  # Pot 2 team
    # Group I
    ("I", 1): 1,  # Pot 1 team
    ("I", 2): 2,  # Pot 2 team
    ("I", 3): 4,  # Pot 4 team
    ("I", 4): 3,  # Pot 3 team
    # Group J
    ("J", 1): 1,  # Pot 1 team
    ("J", 2): 3,  # Pot 3 team
    ("J", 3): 2,  # Pot 2 team
    ("J", 4): 4,  # Pot 4 team
    # Group K
    ("K", 1): 1,  # Pot 1 team
    ("K", 2): 4,  # Pot 4 team
    ("K", 3): 3,  # Pot 3 team
    ("K", 4): 2,  # Pot 2 team
    # Group L
    ("L", 1): 1,  # Pot 1 team
    ("L", 2): 2,  # Pot 2 team
    ("L", 3): 4,  # Pot 4 team
    ("L", 4): 3,  # Pot 3 team
}


# Reverse mapping: (group, pot) -> position
# This is what we need when placing teams from a specific pot into groups
POT_TO_GROUP_POSITION: Dict[tuple[str, int], int] = {
    (grp, pot): pos for (grp, pos), pot in GROUP_POSITION_TO_POT.items()
}


def get_position_for_pot(group: str, pot: int) -> int:
    """
    Get the position number (1-4) for a team from a given pot in a group.

    Args:
        group: Group letter (A-L)
        pot: Pot number (1-4)

    Returns:
        Position number (1-4)

    Example:
        >>> get_position_for_pot("A", 3)
        2  # Pot 3 team goes into position A2
    """
    key = (group, pot)
    if key not in POT_TO_GROUP_POSITION:
        raise ValueError(f"Invalid group/pot combination: {group}/{pot}")
    return POT_TO_GROUP_POSITION[key]


def get_pot_for_position(group: str, position: int) -> int:
    """
    Get the pot number (1-4) that should occupy a given position in a group.

    Args:
        group: Group letter (A-L)
        position: Position number (1-4)

    Returns:
        Pot number (1-4)

    Example:
        >>> get_pot_for_position("A", 2)
        3  # Position A2 is occupied by the Pot 3 team
    """
    key = (group, position)
    if key not in GROUP_POSITION_TO_POT:
        raise ValueError(f"Invalid group/position combination: {group}/{position}")
    return GROUP_POSITION_TO_POT[key]


def get_position_order_for_group(group: str) -> list[int]:
    """
    Get the pot order for positions 1-4 in a group.

    Args:
        group: Group letter (A-L)

    Returns:
        List of 4 pot numbers in position order

    Example:
        >>> get_position_order_for_group("A")
        [1, 3, 2, 4]  # Position 1=Pot1, Position 2=Pot3, Position 3=Pot2, Position 4=Pot4
    """
    return [get_pot_for_position(group, pos) for pos in [1, 2, 3, 4]]
