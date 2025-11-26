"""
Top 4 FIFA bracket separation constraint.

FIFA's official draw procedure requires the top 4 ranked teams to be separated
into different knockout bracket quadrants to ensure they cannot meet before
the semi-finals (if they all win their groups).
"""

from typing import Dict, List, Optional
from .parser import Team


# Quadrant definitions based on knockout bracket structure
QUADRANTS = {
    "blue": ["E", "I", "F"],
    "turquoise": ["H", "D", "G"],
    "green": ["C", "A", "L"],
    "red": ["J", "B", "K"],
}

# Bracket halves for top 2 separation
HALVES = {
    "half1": ["blue", "turquoise"],  # Blue + Turquoise meet in SF1
    "half2": ["green", "red"],  # Green + Red meet in SF2
}


def get_quadrant_for_group(group: str) -> str:
    """Return which quadrant a group belongs to."""
    for quadrant, groups in QUADRANTS.items():
        if group in groups:
            return quadrant
    raise ValueError(f"Unknown group: {group}")


def get_half_for_quadrant(quadrant: str) -> str:
    """Return which half a quadrant belongs to."""
    for half, quadrants in HALVES.items():
        if quadrant in quadrants:
            return half
    raise ValueError(f"Unknown quadrant: {quadrant}")


def identify_top4_teams(pot1_teams: List[Team]) -> List[Team]:
    """
    Identify the top 4 ranked teams from Pot 1.

    Returns list of 4 teams sorted by FIFA ranking (best to worst).
    """
    # Sort by FIFA ranking (ascending - lower number is better)
    sorted_teams = sorted(pot1_teams, key=lambda t: t.fifa_ranking)
    return sorted_teams[:4]


