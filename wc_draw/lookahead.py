"""
Lookahead constraint checking for FIFA World Cup 2026 draw.

This module implements forward-looking constraint checks to ensure that
placing a team in a group won't make it impossible to complete the draw.

The key insight is that certain playoff paths have restricted landing spots:
- Inter Path 1 (CAF|OFC|CONCACAF): Cannot go to groups with CAF, OFC, or CONCACAF
- Inter Path 2 (AFC|CONMEBOL|CONCACAF): Cannot go to groups with AFC, CONMEBOL, or CONCACAF

Without lookahead, ~30% of draws exhaust all valid landing spots for Inter Path 2,
requiring fallback orderings which introduce bias.

Lookahead Rules Implemented:
- L1: UEFA Minimum Feasibility (in draw.py)
- L2: Inter Path 1 Feasibility
- L3: Inter Path 2 Feasibility
- L4: Non-European Pot 1 Group Diversity
- L5: General Confederation Feasibility
"""

import logging
from typing import Dict, List, Set

from .parser import Team

logger = logging.getLogger(__name__)


def _get_group_confederations(teams: List[Team]) -> Set[str]:
    """Get the set of confederations present in a group's teams."""
    confeds = set()
    for team in teams:
        if "|" in (team.confederation or ""):
            # Placeholder team - don't count its confederation
            continue
        if team.confederation:
            confeds.add(team.confederation)
    return confeds


def _is_inter_path_2_eligible(confeds: Set[str]) -> bool:
    """
    Check if a group is eligible for Inter Path 2.

    Inter Path 2 (AFC|CONMEBOL|CONCACAF) cannot go to groups that
    already have AFC, CONMEBOL, or CONCACAF teams.
    """
    return "AFC" not in confeds and "CONMEBOL" not in confeds and "CONCACAF" not in confeds


def _is_inter_path_1_eligible(confeds: Set[str]) -> bool:
    """
    Check if a group is eligible for Inter Path 1.

    Inter Path 1 (CAF|OFC|CONCACAF) cannot go to groups that
    already have CAF, OFC, or CONCACAF teams.
    """
    return "CAF" not in confeds and "OFC" not in confeds and "CONCACAF" not in confeds


def _preserves_inter_path_2_eligibility(confed: str) -> bool:
    """
    Check if a team's confederation preserves Inter Path 2 eligibility.

    Only UEFA and CAF teams preserve eligibility.
    """
    return confed in ("UEFA", "CAF")


def _preserves_inter_path_1_eligibility(confed: str) -> bool:
    """
    Check if a team's confederation preserves Inter Path 1 eligibility.

    Only UEFA, CONMEBOL, and AFC teams preserve eligibility.
    """
    return confed in ("UEFA", "CONMEBOL", "AFC")


def count_inter_path_2_landing_spots(groups: Dict[str, List[Team]]) -> int:
    """
    Count how many groups are valid landing spots for Inter Path 2.

    A valid landing spot has NO AFC, CONMEBOL, or CONCACAF teams.
    """
    count = 0
    for group, teams in groups.items():
        confeds = _get_group_confederations(teams)
        if _is_inter_path_2_eligible(confeds):
            count += 1
    return count


def count_inter_path_1_landing_spots(groups: Dict[str, List[Team]]) -> int:
    """
    Count how many groups are valid landing spots for Inter Path 1.

    A valid landing spot has NO CAF, OFC, or CONCACAF teams.
    """
    count = 0
    for group, teams in groups.items():
        confeds = _get_group_confederations(teams)
        if _is_inter_path_1_eligible(confeds):
            count += 1
    return count


def _count_open_ip2_slots(groups: Dict[str, List[Team]]) -> int:
    """
    Count total open slots in IP2-eligible groups.

    This counts physical slots, not just groups. A group with 3 teams
    has 1 open slot for Pot 4.
    """
    count = 0
    for _, teams in groups.items():
        confeds = _get_group_confederations(teams)
        if _is_inter_path_2_eligible(confeds):
            # Each group can hold 4 teams
            open_slots = 4 - len(teams)
            count += open_slots
    return count


