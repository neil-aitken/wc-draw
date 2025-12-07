"""World Cup 2026 Draw Simulator - Version 2 (Clean Slate)

This module implements the FIFA World Cup 2026 draw following official rules.
No speculative features - just the documented FIFA constraints.

Official FIFA Rules:
1. 48 teams divided into 12 groups of 4 teams each
2. Teams drawn from 4 pots (pot 1 → pot 4)
3. Hosts (USA, Canada, Mexico) fixed to groups A, B, D respectively
4. No group can have more than 1 team from the same confederation (except UEFA: max 2)
5. Every group must have at least 1 UEFA team

Lookahead Constraints (experimental, configurable):
- L1: Ensure UEFA minimum feasibility across all groups (REDUNDANT: covered by L7)
- L2: Preserve landing spots for Inter Path 1 (CAF|OFC|CONCACAF) (REDUNDANT: covered by L9)
- L3: Preserve landing spots for Inter Path 2 (AFC|CONMEBOL|CONCACAF) - REQUIRED
- L4: Diversity for groups with non-UEFA Pot 1 hosts (REDUNDANT: covered by L3/L7/L9)
- L5: General feasibility check using bipartite matching (removed - too slow)
- L6: Preserve landing spots for pot 4 CAF teams - REQUIRED
- L7: Reserve UEFA slots for remaining UEFA teams per pot - REQUIRED
- L8: Reserve CONCACAF slots (non-host groups) - REQUIRED
- L9: Reserve CAF slots (CAF-free groups) - REQUIRED
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from .parser import Team


# =============================================================================
# Quadrant Definitions (for top 4 bracket separation)
# =============================================================================

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


def _get_quadrant_for_group(group: str) -> str:
    """Return which quadrant a group belongs to."""
    for quadrant, groups in QUADRANTS.items():
        if group in groups:
            return quadrant
    raise ValueError(f"Unknown group: {group}")


def _get_half_for_quadrant(quadrant: str) -> str:
    """Return which half a quadrant belongs to."""
    for half, quadrants in HALVES.items():
        if quadrant in quadrants:
            return half
    raise ValueError(f"Unknown quadrant: {quadrant}")


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class LookaheadConfig:
    """Feature flags for lookahead constraints and draw style."""

    # Draw style: FIFA-style (random draw, lowest eligible group) vs MRV heuristic
    fifa_style: bool = False

    # L1: Block placements that would leave a group without UEFA
    l1_uefa_minimum: bool = False

    # L2: Preserve landing spots for Inter Path 1 (CAF|OFC|CONCACAF)
    l2_inter_path_1: bool = False

    # L3: Preserve landing spots for Inter Path 2 (AFC|CONMEBOL|CONCACAF)
    l3_inter_path_2: bool = False

    # L4: Ensure non-UEFA Pot 1 groups get diverse confederations
    l4_non_uefa_diversity: bool = False

    # L5: (removed - was bipartite matching, too slow)

    # L6: Preserve landing spots for pot 4 CAF teams (Cape Verde, Ghana, Inter Path 1)
    l6_pot4_caf_landing: bool = False

    # L7: Reserve enough <2 UEFA groups for remaining UEFA teams in each pot
    l7_uefa_slots: bool = False

    # L8: Reserve spots for CONCACAF teams that can't go to CONCACAF-host groups
    l8_concacaf_slots: bool = False

    # L9: Reserve spots for CAF teams (max 1 per group, so need CAF-free groups)
    l9_caf_slots: bool = False

    # L10: Reserve spots for constrained confederations (CONMEBOL, AFC) in each pot
    l10_confederation_slots: bool = False

    # L11: Combined IP2/CONMEBOL preservation in pot 2
    l11_ip2_conmebol_combined: bool = False

    # L12: Pot 3 team viability check
    l12_pot3_viability: bool = False

    # L13: Pot 4 Jordan/IP2 protection  
    l13_pot4_jordan_ip2: bool = False

    # L14: Pot 3 UEFA distribution for pot 4 CAF viability
    l14_pot3_uefa_caf_distribution: bool = False


# =============================================================================
# Core Draw Logic
# =============================================================================

GROUP_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]


def is_eligible(
    team: Team,
    group: List[Team],
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
    lookahead: LookaheadConfig,
) -> bool:
    """
    Check if a team can be placed in a group.

    Args:
        team: The team to place
        group: Current teams in the target group
        group_name: Label of the target group (A-L)
        all_groups: All groups and their current teams
        remaining_teams: Teams still to be placed (including this team)
        lookahead: Lookahead constraint configuration

    Returns:
        True if placement is allowed, False otherwise
    """
    # Rule: No two teams from the same pot in one group
    if any(t.pot == team.pot for t in group):
        return False

    # Rule: Confederation limits
    if not _check_confederation_limit(team, group):
        return False

    # Rule: Every group needs at least 1 UEFA team (global check)
    if not _check_uefa_minimum(team, group, remaining_teams, all_groups):
        return False

    # Lookahead constraints (optional, skip if None)
    if lookahead is not None:
        if not _check_lookahead(team, group_name, all_groups, remaining_teams, lookahead):
            return False

    return True


def _check_confederation_limit(team: Team, group: List[Team]) -> bool:
    """
    Check confederation limits: max 2 UEFA, max 1 for others.

    Handles pipe-separated confederations (e.g., "AFC|CONMEBOL|CONCACAF")
    which can take any of those confederations.

    For pipe teams: since we don't know which confederation they'll be,
    we must ensure ALL options have room. Otherwise, if the "wrong" team
    wins the playoff, the group would be invalid.
    """
    if "|" in team.confederation:
        # Team can be any of the listed confederations
        # Block if ANY option would exceed the limit
        allowed = [c.strip() for c in team.confederation.split("|")]
        for conf in allowed:
            count = _count_confederation(conf, group)
            limit = 2 if conf == "UEFA" else 1
            if count >= limit:
                return False  # This option is blocked
        return True  # All options have room

    # Simple single-confederation team
    conf = team.confederation
    count = _count_confederation(conf, group)
    limit = 2 if conf == "UEFA" else 1
    return count < limit


def _count_confederation(conf: str, group: List[Team]) -> int:
    """Count teams matching a confederation, including pipe teams that could be that conf."""
    count = 0
    for t in group:
        if t.confederation == conf:
            count += 1
        elif "|" in t.confederation:
            # Pipe team already placed - count if it could be this conf
            if conf in [c.strip() for c in t.confederation.split("|")]:
                count += 1
    return count


def _check_uefa_minimum(
    team: Team,
    group: List[Team],
    remaining_teams: List[Team],
    all_groups: Optional[Dict[str, List[Team]]] = None,
) -> bool:
    """
    Ensure every group can still get at least 1 UEFA team.

    Checks:
    1. Local: This group will have a slot for UEFA if needed
    2. Global: Enough UEFA teams remain for all groups that need them
    3. Efficiency: Don't waste UEFA teams on groups that already have them
       when other groups still need UEFA
    """
    # Check if group already has UEFA
    has_uefa = any(t.confederation.startswith("UEFA") or "UEFA" in t.confederation for t in group)

    # Check if team being placed is/could-be UEFA
    is_team_uefa = team.confederation.startswith("UEFA") or "UEFA" in team.confederation

    # This group will have UEFA after placement?
    group_will_have_uefa = has_uefa or is_team_uefa

    # Local check: if placing non-UEFA in group without UEFA, need slot remaining
    if not group_will_have_uefa:
        remaining_slots = 4 - len(group) - 1  # -1 for the team we're placing
        if remaining_slots < 1:
            return False  # No slot left for UEFA in this group

    # Global check: count groups needing UEFA vs UEFA teams available
    if all_groups is not None:
        # Count groups that will NOT have UEFA after this placement
        groups_needing_uefa = 0
        for g_name, g_teams in all_groups.items():
            g_has_uefa = any(t.confederation.startswith("UEFA") or "UEFA" in t.confederation for t in g_teams)
            if g_has_uefa:
                continue  # This group is fine

            # Is this the group we're placing into?
            if g_teams is group:
                if not is_team_uefa:
                    groups_needing_uefa += 1
            else:
                groups_needing_uefa += 1

        # Count UEFA teams remaining (excluding the one being placed)
        remaining_uefa = sum(1 for t in remaining_teams if t != team and (t.confederation.startswith("UEFA") or "UEFA" in t.confederation))

        # Basic check: enough UEFA teams for groups that need them?
        if groups_needing_uefa > remaining_uefa:
            return False

        # Strict efficiency check: if placing UEFA into group that already has UEFA,
        # block if there are groups that still need UEFA and we have no slack
        # (i.e., remaining UEFA teams exactly equals groups needing them)
        if is_team_uefa and has_uefa and groups_needing_uefa > 0:
            spare_uefa = remaining_uefa - groups_needing_uefa
            if spare_uefa < 0:
                # No slack - this UEFA should go to a group that needs it
                return False

    return True


def _check_lookahead(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
    config: LookaheadConfig,
) -> bool:
    """Apply enabled lookahead constraints."""

    if config.l1_uefa_minimum:
        if not _lookahead_uefa_minimum(team, group_name, all_groups, remaining_teams):
            return False

    if config.l2_inter_path_1:
        if not _lookahead_inter_path_1(team, group_name, all_groups, remaining_teams):
            return False

    if config.l3_inter_path_2:
        if not _lookahead_inter_path_2(team, group_name, all_groups, remaining_teams):
            return False

    if config.l4_non_uefa_diversity:
        if not _lookahead_non_uefa_diversity(team, group_name, all_groups, remaining_teams):
            return False

    if config.l6_pot4_caf_landing:
        if not _lookahead_pot4_caf(team, group_name, all_groups, remaining_teams):
            return False

    if config.l7_uefa_slots:
        if not _lookahead_uefa_slots(team, group_name, all_groups, remaining_teams):
            return False

    if config.l8_concacaf_slots:
        if not _lookahead_concacaf_slots(team, group_name, all_groups, remaining_teams):
            return False

    if config.l9_caf_slots:
        if not _lookahead_caf_slots(team, group_name, all_groups, remaining_teams):
            return False

    return True


# =============================================================================
# Lookahead Constraint Implementations
# =============================================================================


def _lookahead_uefa_minimum(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L1: Ensure UEFA teams go to groups that need them.

    If placing a UEFA team in a group that already has UEFA, check that
    there are enough UEFA teams for the groups that still need them.
    """
    # Count groups that need UEFA
    groups_needing_uefa = []
    for g, teams in all_groups.items():
        has_uefa = any(t.confederation.startswith("UEFA") for t in teams)
        if not has_uefa:
            groups_needing_uefa.append(g)

    # Is target group one that needs UEFA?
    target_needs_uefa = group_name in groups_needing_uefa

    # Count UEFA remaining (excluding current team)
    is_uefa = team.confederation.startswith("UEFA")
    uefa_remaining = sum(1 for t in remaining_teams if t != team and t.confederation.startswith("UEFA"))

    # If placing UEFA in group that already has UEFA
    if is_uefa and not target_needs_uefa:
        # Would this leave too many needy groups?
        if len(groups_needing_uefa) > uefa_remaining:
            return False

    return True


