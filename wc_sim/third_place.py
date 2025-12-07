"""
Third-place team ranking and R32 assignment.

FIFA ranks the 12 third-place teams and advances the best 8 to R32.
The assignment of which third-place team plays which group winner/runner-up
is determined by which combination of groups produce advancing thirds.
"""

import random
from typing import Dict, List, Set, Tuple

from .group_stage import TeamStanding
from .match_engine import get_simulator


# FIFA Third Place to R32 Slot Mapping
# Based on which 8 groups produce qualifying third-place teams,
# each third-place team is assigned to face a specific group winner or runner-up.
#
# The R32 matches that include third-place teams:
# Slots 81-88 (match numbers in the bracket)
#
# Since there are C(12,8) = 495 combinations, we use a programmatic approach
# that follows FIFA's principles:
# 1. Ensure geographic/confederation diversity where possible
# 2. Best third-place teams get "easier" opponents (lower-seeded group winners)
# 3. Consistent slot assignment based on group letter patterns

# Pre-defined slot assignments for common combinations
# Key: Tuple of sorted group letters (8 qualifying groups)
# Value: List of (third_place_group, r32_match_number, opponent_type)

# Rather than enumerate all 495, we implement the FIFA algorithm:
# After ranking, each third goes to a predetermined slot based on their source group

# The 8 R32 slots for third-place teams and their opponents:
# Match 81: 1I vs 3rd
# Match 82: 1J vs 3rd
# Match 83: 1K vs 3rd
# Match 84: 1L vs 3rd
# Match 85: 2I vs 3rd
# Match 86: 2J vs 3rd
# Match 87: 2K vs 3rd
# Match 88: 2L vs 3rd

# Simplified mapping: Based on which groups qualify, assign thirds to matches
# The exact assignment follows FIFA's published tables

# For simulation purposes, we use a consistent algorithm:
# 1. Rank all 12 third-place teams
# 2. Top 8 advance
# 3. Assign to slots based on their ranking and source group


def rank_third_place_teams(third_place: Dict[str, TeamStanding]) -> List[Tuple[str, TeamStanding]]:
    """
    Rank all 12 third-place teams using FIFA criteria.

    Returns list of (group_letter, standing) tuples, ranked best to worst.
    """
    sim = get_simulator()

    def sort_key(item):
        group, standing = item
        # Use FIFA ranking as final tiebreaker
        fifa_rank = sim.get_fifa_rank(standing.team)
        # Random for fair play points tiebreaker
        fair_play_random = random.random()

        return (
            -standing.points,
            -standing.goal_difference,
            -standing.goals_for,
            fair_play_random,  # Random tiebreaker (fair play simulation)
            fifa_rank,  # FIFA ranking
            group,  # Alphabetical by group as absolute last resort
        )

    items = list(third_place.items())
    return sorted(items, key=sort_key)


def get_advancing_thirds(ranked_thirds: List[Tuple[str, TeamStanding]]) -> List[Tuple[str, TeamStanding]]:
    """Get the 8 advancing third-place teams."""
    return ranked_thirds[:8]


def get_eliminated_thirds(ranked_thirds: List[Tuple[str, TeamStanding]]) -> List[Tuple[str, TeamStanding]]:
    """Get the 4 eliminated third-place teams."""
    return ranked_thirds[8:]


# Slot assignment lookup table
# Based on which 8 groups qualify, determines slot assignment
# This is simplified from FIFA's full 495-combination table