class Top4BracketTracker:
    """
    Tracks top 4 team placements and quadrant occupancy during Pot 1 draw.

    Implements Option B: Non-top-4 teams cannot fill a quadrant completely
    before a top-4 team has been placed in that quadrant.
    """

    def __init__(self, pot1_teams: List[Team]):
        """Initialize tracker with Pot 1 teams."""
        self.top4_teams = identify_top4_teams(pot1_teams)
        self.top4_names = {t.name for t in self.top4_teams}

        # Track which groups are occupied by which teams
        self.group_assignments: Dict[str, Optional[Team]] = {
            chr(ord("A") + i): None for i in range(12)
        }

        # Track quadrant state
        self.quadrant_has_top4: Dict[str, bool] = {q: False for q in QUADRANTS.keys()}

    def is_top4_team(self, team: Team) -> bool:
        """Check if team is one of the top 4."""
        return team.name in self.top4_names

    def get_placed_top4(self) -> Dict[str, str]:
        """
        Get mapping of placed top 4 teams to their quadrants.

        Returns: {team_name: quadrant}
        """
        result = {}
        for group, team in self.group_assignments.items():
            if team and self.is_top4_team(team):
                quadrant = get_quadrant_for_group(group)
                result[team.name] = quadrant
        return result

    def get_quadrant_occupancy(self, quadrant: str) -> int:
        """Return number of groups occupied in a quadrant (0-3)."""
        groups_in_quadrant = QUADRANTS[quadrant]
        return sum(1 for g in groups_in_quadrant if self.group_assignments[g] is not None)

    def can_place_team_in_group(self, team: Team, group: str) -> tuple[bool, Optional[str]]:
        """
        Check if team can be placed in group according to top 4 constraints.

        Returns: (can_place, reason)
            can_place: True if placement is allowed
            reason: If False, explanation why placement is blocked
        """
        # Group must be empty
        if self.group_assignments[group] is not None:
            return False, f"Group {group} already occupied"

        quadrant = get_quadrant_for_group(group)

        if self.is_top4_team(team):
            # Top 4 team placement rules
            return self._check_top4_placement(team, group, quadrant)
        else:
            # Non-top-4 team placement rules (reservation logic)
            return self._check_non_top4_placement(team, group, quadrant)

    def _check_top4_placement(
        self, team: Team, group: str, quadrant: str
    ) -> tuple[bool, Optional[str]]:
        """Check if a top 4 team can be placed in the given group."""
        placed_top4 = self.get_placed_top4()

        # Rule 1: Each top 4 team must be in a different quadrant
        if quadrant in placed_top4.values():
            return False, f"Quadrant {quadrant} already has a top-4 team"

        this_half = get_half_for_quadrant(quadrant)
        team_rank = team.fifa_ranking

        # Rule 2: Top 2 (Spain #1, Argentina #2) must be in opposite halves
        if team_rank <= 2:
            # This is Spain or Argentina
            other_top2_rank = 1 if team_rank == 2 else 2
            other_top2_name = next(
                (t.name for t in self.top4_teams if t.fifa_ranking == other_top2_rank), None
            )

            if other_top2_name and other_top2_name in placed_top4:
                other_quadrant = placed_top4[other_top2_name]
                other_half = get_half_for_quadrant(other_quadrant)

                if this_half == other_half:
                    return (
                        False,
                        f"Top 2 must be in opposite halves (other is in {other_quadrant})",
                    )

        # Rule 3: Seeds 3-4 (France #3, England #4) must be in opposite halves
        # This prevents deadlock scenarios where both are drawn early into same half
        if team_rank in [3, 4]:
            # This is France or England
            other_seed34_rank = 3 if team_rank == 4 else 4
            other_seed34_name = next(
                (t.name for t in self.top4_teams if t.fifa_ranking == other_seed34_rank), None
            )

            if other_seed34_name and other_seed34_name in placed_top4:
                other_quadrant = placed_top4[other_seed34_name]
                other_half = get_half_for_quadrant(other_quadrant)

                if this_half == other_half:
                    return (
                        False,
                        f"Seeds 3-4 must be in opposite halves (other is in {other_quadrant})",
                    )

        return True, None

    def _check_non_top4_placement(
        self, team: Team, group: str, quadrant: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a non-top-4 team can be placed in the given group.

        Implements reservation logic: A non-top-4 team cannot occupy the last
        available group in a quadrant unless that quadrant already has a top-4 team.
        """
        # Check if quadrant already has a top-4 team
        if self.quadrant_has_top4[quadrant]:
            # Quadrant is "unlocked" - any team can go here
            return True, None

        # Quadrant does not yet have a top-4 team
        # Check if this would be the last available group in the quadrant
        current_occupancy = self.get_quadrant_occupancy(quadrant)

        # Each quadrant has 3 groups. If 2 are already occupied and this would be the 3rd,
        # we must reserve it for a top-4 team
        if current_occupancy == 2:
            return (
                False,
                f"Cannot fill last group in quadrant {quadrant} - must reserve for top-4",
            )

        return True, None

    def place_team(self, team: Team, group: str) -> None:
        """
        Place a team in a group and update tracker state.

        Should only be called after can_place_team_in_group returns True.
        """
        if self.group_assignments[group] is not None:
            raise ValueError(f"Group {group} already occupied")

        self.group_assignments[group] = team
        quadrant = get_quadrant_for_group(group)

        if self.is_top4_team(team):
            self.quadrant_has_top4[quadrant] = True

    def get_available_groups_for_team(self, team: Team) -> List[str]:
        """
        Get list of groups where team can be placed according to constraints.

        Returns list of group labels (e.g., ['E', 'F', 'H']).
        """
        available = []
        for group in self.group_assignments.keys():
            can_place, _ = self.can_place_team_in_group(team, group)
            if can_place:
                available.append(group)
        return available

    def validate_final_placement(self) -> tuple[bool, List[str]]:
        """
        Validate that all top 4 teams are properly separated.

        Returns: (is_valid, list_of_errors)
        """
        errors = []
        placed_top4 = self.get_placed_top4()

        # Check all 4 are placed
        if len(placed_top4) != 4:
            errors.append(f"Expected 4 top-4 teams placed, found {len(placed_top4)}")
            return False, errors

        # Check all in different quadrants
        quadrants_used = set(placed_top4.values())
        if len(quadrants_used) != 4:
            errors.append(f"Top 4 teams not in different quadrants: {placed_top4}")

        # Check top 2 in opposite halves
        top2_names = [t.name for t in self.top4_teams[:2]]
        top2_quadrants = [placed_top4.get(name) for name in top2_names if name in placed_top4]

        if len(top2_quadrants) == 2:
            half1 = get_half_for_quadrant(top2_quadrants[0])
            half2 = get_half_for_quadrant(top2_quadrants[1])
            if half1 == half2:
                errors.append(
                    f"Top 2 teams in same half: {top2_names[0]}={top2_quadrants[0]}, "
                    f"{top2_names[1]}={top2_quadrants[1]}"
                )

        # Check seeds 3-4 in opposite halves
        seeds34_names = [t.name for t in self.top4_teams[2:4]]
        seeds34_quadrants = [placed_top4.get(name) for name in seeds34_names if name in placed_top4]

        if len(seeds34_quadrants) == 2:
            half1 = get_half_for_quadrant(seeds34_quadrants[0])
            half2 = get_half_for_quadrant(seeds34_quadrants[1])
            if half1 == half2:
                errors.append(
                    f"Seeds 3-4 teams in same half: {seeds34_names[0]}={seeds34_quadrants[0]}, "
                    f"{seeds34_names[1]}={seeds34_quadrants[1]}"
                )

        return len(errors) == 0, errors