def _lookahead_inter_path_1(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L2: Preserve landing spots for Inter Path 1 (CAF|OFC|CONCACAF).

    Block placements that would eliminate all valid groups for Inter Path 1.
    """
    IP1_CONFEDS = {"CAF", "OFC", "CONCACAF"}

    # Find Inter Path 1 team
    ip1 = next((t for t in remaining_teams if t.name == "Inter Path 1"), None)
    if ip1 is None or ip1 == team:
        return True  # IP1 already placed or is being placed

    # Simulate placement
    simulated = {g: list(teams) for g, teams in all_groups.items()}
    simulated[group_name].append(team)

    # Count valid groups for IP1 after this placement
    valid_groups = 0
    for g, teams in simulated.items():
        if len(teams) >= 4:
            continue
        # Check if any IP1 confed is blocked
        blocked = False
        for conf in IP1_CONFEDS:
            if _count_confederation(conf, teams) >= 1:
                blocked = True
                break
        if not blocked:
            valid_groups += 1

    return valid_groups >= 1


def _lookahead_inter_path_2(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L3: Preserve landing spots for Inter Path 2 (AFC|CONMEBOL|CONCACAF).

    Inter Path 2 needs a group with:
    - Pot 1: UEFA team (not CONCACAF/CONMEBOL host)
    - Pot 2: CAF or UEFA team
    - Pot 3: CAF or UEFA team

    This ensures the group has no AFC, CONMEBOL, or CONCACAF teams,
    allowing Inter Path 2 to match any of its three confederation options.
    """
    # Find Inter Path 2 team
    ip2 = next((t for t in remaining_teams if t.name == "Inter Path 2"), None)
    if ip2 is None or ip2 == team:
        return True  # IP2 already placed or is being placed

    # Valid confederations for each pot position
    VALID_POT1 = {"UEFA"}  # Only UEFA pot 1 teams work
    VALID_POT23 = {"CAF", "UEFA"}  # CAF or UEFA in pots 2 and 3

    # Simulate placement
    simulated = {g: list(teams) for g, teams in all_groups.items()}
    simulated[group_name].append(team)

    # Count remaining CAF teams in pot 3 (these could fill groups that need CAF)
    remaining_caf_pot3 = sum(1 for t in remaining_teams if t.pot == 3 and t.confederation == "CAF" and t != team)

    # Count groups that could still host IP2
    # A group is valid if it CAN end up with UEFA pot 1 + CAF/UEFA pot 2 + CAF/UEFA pot 3
    valid_groups = 0
    groups_needing_caf = 0  # Groups that need CAF specifically (already have 2 UEFA)

    for g, teams in simulated.items():
        if len(teams) >= 4:
            continue  # Group is full

        # Check current composition
        pot1_teams = [t for t in teams if t.pot == 1]
        pot2_teams = [t for t in teams if t.pot == 2]
        pot3_teams = [t for t in teams if t.pot == 3]

        # Pot 1 must be UEFA (already placed in pot 1)
        if pot1_teams:
            if pot1_teams[0].confederation not in VALID_POT1:
                continue  # This group has non-UEFA pot 1, can't host IP2

        # If pot 2 is placed, it must be CAF or UEFA
        if pot2_teams:
            if pot2_teams[0].confederation not in VALID_POT23:
                continue  # This group has blocking pot 2 team

        # If pot 3 is placed, it must be CAF or UEFA
        if pot3_teams:
            if pot3_teams[0].confederation not in VALID_POT23:
                continue  # This group has blocking pot 3 team
            valid_groups += 1
        else:
            # Pot 3 is empty - check what can go here
            uefa_count = sum(1 for t in teams if t.confederation == "UEFA")
            caf_count = sum(1 for t in teams if t.confederation == "CAF")

            # UEFA max is 2, CAF max is 1
            can_take_uefa = uefa_count < 2
            can_take_caf = caf_count < 1

            if not can_take_uefa and not can_take_caf:
                continue  # Neither CAF nor UEFA can go here

            if can_take_caf and can_take_uefa:
                valid_groups += 1  # Either works
            elif can_take_caf:
                groups_needing_caf += 1  # Only CAF works
            else:
                valid_groups += 1  # Only UEFA works (rare)

    # Must have at least 1 valid group, and enough CAF teams for groups that need them
    if valid_groups >= 1:
        return True
    elif groups_needing_caf > 0 and remaining_caf_pot3 >= groups_needing_caf:
        return True
    else:
        return False


def _lookahead_non_uefa_diversity(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L4: Ensure groups with non-UEFA Pot 1 hosts get diverse confederations.

    The 5 non-UEFA hosts (USA, Canada, Mexico, Argentina, Brazil) create groups
    that need more diversity since they start without UEFA.
    """
    # Identify non-UEFA Pot 1 groups
    non_uefa_groups = set()
    for g, teams in all_groups.items():
        pot1_teams = [t for t in teams if t.pot == 1]
        if pot1_teams and not pot1_teams[0].confederation.startswith("UEFA"):
            non_uefa_groups.add(g)

    if not non_uefa_groups:
        return True

    # If targeting a non-UEFA Pot 1 group with same confed as Pot 1 team
    if group_name in non_uefa_groups:
        pot1_confed = next((t.confederation for t in all_groups[group_name] if t.pot == 1), None)
        if pot1_confed and team.confederation == pot1_confed:
            # Check if there are enough diverse teams remaining
            # This is a soft constraint - allow if no alternative
            diverse_remaining = sum(1 for t in remaining_teams if t != team and t.confederation != pot1_confed)
            if diverse_remaining == 0:
                return True  # No alternative, allow it
            # Check if other groups need this team more
            return True  # Simplified - just return True for now

    return True


def _is_caf_team(team: Team) -> bool:
    """Check if a team is CAF (not just containing 'CAF' as substring)."""
    # Split confederation by | for multi-confed teams
    confeds = team.confederation.split("|")
    return "CAF" in confeds


def _lookahead_uefa_slots(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L7: Reserve enough <2 UEFA groups for remaining UEFA teams in current pot.

    Problem: MRV places most-constrained teams first. UEFA teams often have
    MORE options (can go to groups with 0 or 1 UEFA), so they get placed last.
    But by then, all <2 UEFA groups may be filled by non-UEFA teams.

    Solution: When a non-UEFA team wants to go to a <2 UEFA group, check if
    there are enough <2 UEFA groups remaining for the UEFA teams in this pot.
    """
    # Only matters for non-UEFA teams targeting <2 UEFA groups
    is_uefa = team.confederation == "UEFA"
    if is_uefa:
        return True  # UEFA teams can always go to <2 UEFA groups

    # Simulate placement
    simulated = {g: list(teams) for g, teams in all_groups.items()}
    simulated[group_name].append(team)

    # Get current pot
    current_pot = team.pot
    expected_size = current_pot  # After this pot completes, groups have this many

    # Count UEFA teams remaining in this pot (excluding current team)
    uefa_remaining_this_pot = sum(1 for t in remaining_teams if t.pot == current_pot and t.confederation == "UEFA" and t != team)

    if uefa_remaining_this_pot == 0:
        return True  # No UEFA teams left in this pot

    # Count groups with <2 UEFA that still need a team from this pot
    # These are groups where we could still place a UEFA team
    available_for_uefa = 0
    for g, teams in simulated.items():
        # Group still needs a team from this pot if size < expected_size
        if len(teams) >= expected_size:
            continue  # Already has its team from this pot

        # Count UEFA in this group
        uefa_count = sum(1 for t in teams if t.confederation == "UEFA")
        if uefa_count < 2:
            available_for_uefa += 1

    # Must have enough slots for remaining UEFA teams
    return available_for_uefa >= uefa_remaining_this_pot


def _lookahead_concacaf_slots(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L8: Reserve spots for CONCACAF teams that can't go to CONCACAF-host groups.

    Problem: Panama (pot 3) and Haiti/Curacao (pot 4) are CONCACAF teams.
    They cannot go to groups A, B, D which have CONCACAF hosts (Mexico, Canada, USA).
    So they can only go to 9 groups (C, E-L) that are CONCACAF-free.

    For pot 4: CONCACAF teams also need UEFA in the group (L1 minimum), so they
    can only go to CONCACAF-free, non-host groups WITH UEFA.

    Additionally for pot 4 CONCACAF teams: we must ensure placing them won't
    strand OTHER CONCACAF teams due to L7 (UEFA slot reservation).

    Solution: When placing a CONCACAF team, check that remaining CONCACAF teams
    can still find groups that don't conflict with UEFA reservation.
    """
    CONCACAF_HOST_GROUPS = {"A", "B", "D"}

    # This constraint applies to both CONCACAF and non-CONCACAF teams
    is_concacaf = team.confederation == "CONCACAF"
    is_host_group = group_name in CONCACAF_HOST_GROUPS

    # Simulate placement
    simulated = {g: list(teams) for g, teams in all_groups.items()}
    simulated[group_name].append(team)

    # Get current pot
    current_pot = team.pot
    expected_size = current_pot  # After this pot completes, groups have this many

    # Count CONCACAF teams remaining in this pot (excluding current team)
    concacaf_remaining = sum(1 for t in remaining_teams if t.pot == current_pot and t.confederation == "CONCACAF" and t != team)

    if concacaf_remaining == 0:
        return True  # No CONCACAF teams left in this pot

    # For non-CONCACAF teams: check slot availability
    if not is_concacaf:
        # Basic slot count (only for non-host groups - those are what CONCACAF needs)
        if not is_host_group:
            available_for_concacaf = 0
            for g, teams in simulated.items():
                if g in CONCACAF_HOST_GROUPS:
                    continue
                if len(teams) >= expected_size:
                    continue
                has_concacaf = any("CONCACAF" in t.confederation for t in teams)
                if has_concacaf:
                    continue
                if current_pot == 4:
                    has_uefa = any("UEFA" in t.confederation for t in teams)
                    if not has_uefa:
                        continue
                available_for_concacaf += 1

            if available_for_concacaf < concacaf_remaining:
                return False

        # For pot 4: ALSO check UEFA/CONCACAF interaction
        # ANY pot 4 placement (including to host groups!) can affect the balance
        # of shared groups that both CONCACAF and UEFA need.
        # We must ensure UEFA won't crowd out CONCACAF from shared groups.
        if current_pot == 4:
            uefa_remaining = sum(1 for t in remaining_teams if t.pot == current_pot and t.confederation == "UEFA" and t != team)

            # After placement, count shared vs UEFA-only groups
            concacaf_eligible = []
            uefa_eligible = []
            for g, teams in simulated.items():
                if len(teams) >= expected_size:
                    continue
                g_confeds = [t.confederation for t in teams]
                has_concacaf_g = any("CONCACAF" in c for c in g_confeds)
                has_uefa_g = any("UEFA" in c for c in g_confeds)
                uefa_count = sum(1 for c in g_confeds if c == "UEFA")

                # CONCACAF can't go to host groups (A, B, D)
                if g not in CONCACAF_HOST_GROUPS and not has_concacaf_g and has_uefa_g:
                    concacaf_eligible.append(g)
                # UEFA can go to any group with <2 UEFA (including host groups)
                if uefa_count < 2:
                    uefa_eligible.append(g)

            uefa_only = [g for g in uefa_eligible if g not in concacaf_eligible]

            # If UEFA needs shared groups, check CONCACAF availability
            if len(uefa_only) < uefa_remaining:
                uefa_needs_shared = uefa_remaining - len(uefa_only)
                concacaf_available = len(concacaf_eligible) - uefa_needs_shared
                if concacaf_available < concacaf_remaining:
                    return False

        return True

    # For CONCACAF teams in pot 4: check L7 interaction
    # When we place a CONCACAF team, it takes a CONCACAF-free+UEFA slot.
    # The remaining CONCACAF teams need their own slots.
    # But L7 also reserves <2 UEFA groups for UEFA teams.
    # If a CONCACAF slot is ALSO needed by L7, we could strand the next CONCACAF.
    if is_concacaf and current_pot == 4:
        # Count UEFA teams remaining (excluding team being placed)
        uefa_remaining = sum(1 for t in remaining_teams if t.pot == current_pot and t.confederation == "UEFA" and t != team)

        # Count groups that are: CONCACAF-free, UEFA, non-host, unfilled
        # These are valid for CONCACAF teams
        concacaf_eligible_groups = []
        for g, teams in simulated.items():
            if g in CONCACAF_HOST_GROUPS:
                continue
            if len(teams) >= expected_size:
                continue
            has_concacaf = any("CONCACAF" in t.confederation for t in teams)
            if has_concacaf:
                continue
            has_uefa = any("UEFA" in t.confederation for t in teams)
            if not has_uefa:
                continue
            concacaf_eligible_groups.append(g)

        # Count groups that can take UEFA (< 2 UEFA) and are unfilled
        # These groups include the CONCACAF-eligible ones plus some others
        uefa_eligible_groups = []
        for g, teams in simulated.items():
            if len(teams) >= expected_size:
                continue
            uefa_count = sum(1 for t in teams if t.confederation == "UEFA")
            if uefa_count < 2:
                uefa_eligible_groups.append(g)

        # Groups that are ONLY usable by UEFA (not by CONCACAF)
        # These are: <2 UEFA but either (host group OR has CONCACAF OR no UEFA)
        uefa_only_groups = [g for g in uefa_eligible_groups if g not in concacaf_eligible_groups]

        # If UEFA can be fully satisfied by uefa_only groups, CONCACAF is fine
        if len(uefa_only_groups) >= uefa_remaining:
            return len(concacaf_eligible_groups) >= concacaf_remaining

        # UEFA needs some shared groups. Check if there's still room for CONCACAF.
        uefa_from_shared = uefa_remaining - len(uefa_only_groups)
        concacaf_available = len(concacaf_eligible_groups) - uefa_from_shared

        return concacaf_available >= concacaf_remaining

    return True  # Default: allow


def _lookahead_caf_slots(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L9: Reserve spots for CAF teams (max 1 per group).

    Problem: CAF limit is 1 team per group. If non-CAF teams fill all CAF-free
    groups before CAF teams are placed, some CAF teams get stuck.

    For pot 3: CAF teams need CAF-free groups, but also must preserve
              CAF-free+UEFA groups for pot 4 CAF teams.
              Key insight: pot 3 CAF teams should go to non-UEFA groups when
              possible, to leave UEFA groups CAF-free for pot 4.
    For pot 4: CAF teams need groups that are CAF-free AND have UEFA.
              Also need to account for CONCACAF needing some of the same groups.

    Solution: When placing a non-CAF team, ensure enough CAF-viable groups
    remain for both current pot and future pots.
    """
    current_pot = team.pot

    # Only apply to pots 3 and 4
    if current_pot < 3:
        return True

    # Only matters for non-CAF teams
    if _is_caf_team(team):
        return True

    # Simulate placement
    simulated = {g: list(teams) for g, teams in all_groups.items()}
    simulated[group_name].append(team)

    expected_size = current_pot  # Groups should have this many teams after this pot

    # Count CAF teams remaining in this pot
    caf_remaining_this_pot = sum(1 for t in remaining_teams if t.pot == current_pot and _is_caf_team(t) and t != team)

    # Count CAF-free groups for this pot
    available_for_caf = 0
    for g, teams in simulated.items():
        if len(teams) >= expected_size:
            continue
        has_caf = any(_is_caf_team(t) for t in teams)
        if has_caf:
            continue
        # For pot 4: also need UEFA
        if current_pot == 4:
            has_uefa = any("UEFA" in t.confederation for t in teams)
            if not has_uefa:
                continue
        available_for_caf += 1

    if available_for_caf < caf_remaining_this_pot:
        return False

    # For pot 4: Also check combined CAF + CONCACAF constraint
    # Both CAF and CONCACAF teams need CONCACAF-free + UEFA groups (non-host)
    # If the shared pool is too small, both constraints can't be satisfied
    if current_pot == 4:
        CONCACAF_HOST_GROUPS = {"A", "B", "D"}

        # Count CONCACAF teams remaining
        concacaf_remaining = sum(1 for t in remaining_teams if t.pot == 4 and t.confederation == "CONCACAF" and t != team)

        if concacaf_remaining > 0:
            # CAF teams need: CAF-free + UEFA
            # CONCACAF teams need: CONCACAF-free + UEFA + non-host
            # The shared pool is: CAF-free + CONCACAF-free + UEFA + non-host

            # Count groups only available to CONCACAF (have CAF already, but no CONCACAF)
            concacaf_only = 0
            for g, teams in simulated.items():
                if g in CONCACAF_HOST_GROUPS:
                    continue
                if len(teams) >= expected_size:
                    continue
                has_concacaf = any("CONCACAF" in t.confederation for t in teams)
                if has_concacaf:
                    continue
                has_uefa = any("UEFA" in t.confederation for t in teams)
                if not has_uefa:
                    continue
                has_caf = any(_is_caf_team(t) for t in teams)
                if has_caf:
                    concacaf_only += 1  # Has CAF but not CONCACAF, only for CONCACAF

            # After CAF takes all their needed slots from shared pool,
            # CONCACAF has: concacaf_only + (shared - caf_remaining)
            # Shared pool = available_for_caf (CAF-free + UEFA)
            # (subset of CONCACAF-eligible)

            # CONCACAF available = concacaf_only + max(0, available_for_caf - caf)
            concacaf_available_after_caf = concacaf_only + max(0, available_for_caf - caf_remaining_this_pot)

            if concacaf_available_after_caf < concacaf_remaining:
                return False

    return True


def _lookahead_pot4_caf(
    team: Team,
    group_name: str,
    all_groups: Dict[str, List[Team]],
    remaining_teams: List[Team],
) -> bool:
    """
    L6: Preserve landing spots for pot 4 CAF teams.

    pot 4 CAF teams (3 total) MUST go to groups that have UEFA AND are CAF-free.

    This requires:
    1. All 12 groups must have UEFA by pot 3 end (7 from pot 1 + 5 additions)
    2. Pot 2 UEFA (3) + pot 3 UEFA (2) = 5 teams to cover 5 non-UEFA groups

    So pot 2 UEFA teams MUST go to non-UEFA groups. To ensure this:
    - Block pot 2 UEFA from going to already-UEFA groups
    - Block non-UEFA teams from taking too many non-UEFA slots (leave room for UEFA)

    Additionally, for CAF teams:
    - Apply the standard check that enough CAF-free+UEFA groups remain
    """
    POT4_CAF_NAMES = {"Cape Verde", "Ghana", "Inter Path 1"}

    # Only apply during pot 2 (groups have exactly 1 team before placement)
    current_sizes = [len(ts) for ts in all_groups.values()]
    if min(current_sizes) != 1 or max(current_sizes) != 1:
        return True  # Not pot 2

    # Check pot 4 CAF count
    pot4_caf_count = len([t for t in remaining_teams if t.name in POT4_CAF_NAMES])
    if pot4_caf_count == 0:
        return True

    # Target group characteristics
    target_has_uefa = any("UEFA" in t.confederation for t in all_groups[group_name])
    is_uefa_team = "UEFA" in team.confederation

    # Count current state (before this placement)
    non_uefa_groups_before = sum(1 for g in all_groups if not any("UEFA" in t.confederation for t in all_groups[g]))

    # Count pot 2 UEFA teams remaining (including current if applicable)
    pot2_uefa_remaining = len([t for t in remaining_teams if t.pot == 2 and "UEFA" in t.confederation and t != team])
    if is_uefa_team:
        pot2_uefa_total = pot2_uefa_remaining + 1  # Include current team
    else:
        pot2_uefa_total = pot2_uefa_remaining

    # Constraint 1: UEFA teams must go to non-UEFA groups
    if is_uefa_team and target_has_uefa:
        # Allow only if there are more remaining UEFA teams than non-UEFA groups
        # (meaning we have "spare" UEFA teams that can go to already-UEFA groups)
        pot3_uefa_count = 2
        total_uefa_to_place = pot2_uefa_remaining + pot3_uefa_count
        if target_has_uefa:
            # This would waste a UEFA team on already-UEFA group
            # Only allow if we have more UEFA teams than needed
            if total_uefa_to_place <= non_uefa_groups_before:
                return False  # Block - we need all UEFA to spread

    # Constraint 2: Non-UEFA teams should not take too many non-UEFA slots
    # We need pot 2 UEFA (pot2_uefa_total) slots in non-UEFA groups
    if not is_uefa_team and not target_has_uefa:
        # This non-UEFA team wants to go to a non-UEFA group
        # Check if this would leave enough room for UEFA teams

        # Simulate placement
        simulated = {g: list(teams) for g, teams in all_groups.items()}
        simulated[group_name].append(team)

        # Count available non-UEFA groups after this placement
        available_non_uefa = 0
        for g, teams in simulated.items():
            if len(teams) > 1:  # Already has pot 2 team
                continue
            has_uefa = any("UEFA" in t.confederation for t in teams)
            if not has_uefa:
                available_non_uefa += 1

        # Check if remaining pot 2 UEFA can fit
        if available_non_uefa < pot2_uefa_total:
            return False  # Block - not enough room for UEFA teams

    # Constraint 3: Standard CAF constraint
    # Simulate placement
    simulated = {g: list(teams) for g, teams in all_groups.items()}
    simulated[group_name].append(team)

    # Count groups with/without UEFA and CAF after this placement
    uefa_groups = 0
    non_uefa_groups = 0
    caf_in_uefa_groups = 0

    for _, teams in simulated.items():
        has_uefa = any("UEFA" in t.confederation for t in teams)
        has_caf = any(_is_caf_team(t) for t in teams)
        if has_uefa:
            uefa_groups += 1
            if has_caf:
                caf_in_uefa_groups += 1
        else:
            non_uefa_groups += 1

    # Count remaining teams
    pot2_caf_remaining = len([t for t in remaining_teams if t.pot == 2 and _is_caf_team(t) and t != team])
    pot3_caf_count = 5
    pot3_uefa_count = 2

    # Maximum UEFA groups achievable
    max_uefa_additions = min(pot2_uefa_remaining + pot3_uefa_count, non_uefa_groups)
    max_uefa_groups_final = uefa_groups + max_uefa_additions

    # Maximum CAF teams in UEFA groups (worst case)
    max_caf_in_uefa_final = caf_in_uefa_groups + pot2_caf_remaining + pot3_caf_count

    # Available CAF-free+UEFA groups for pot 4 CAF
    min_available = max_uefa_groups_final - max_caf_in_uefa_final

    return min_available >= pot4_caf_count


# =============================================================================
# Pot 1 Top 4 Separation
# =============================================================================


def _identify_top4(pot1_teams: List[Team]) -> List[Team]:
    """Identify the top 4 ranked teams from Pot 1."""
    ranked = [t for t in pot1_teams if t.fifa_ranking]
    ranked.sort(key=lambda t: t.fifa_ranking)
    return ranked[:4]


def _get_available_groups_for_top4(
    team: Team,
    groups: Dict[str, List[Team]],
    top4_placements: Dict[str, str],  # team_name -> quadrant
    top4_teams: List[Team],
) -> List[str]:
    """
    Get groups available for a top 4 team respecting quadrant constraints.

    Rules:
    1. Each top 4 must be in a different quadrant
    2. Top 2 (ranks 1-2) must be in opposite halves
    3. Seeds 3-4 (ranks 3-4) must be in opposite halves
    """
    # Get empty groups
    empty_groups = [g for g, teams in groups.items() if not teams]

    # Filter by quadrant constraints
    available = []
    for group in empty_groups:
        quadrant = _get_quadrant_for_group(group)

        # Rule 1: Quadrant must not already have a top 4 team
        if quadrant in top4_placements.values():
            continue

        half = _get_half_for_quadrant(quadrant)

        # Rule 2: Top 2 must be in opposite halves
        if team.fifa_ranking <= 2:
            # Find the other top 2 team
            other_top2 = next(
                (t for t in top4_teams if t.fifa_ranking <= 2 and t.name != team.name),
                None,
            )
            if other_top2 and other_top2.name in top4_placements:
                other_q = top4_placements[other_top2.name]
                other_h = _get_half_for_quadrant(other_q)
                if half == other_h:
                    continue

        # Rule 3: Seeds 3-4 must be in opposite halves
        if team.fifa_ranking in [3, 4]:
            other_seed34 = next(
                (t for t in top4_teams if t.fifa_ranking in [3, 4] and t.name != team.name),
                None,
            )
            if other_seed34 and other_seed34.name in top4_placements:
                other_q = top4_placements[other_seed34.name]
                other_h = _get_half_for_quadrant(other_q)
                if half == other_h:
                    continue

        available.append(group)

    return available


def _get_available_groups_for_non_top4(
    groups: Dict[str, List[Team]],
    quadrants_with_top4: set,
) -> List[str]:
    """
    Get groups available for non-top-4 teams.

    Rule: Cannot fill the last group in a quadrant that doesn't have a top 4 yet.
    """
    empty_groups = [g for g, teams in groups.items() if not teams]

    available = []
    for group in empty_groups:
        quadrant = _get_quadrant_for_group(group)

        # If quadrant already has top 4, all groups are available
        if quadrant in quadrants_with_top4:
            available.append(group)
            continue

        # Count empty groups in this quadrant
        quadrant_groups = QUADRANTS[quadrant]
        empty_in_quadrant = sum(1 for g in quadrant_groups if not groups[g])

        # If more than 1 empty, can use this group
        if empty_in_quadrant > 1:
            available.append(group)

    return available


def draw_pot1_with_separation(
    pot1_teams: List[Team],
    groups: Dict[str, List[Team]],
    rng: random.Random,
) -> bool:
    """
    Draw pot 1 with top 4 quadrant separation constraints.

    Hosts are pre-placed. This draws the remaining pot 1 teams
    ensuring top 4 are in different quadrants.
    """
    # Identify top 4 among all pot 1 (including pre-placed hosts)
    all_pot1 = pot1_teams + [t for g in groups.values() for t in g if t.pot == 1]
    top4_teams = _identify_top4(all_pot1)
    top4_names = {t.name for t in top4_teams}

    # Track top 4 placements (quadrant for each placed top 4)
    top4_placements: Dict[str, str] = {}

    # Check already-placed hosts
    for group, teams in groups.items():
        for t in teams:
            if t.name in top4_names:
                quadrant = _get_quadrant_for_group(group)
                top4_placements[t.name] = quadrant

    # Remaining teams to place
    remaining = list(pot1_teams)

    while remaining:
        # Use MRV: place most constrained team first
        team_options = []
        for team in remaining:
            if team.name in top4_names:
                available = _get_available_groups_for_top4(team, groups, top4_placements, top4_teams)
            else:
                quadrants_with_top4 = set(top4_placements.values())
                available = _get_available_groups_for_non_top4(groups, quadrants_with_top4)

            team_options.append((team, available))

        # Sort by MRV
        team_options.sort(key=lambda x: len(x[1]))

        team, eligible = team_options[0]

        if not eligible:
            return False

        # Place team
        target = rng.choice(eligible)
        groups[target].append(team)
        remaining.remove(team)

        # Update top 4 tracking
        if team.name in top4_names:
            quadrant = _get_quadrant_for_group(target)
            top4_placements[team.name] = quadrant

    return True


# =============================================================================
# Draw Execution
# =============================================================================


def draw_pot(
    pot: List[Team],
    groups: Dict[str, List[Team]],
    rng: random.Random,
    lookahead: LookaheadConfig,
    future_pots: Optional[List[List[Team]]] = None,
) -> bool:
    """
    Draw a single pot into the groups using single-pass MRV heuristic.

    Uses Most Restricted Variable (MRV) ordering: always place the team
    with the fewest eligible groups first. This maximizes the chance of
    finding a valid arrangement without backtracking.

    Args:
        pot: Teams in this pot
        groups: Current group state (modified in place on success)
        rng: Random number generator
        lookahead: Lookahead configuration
        future_pots: Teams in future pots (for lookahead checking)

    Returns:
        True if successful, False if stuck (no valid placement found)
    """
    if not pot:
        return True

    future_pots = future_pots or []

    # Determine expected group size before this pot
    expected_size = pot[0].pot - 1

    # Teams remaining to place in this pot
    remaining = list(pot)

    while remaining:
        # All remaining teams = this pot's remaining + all future pots
        all_remaining = remaining + [t for fp in future_pots for t in fp]

        # Find eligible groups for each remaining team in this pot
        team_options = []
        for team in remaining:
            if team.fixed_group:
                # Fixed teams can only go to their assigned group
                if is_eligible(
                    team,
                    groups[team.fixed_group],
                    team.fixed_group,
                    groups,
                    all_remaining,
                    lookahead,
                ):
                    eligible = [team.fixed_group]
                else:
                    eligible = []
            else:
                eligible = [
                    g
                    for g, grp in groups.items()
                    if len(grp) == expected_size and len(grp) < 4 and is_eligible(team, grp, g, groups, all_remaining, lookahead)
                ]
            team_options.append((team, eligible))

        # Sort by MRV: fewest options first
        # For pot 3: break ties by giving CAF teams priority
        # This helps CAF teams get first pick at non-UEFA groups
        if pot[0].pot == 3:
            # Secondary key: CAF teams get priority (0) over non-CAF (1)
            team_options.sort(key=lambda x: (len(x[1]), 0 if _is_caf_team(x[0]) else 1))
        else:
            team_options.sort(key=lambda x: len(x[1]))

        # Take the most constrained team
        team, eligible = team_options[0]

        if not eligible:
            # No valid placement - draw failed
            return False

        # For pot 3: special group selection to preserve CAF-free+UEFA for pot 4
        if pot[0].pot == 3:
            if _is_caf_team(team):
                # CAF teams prefer non-UEFA groups to preserve UEFA CAF-free for pot 4
                non_uefa_groups = [g for g in eligible if not any("UEFA" in t.confederation for t in groups[g])]
                if non_uefa_groups:
                    target = rng.choice(non_uefa_groups)
                else:
                    target = rng.choice(eligible)
            else:
                # Non-CAF teams prefer UEFA groups (leaving non-UEFA for CAF teams)
                uefa_groups = [g for g in eligible if any("UEFA" in t.confederation for t in groups[g])]
                if uefa_groups:
                    target = rng.choice(uefa_groups)
                else:
                    target = rng.choice(eligible)
        else:
            # Randomly pick among eligible groups
            target = rng.choice(eligible)
        groups[target].append(team)
        remaining.remove(team)

    return True


def run_draw(
    pots: Dict[int, List[Team]],
    seed: Optional[int] = None,
    lookahead: Optional[LookaheadConfig] = None,
) -> tuple[Dict[str, List[Team]], int]:
    """
    Run a complete World Cup draw (single pass, no retries).

    Args:
        pots: Dictionary mapping pot number (1-4) to list of teams
        seed: Random seed for reproducibility (None = random)
        lookahead: Lookahead constraint configuration

    Returns:
        Tuple of (groups dict, seed used)

    Raises:
        RuntimeError: If draw cannot be completed
    """
    if lookahead is None:
        lookahead = LookaheadConfig()

    if seed is None:
        seed = random.SystemRandom().randint(0, 2**32 - 1)

    rng = random.Random(seed)

    # Initialize empty groups
    groups: Dict[str, List[Team]] = {label: [] for label in GROUP_LABELS}

    # Pre-place hosts (fixed_group teams) - skip all eligibility checks
    # This is an optimization: hosts are guaranteed valid placements
    pot1_teams = list(pots.get(1, []))
    hosts = [t for t in pot1_teams if t.fixed_group]
    non_hosts = [t for t in pot1_teams if not t.fixed_group]

    for host in hosts:
        assert host.fixed_group is not None  # We filtered for this above
        groups[host.fixed_group].append(host)

    # Draw pot 1 with top 4 separation constraints
    if non_hosts:
        if not draw_pot1_with_separation(non_hosts, groups, rng):
            raise RuntimeError("Failed to place pot 1 with top 4 separation")

    # Build modified pots for pots 2-4
    modified_pots = {k: v for k, v in pots.items() if k > 1}

    # Draw pots 2-4 with lookahead constraints
    pot_nums = [2, 3, 4]
    for i, pot_num in enumerate(pot_nums):
        if pot_num not in modified_pots:
            continue

        # Collect future pots for lookahead
        future_pots = [modified_pots[p] for p in pot_nums[i + 1 :] if p in modified_pots]

        if not draw_pot(modified_pots[pot_num], groups, rng, lookahead, future_pots):
            raise RuntimeError(f"Failed to place pot {pot_num}")

    return groups, seed


# =============================================================================
# Utility Functions
# =============================================================================


def validate_draw(groups: Dict[str, List[Team]]) -> List[str]:
    """
    Validate a completed draw against FIFA rules.

    Returns list of violation messages (empty if valid).
    """
    violations = []

    for group_name, teams in groups.items():
        # Check group size
        if len(teams) != 4:
            violations.append(f"Group {group_name} has {len(teams)} teams (expected 4)")
            continue

        # Check pot uniqueness
        pots_seen = set()
        for t in teams:
            if t.pot in pots_seen:
                violations.append(f"Group {group_name} has multiple pot {t.pot} teams")
            pots_seen.add(t.pot)

        # Check confederation limits
        # For non-pipe teams, count them directly
        # For pipe teams, they can be any of their listed confeds (don't count as violation)
        confed_counts: Dict[str, int] = {}
        for t in teams:
            if "|" not in t.confederation:
                conf = t.confederation
                confed_counts[conf] = confed_counts.get(conf, 0) + 1

        # Also count pipe teams that could match each non-pipe confederation
        # A pipe team can potentially conflict with any of its listed confeds
        for t in teams:
            if "|" in t.confederation:
                pipe_confeds = [c.strip() for c in t.confederation.split("|")]
                for conf in pipe_confeds:
                    if conf in confed_counts:
                        # This pipe team could conflict with existing teams of this conf
                        confed_counts[conf] = confed_counts.get(conf, 0) + 1

        for conf, count in confed_counts.items():
            limit = 2 if conf == "UEFA" else 1
            if count > limit:
                violations.append(f"Group {group_name} has {count} {conf} teams (max {limit})")

        # Check UEFA minimum
        has_uefa = any(t.confederation.startswith("UEFA") or "UEFA" in t.confederation for t in teams)
        if not has_uefa:
            violations.append(f"Group {group_name} has no UEFA team")

    # Check top 4 quadrant separation
    # Find pot 1 teams and their rankings
    pot1_teams = []
    for group_name, teams in groups.items():
        for t in teams:
            if t.pot == 1 and t.fifa_ranking:
                pot1_teams.append((t, group_name))

    # Sort by ranking to identify top 4
    pot1_teams.sort(key=lambda x: x[0].fifa_ranking)
    top4 = pot1_teams[:4] if len(pot1_teams) >= 4 else []

    if len(top4) == 4:
        # Check: All 4 must be in different quadrants
        quadrants_used = {}
        for team, group in top4:
            q = _get_quadrant_for_group(group)
            if q in quadrants_used:
                violations.append(f"Top 4 separation: {team.name} and {quadrants_used[q]} are both in quadrant {q}")
            quadrants_used[q] = team.name

        # Check: Top 2 (ranks 1-2) must be in opposite halves
        top2 = top4[:2]
        if len(top2) == 2:
            q1 = _get_quadrant_for_group(top2[0][1])
            q2 = _get_quadrant_for_group(top2[1][1])
            h1 = _get_half_for_quadrant(q1)
            h2 = _get_half_for_quadrant(q2)
            if h1 == h2:
                violations.append(f"Top 2 separation: {top2[0][0].name} and {top2[1][0].name} are both in {h1}")

        # Check: Seeds 3-4 (ranks 3-4) must be in opposite halves
        seeds34 = top4[2:4]
        if len(seeds34) == 2:
            q3 = _get_quadrant_for_group(seeds34[0][1])
            q4 = _get_quadrant_for_group(seeds34[1][1])
            h3 = _get_half_for_quadrant(q3)
            h4 = _get_half_for_quadrant(q4)
            if h3 == h4:
                violations.append(f"Seeds 3-4 separation: {seeds34[0][0].name} and {seeds34[1][0].name} are both in {h3}")

    return violations


def print_draw(groups: Dict[str, List[Team]]) -> None:
    """Print a draw result in a readable format."""
    for group_name in GROUP_LABELS:
        teams = groups.get(group_name, [])
        print(f"\nGroup {group_name}:")
        for i, team in enumerate(teams, 1):
            flag = team.flag or ""
            print(f"  {i}. {flag} {team.name} ({team.confederation})")