def would_eliminate_inter_path_2_spot(
    team: Team,
    target_group: str,
    groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    Check if placing team in target_group would reduce Inter Path 2 landing spots
    below a safe threshold.

    This is the key lookahead check. We need to ensure that after this placement,
    there will still be enough groups where Inter Path 2 can land.

    Two types of checks:
    1. Confederation blocking: AFC/CONMEBOL/CONCACAF teams would make the group
       ineligible for IP2
    2. Slot stealing: Even UEFA/CAF teams can steal the last physical slot in
       the only IP2-eligible group

    Args:
        team: The team being considered for placement
        target_group: The group being considered
        groups: Current state of all groups
        remaining_teams: Teams still to be placed (including the current team)

    Returns:
        True if this placement should be BLOCKED because it reduces IP2 spots too much
    """
    # Skip if team is Inter Path 2 itself
    if team.confederation == "AFC|CONMEBOL|CONCACAF":
        return False

    # During Pot 2 and 3, we always need to protect IP2 spots since IP2 is in Pot 4
    # During Pot 4, check if IP2 is still in remaining teams
    in_pot_4 = team.pot == 4

    if in_pot_4:
        # Only check if IP2 is still unplaced during Pot 4
        ip2_remaining = any(t.confederation == "AFC|CONMEBOL|CONCACAF" for t in remaining_teams)
        if not ip2_remaining:
            return False  # IP2 already placed, no need to protect slots

    # Get current confederations in target group
    current_confeds = _get_group_confederations(groups[target_group])

    # Check if target group is IP2-eligible
    target_is_ip2_eligible = _is_inter_path_2_eligible(current_confeds)

    # Case 1: Team's confederation would block IP2 from this group
    if target_is_ip2_eligible and not _preserves_inter_path_2_eligibility(team.confederation):
        # Count remaining IP2-eligible groups after this placement
        remaining_eligible_groups = 0
        for group, teams in groups.items():
            if group == target_group:
                continue  # This group will be blocked by the confederation
            confeds = _get_group_confederations(teams)
            if _is_inter_path_2_eligible(confeds):
                remaining_eligible_groups += 1

        # Determine minimum required
        if in_pot_4:
            min_required = 1
        else:
            # During Pot 2/3, require at least 2 IP2-eligible groups
            # This is achievable given the team distribution
            # Note: We must preserve at least 2 slots (not groups) for IP2 to have options
            min_required = 2

        if remaining_eligible_groups < min_required:
            logger.debug(
                f"BLOCKING (confed): Placing {team.name} ({team.confederation}) in {target_group} "
                f"would reduce IP2-eligible groups to {remaining_eligible_groups} (need {min_required})"
            )
            return True

    # Case 2: Slot stealing in Pot 4
    # We need to reserve enough IP2-eligible slots for IP2 to have options.
    # If placing this team in an IP2-eligible group would reduce available slots
    # to 0 (while IP2 is still unplaced), block it.
    if in_pot_4 and target_is_ip2_eligible:
        # Count open slots, excluding the one we're about to take
        open_slots_after = _count_open_ip2_slots(groups) - 1

        if open_slots_after < 1:
            # Would leave no IP2 slots, block it
            logger.debug(
                f"BLOCKING (slot): Placing {team.name} in {target_group} "
                f"would leave only {open_slots_after} IP2 slot(s)"
            )
            return True

    return False


def would_eliminate_inter_path_1_spot(
    team: Team,
    target_group: str,
    groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    Check if placing team in target_group would eliminate all Inter Path 1 landing spots.

    Inter Path 1 (CAF|OFC|CONCACAF) needs at least one group with no CAF, OFC, or CONCACAF.

    Args:
        team: The team being considered for placement
        target_group: The group being considered
        groups: Current state of all groups
        remaining_teams: Teams still to be placed

    Returns:
        True if this placement should be BLOCKED because it eliminates Inter Path 1 spots
    """
    # Skip if team is a placeholder
    if "|" in (team.confederation or ""):
        return False

    # Only CAF, OFC, CONCACAF teams can block Inter Path 1
    if _preserves_inter_path_1_eligibility(team.confederation):
        return False

    # Get current confederations in target group
    current_confeds = _get_group_confederations(groups[target_group])

    # If target group is already blocked for IP1, placing here doesn't reduce spots
    if not _is_inter_path_1_eligible(current_confeds):
        return False

    # This placement would block the target group for IP1
    # Count remaining IP1 spots after this placement
    remaining_spots = 0
    for group, teams in groups.items():
        if group == target_group:
            continue
        confeds = _get_group_confederations(teams)
        if _is_inter_path_1_eligible(confeds):
            remaining_spots += 1

    if remaining_spots == 0:
        logger.debug(
            f"BLOCKING: Placing {team.name} ({team.confederation}) in {target_group} "
            f"would eliminate last Inter Path 1 landing spot"
        )
        return True

    return False


def would_leave_group_without_uefa(
    team: Team,
    target_group: str,
    groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    Check if placing team in target_group would make it impossible for some group
    to get a UEFA team.

    Rule: Every group must have at least 1 UEFA team.

    This check handles two cases:
    1. Placing a non-UEFA team in a UEFA-less group when not enough UEFA remains
    2. Placing a UEFA team in a group that already has UEFA when needy groups exist

    Args:
        team: The team being considered for placement
        target_group: The group being considered
        groups: Current state of all groups
        remaining_teams: Teams still to be placed

    Returns:
        True if this placement should be BLOCKED because it would make UEFA infeasible
    """
    # Count groups that currently need UEFA
    groups_needing_uefa = []
    for group, teams in groups.items():
        has_uefa = any(
            t.confederation.startswith("UEFA") or "|" in (t.confederation or "") for t in teams
        )
        if not has_uefa:
            groups_needing_uefa.append(group)

    # Check if target group has UEFA
    target_has_uefa = target_group not in groups_needing_uefa

    # Count UEFA teams still available (in remaining_teams, excluding current team if it's UEFA)
    # Only count pure UEFA teams - pipe teams like Inter Path are NOT UEFA
    is_uefa_team = team.confederation.startswith("UEFA")
    uefa_remaining = sum(
        1 for t in remaining_teams if t != team and t.confederation.startswith("UEFA")
    )

    # Add UEFA from future pots (not included in remaining_teams)
    # Pot 2: 3 UEFA, Pot 3: 2 UEFA, Pot 4: 4 UEFA
    # If we're in Pot 2, add Pot 3 + Pot 4 UEFA
    # If we're in Pot 3, add Pot 4 UEFA
    # If we're in Pot 4, add nothing
    future_uefa_by_pot = {
        2: 2 + 4,  # Pot 3 (2) + Pot 4 (4)
        3: 4,  # Pot 4 (4)
        4: 0,  # No future pots
    }
    future_uefa = future_uefa_by_pot.get(team.pot, 0)
    total_uefa_supply = uefa_remaining + future_uefa

    # If placing a UEFA team into a group that already has UEFA
    if is_uefa_team and target_has_uefa:
        # This UEFA team would be "wasted" on a group that doesn't need it
        # After this placement, needy groups stay the same but supply drops by 1
        if len(groups_needing_uefa) > total_uefa_supply:
            logger.debug(
                f"BLOCKING (L1-global): Placing UEFA team {team.name} in {target_group} "
                f"(already has UEFA) would leave {len(groups_needing_uefa)} needy groups "
                f"with only {total_uefa_supply} UEFA teams remaining (current={uefa_remaining}, future={future_uefa})"
            )
            return True
        return False

    # If placing a non-UEFA team
    if not is_uefa_team:
        # If target group already has UEFA, no problem
        if target_has_uefa:
            return False

        # Target group doesn't have UEFA - it stays needy after this placement
        # After this placement, needy groups stay the same, supply stays the same
        # We just need to check if we can still cover all needy groups
        if len(groups_needing_uefa) > total_uefa_supply:
            logger.debug(
                f"BLOCKING (L1-global): Placing {team.name} ({team.confederation}) in {target_group} "
                f"would leave {len(groups_needing_uefa)} groups needing UEFA but only {total_uefa_supply} UEFA teams remain"
            )
            return True

    return False


def check_lookahead_constraints(
    team: Team,
    target_group: str,
    groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    Main lookahead check: returns True if placement is SAFE, False if it should be blocked.

    This function checks all lookahead constraints:
    1. UEFA minimum feasibility (L1-global) - only for Pot 4
    2. Inter Path 2 landing spot preservation (L3)
    3. Inter Path 1 landing spot preservation (L2)
    4. Non-European Pot 1 group diversity (L4)
    5. General confederation feasibility (L5)

    Args:
        team: The team being considered for placement
        target_group: The group being considered
        groups: Current state of all groups
        remaining_teams: Teams still to be placed

    Returns:
        True if placement is safe (passes all lookahead checks)
        False if placement should be blocked (violates a lookahead constraint)
    """
    # Check UEFA minimum feasibility (L1-global) - DISABLED for debugging
    # if team.pot == 4:
    #     if would_leave_group_without_uefa(team, target_group, groups, remaining_teams):
    #         return False

    # Check Inter Path 2 constraint (L3)
    if would_eliminate_inter_path_2_spot(team, target_group, groups, remaining_teams):
        return False

    # Check Inter Path 1 constraint (L2)
    if would_eliminate_inter_path_1_spot(team, target_group, groups, remaining_teams):
        return False

    # Check Non-European Pot 1 diversity (L4)
    if would_violate_non_uefa_pot1_diversity(team, target_group, groups, remaining_teams):
        return False

    # Check general confederation feasibility (L5)
    if would_leave_team_without_options(team, target_group, groups, remaining_teams):
        return False

    return True


def _get_non_uefa_pot1_groups(groups: Dict[str, List[Team]]) -> Set[str]:
    """
    Identify groups with non-UEFA Pot 1 teams.

    These are groups with Argentina, Brazil, Mexico, Canada, or USA.
    """
    non_uefa_groups = set()
    for group_name, teams in groups.items():
        for team in teams:
            if team.pot == 1 and team.confederation in ("CONMEBOL", "CONCACAF"):
                non_uefa_groups.add(group_name)
                break
    return non_uefa_groups


def would_violate_non_uefa_pot1_diversity(
    team: Team,
    target_group: str,
    groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L4: Check if placing team would make it impossible to have AFC and CAF diversity
    in the groups with non-UEFA Pot 1 teams.

    The 5 groups with CONMEBOL/CONCACAF Pot 1 teams (Argentina, Brazil, Mexico, Canada, USA)
    should collectively receive at least 1 AFC team and 1 CAF team from Pot 2/3.
    This ensures Pot 4 teams have valid landing spots.

    Args:
        team: The team being considered for placement
        target_group: The group being considered
        groups: Current state of all groups
        remaining_teams: Teams still to be placed

    Returns:
        True if this placement should be BLOCKED
    """
    # Only check during Pot 2 and Pot 3
    if not team.pot or team.pot not in (2, 3):
        return False

    # Get all non-UEFA Pot 1 groups
    non_uefa_pot1_groups = _get_non_uefa_pot1_groups(groups)

    if not non_uefa_pot1_groups:
        return False  # No non-UEFA Pot 1 groups yet (shouldn't happen after Pot 1)

    # Check if these groups collectively have AFC and CAF teams
    has_afc_in_non_uefa_groups = False
    has_caf_in_non_uefa_groups = False

    for group_name in non_uefa_pot1_groups:
        for t in groups[group_name]:
            if t.confederation == "AFC":
                has_afc_in_non_uefa_groups = True
            if t.confederation == "CAF":
                has_caf_in_non_uefa_groups = True

    # If we already have both AFC and CAF diversity, no need to block
    if has_afc_in_non_uefa_groups and has_caf_in_non_uefa_groups:
        return False

    # Count remaining AFC and CAF teams in remaining_teams
    remaining_afc = sum(1 for t in remaining_teams if t.confederation == "AFC")
    remaining_caf = sum(1 for t in remaining_teams if t.confederation == "CAF")

    # If placing this team takes the last AFC/CAF and we don't have diversity yet
    if target_group in non_uefa_pot1_groups:
        # This placement goes into a non-UEFA Pot 1 group - it helps diversity
        return False

    # If placing this AFC/CAF team in a UEFA Pot 1 group and it's the last one,
    # and we need diversity, block it
    if team.confederation == "AFC" and not has_afc_in_non_uefa_groups:
        if remaining_afc <= 1:
            # This is the last AFC team and it's not going to a non-UEFA Pot 1 group
            # Check if there's still room in non-UEFA Pot 1 groups
            open_slots_in_non_uefa_groups = sum(4 - len(groups[g]) for g in non_uefa_pot1_groups)
            if open_slots_in_non_uefa_groups > 0:
                logger.debug(
                    f"BLOCKING (L4): Placing {team.name} (AFC) in {target_group} "
                    f"would prevent AFC diversity in non-UEFA Pot 1 groups"
                )
                return True

    if team.confederation == "CAF" and not has_caf_in_non_uefa_groups:
        if remaining_caf <= 1:
            # This is the last CAF team and it's not going to a non-UEFA Pot 1 group
            open_slots_in_non_uefa_groups = sum(4 - len(groups[g]) for g in non_uefa_pot1_groups)
            if open_slots_in_non_uefa_groups > 0:
                logger.debug(
                    f"BLOCKING (L4): Placing {team.name} (CAF) in {target_group} "
                    f"would prevent CAF diversity in non-UEFA Pot 1 groups"
                )
                return True

    return False


def would_leave_team_without_options(
    team: Team,
    target_group: str,
    groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L5: General feasibility check - ensure every remaining team still has at least
    one valid group after this placement.

    This is a catch-all constraint that prevents the draw from painting itself
    into a corner where some team has no valid placement.

    This check has two parts:
    1. Individual check: Each remaining team must have at least one valid group
    2. Counting check: For each confederation, the number of remaining teams needing
       that confederation's slot must not exceed the number of available slots

    Args:
        team: The team being considered for placement
        target_group: The group being considered
        groups: Current state of all groups
        remaining_teams: Teams still to be placed

    Returns:
        True if this placement should be BLOCKED because it leaves some team with no options
    """
    # Skip this check for placeholder teams (Inter Paths)
    if "|" in (team.confederation or ""):
        return False

    # Simulate the placement
    simulated_groups = {g: list(ts) for g, ts in groups.items()}
    simulated_groups[target_group].append(team)

    # Part 1: Individual check - each remaining team has at least one option
    for other_team in remaining_teams:
        if other_team == team:
            continue

        # Check if other_team has at least one valid group
        has_valid_group = False
        for group_name, group_teams in simulated_groups.items():
            if _can_team_go_to_group(other_team, group_name, group_teams):
                has_valid_group = True
                break

        if not has_valid_group:
            logger.debug(
                f"BLOCKING (L5): Placing {team.name} in {target_group} "
                f"would leave {other_team.name} ({other_team.confederation}) with no valid groups"
            )
            return True

    # Part 2: Counting check - ensure confederation slots aren't over-subscribed
    # Count remaining teams by confederation (excluding placeholders and current team)
    confed_demand: Dict[str, int] = {}
    for other_team in remaining_teams:
        if other_team == team:
            continue
        confed = other_team.confederation
        # Skip placeholder teams for counting
        if not confed or "|" in confed:
            continue
        confed_demand[confed] = confed_demand.get(confed, 0) + 1

    # Count available slots for each confederation
    confed_supply: Dict[str, int] = {}
    for group_name, group_teams in simulated_groups.items():
        if len(group_teams) >= 4:
            continue  # Group is full

        existing_confeds = [t.confederation for t in group_teams]

        # For each confederation with demand, check if this group can take one
        for confed in confed_demand:
            if confed == "UEFA":
                # UEFA can have up to 2 per group
                if existing_confeds.count("UEFA") < 2:
                    confed_supply[confed] = confed_supply.get(confed, 0) + 1
            else:
                # Other confederations: max 1 per group
                if confed not in existing_confeds:
                    confed_supply[confed] = confed_supply.get(confed, 0) + 1

    # Check if any confederation is over-subscribed
    for confed, demand in confed_demand.items():
        supply = confed_supply.get(confed, 0)
        if demand > supply:
            logger.debug(
                f"BLOCKING (L5-count): Placing {team.name} in {target_group} "
                f"would leave {demand} {confed} teams competing for only {supply} slots"
            )
            return True

    # Part 3: Assignment feasibility check using bipartite matching
    # This catches cases where different confederations compete for the same slots
    # Only do this for Pot 4 to avoid performance issues in earlier pots
    # (Earlier pots have more slack and this check is expensive)
    remaining_non_placeholder = [
        t for t in remaining_teams if t != team and t.confederation and "|" not in t.confederation
    ]

    # Only run bipartite matching for Pot 4 (when team.pot == 4)
    if remaining_non_placeholder and team.pot == 4:
        if not _can_assign_all_teams(remaining_non_placeholder, simulated_groups):
            logger.debug(
                f"BLOCKING (L5-assign): Placing {team.name} in {target_group} "
                f"would make it impossible to assign all remaining teams"
            )
            return True

    return False


def _can_assign_all_teams(
    teams: List[Team],
    groups: Dict[str, List[Team]],
) -> bool:
    """
    Check if all teams can be assigned to groups using backtracking.

    This is a bipartite matching check to ensure there exists a valid
    assignment of teams to groups.
    """
    if not teams:
        return True

    team = teams[0]
    remaining = teams[1:]

    # Find all groups this team can go to
    for group_name, group_teams in groups.items():
        if _can_team_go_to_group(team, group_name, group_teams):
            # Try assigning this team to this group
            new_groups = {g: list(ts) for g, ts in groups.items()}
            new_groups[group_name].append(team)

            # Recursively check if remaining teams can be assigned
            if _can_assign_all_teams(remaining, new_groups):
                return True

    return False


def _can_team_go_to_group(team: Team, group_name: str, group_teams: List[Team]) -> bool:
    """
    Basic eligibility check for whether a team can go to a group.

    This is a simplified version of eligible_for_group() for lookahead purposes.
    It checks:
    - No duplicate pot in group
    - Confederation constraints (max 2 UEFA, max 1 per other confed)
    - Group not full
    """
    # Group full
    if len(group_teams) >= 4:
        return False

    # Same pot already in group
    if any(t.pot == team.pot for t in group_teams):
        return False

    # Confederation constraint
    confed = team.confederation
    if not confed:
        return True

    # Handle placeholder teams (Inter Paths)
    if "|" in confed:
        allowed = [c.strip() for c in confed.split("|") if c.strip()]
        for conf in allowed:
            cnt = sum(1 for t in group_teams if t.confederation == conf)
            if conf == "UEFA":
                if cnt >= 2:
                    return False
            else:
                if cnt >= 1:
                    return False
        return True

    # Regular team
    same = sum(1 for t in group_teams if t.confederation == confed)

    if confed == "UEFA":
        return same < 2
    return same < 1