def assign_third_place_slots(qualifying_groups: List[str]) -> Dict[str, int]:
    """
    Assign third-place teams to R32 match slots.

    FIFA's assignment ensures:
    - No third can face a team from their own group
    - Best thirds get slightly easier draws
    - Consistent pairing based on qualifying combination

    Args:
        qualifying_groups: List of 8 group letters that have qualifying thirds

    Returns:
        Dict mapping group letter to R32 match number (81-88)
    """
    # Sort groups for consistent lookup
    quals = sorted(qualifying_groups)

    # Match slots and their opponents:
    # 81: vs 1I (Group I winner)
    # 82: vs 1J (Group J winner)
    # 83: vs 1K (Group K winner)
    # 84: vs 1L (Group L winner)
    # 85: vs 2I (Group I runner-up)
    # 86: vs 2J (Group J runner-up)
    # 87: vs 2K (Group K runner-up)
    # 88: vs 2L (Group L runner-up)

    # Eligibility rules (third from group X cannot face teams from group X):
    # - Thirds from I cannot go to slots 81 or 85
    # - Thirds from J cannot go to slots 82 or 86
    # - Thirds from K cannot go to slots 83 or 87
    # - Thirds from L cannot go to slots 84 or 88

    # Build assignment using backtracking algorithm respecting constraints
    slots = [81, 82, 83, 84, 85, 86, 87, 88]
    assignment = {}

    # Forbidden slots for each group (third cannot face teams from their own group)
    # Match 81: vs 1I, Match 82: vs 1J, Match 83: vs 1K, Match 84: vs 1L
    # Match 85: vs 2I, Match 86: vs 2J, Match 87: vs 2K, Match 88: vs 2L
    forbidden = {
        'A': set(),
        'B': set(),
        'C': set(),
        'D': set(),
        'E': set(),
        'F': set(),
        'G': set(),
        'H': set(),
        'I': {81, 85},  # Can't face 1I or 2I
        'J': {82, 86},  # Can't face 1J or 2J
        'K': {83, 87},  # Can't face 1K or 2K
        'L': {84, 88},  # Can't face 1L or 2L
    }

    # Use backtracking to find valid assignment
    def backtrack(remaining_groups: List[str], remaining_slots: Set[int]) -> bool:
        if not remaining_groups:
            return True

        group = remaining_groups[0]
        rest = remaining_groups[1:]

        # Try each available slot
        for slot in sorted(remaining_slots):
            if slot not in forbidden[group]:
                assignment[group] = slot
                new_remaining = remaining_slots - {slot}
                if backtrack(rest, new_remaining):
                    return True
                del assignment[group]

        return False

    # Sort qualifying groups to process most constrained first
    # (Groups I, J, K, L have restrictions)
    constrained = [g for g in quals if g in 'IJKL']
    unconstrained = [g for g in quals if g not in 'IJKL']

    # Process constrained groups first for better backtracking
    ordered_groups = constrained + unconstrained

    if not backtrack(ordered_groups, set(slots)):
        raise ValueError(f"Could not find valid slot assignment for groups: {quals}")

    return assignment


def get_r32_third_place_matchups(
    advancing: List[Tuple[str, TeamStanding]],
    winners: Dict[str, str],
    runners_up: Dict[str, str]
) -> Dict[int, Tuple[str, str]]:
    """
    Get R32 matchups involving third-place teams.

    Args:
        advancing: List of (group_letter, standing) for advancing thirds
        winners: Dict of group_letter -> winner team name
        runners_up: Dict of group_letter -> runner-up team name

    Returns:
        Dict mapping match number (81-88) to (opponent, third_place_team)
    """
    qualifying_groups = [group for group, _ in advancing]
    slot_assignment = assign_third_place_slots(qualifying_groups)

    # Match opponents
    slot_opponents = {
        81: ('1I', winners.get('I')),
        82: ('1J', winners.get('J')),
        83: ('1K', winners.get('K')),
        84: ('1L', winners.get('L')),
        85: ('2I', runners_up.get('I')),
        86: ('2J', runners_up.get('J')),
        87: ('2K', runners_up.get('K')),
        88: ('2L', runners_up.get('L')),
    }

    matchups = {}
    for group, standing in advancing:
        slot = slot_assignment[group]
        _, opponent = slot_opponents[slot]
        matchups[slot] = (opponent, standing.team)

    return matchups


if __name__ == "__main__":
    # Test third-place ranking
    from .playoffs import get_playoff_qualified_groups
    from .group_stage import simulate_all_groups, get_advancing_teams

    print("Simulating groups...")
    groups = get_playoff_qualified_groups()
    results = simulate_all_groups(groups)
    advancing = get_advancing_teams(results)

    print("\nRanking third-place teams...")
    ranked = rank_third_place_teams(advancing['third_place'])

    print("\nAll third-place teams (ranked):")
    for i, (group, standing) in enumerate(ranked, 1):
        status = "ADVANCE" if i <= 8 else "ELIMINATED"
        print(f"  {i:2}. Group {group}: {standing} [{status}]")

    advancing_thirds = get_advancing_thirds(ranked)
    qualifying_groups = [g for g, _ in advancing_thirds]

    print(f"\nQualifying groups: {', '.join(qualifying_groups)}")

    print("\nSlot assignments:")
    slots = assign_third_place_slots(qualifying_groups)
    for group in sorted(slots.keys()):
        slot = slots[group]
        opponent_type = "1" if slot <= 84 else "2"
        opponent_group = chr(ord('I') + (slot - 81) % 4)
        print(f"  Group {group} 3rd -> Match {slot} vs {opponent_type}{opponent_group}")

    print("\nR32 Matchups with third-place teams:")
    matchups = get_r32_third_place_matchups(
        advancing_thirds,
        advancing['winners'],
        advancing['runners_up']
    )
    for match_num in sorted(matchups.keys()):
        opponent, third = matchups[match_num]
        print(f"  Match {match_num}: {opponent} vs {third}")
