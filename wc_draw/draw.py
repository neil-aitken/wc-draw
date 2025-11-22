import logging
import random
from typing import Dict, List, Optional

from .config import DrawConfig
from .parser import Team

logger = logging.getLogger(__name__)


def _check_uefa_group_winner_constraint(team: Team, grp_teams: List[Team]) -> bool:
    """
    Return True if team can be placed without violating UEFA group winner rule.

    Rule: At most one UEFA qualifying group winner per World Cup group.

    If the team being placed is a UEFA group winner, ensure no other
    UEFA group winner is already in the group.
    """
    if not team.uefa_group_winner:
        return True

    # Check if any existing team is also a UEFA group winner
    for existing in grp_teams:
        if existing.uefa_group_winner:
            return False

    return True


def draw_pot1(pot1: List[Team], rng: Optional[random.Random] = None) -> Dict[str, List[Team]]:
    """Allocate teams from pot1 into 12 groups labeled A..L.

    Hosts (team.host==True with fixed_group set) are placed into their fixed groups.
    Remaining pot1 teams are drawn randomly into remaining empty pot1 slots.

    Returns mapping group_label -> list of Team (pot1 only).
    """
    if rng is None:
        rng = random.Random()

    groups = {chr(ord("A") + i): [] for i in range(12)}

    # Work on a mutable copy
    remaining = list(pot1)

    # Place hosts first
    for team in list(remaining):
        if team.host and team.fixed_group:
            grp = team.fixed_group
            if grp not in groups:
                raise ValueError(f"Invalid fixed group '{grp}' for host {team.name}")
            if groups[grp]:
                raise ValueError(f"Group {grp} already has a pot1 team")
            groups[grp].append(team)
            remaining.remove(team)

    # Fill remaining empty pot1 slots
    empty_groups = [g for g, v in groups.items() if not v]

    while remaining:
        team = rng.choice(remaining)
        # possible groups are those that are empty
        possible = [g for g in empty_groups if not groups[g]]
        if not possible:
            raise RuntimeError("No available groups to place team")
        grp = rng.choice(possible)
        groups[grp].append(team)
        remaining.remove(team)
        empty_groups.remove(grp)

    return groups


def draw_pot(
    pot: List[Team],
    groups: Dict[str, List[Team]],
    rng: Optional[random.Random] = None,
    max_attempts: int = 5000,
    allow_early: bool = False,
    config: Optional[DrawConfig] = None,
) -> Dict[str, List[Team]]:
    if rng is None:
        rng = random.Random()
    if config is None:
        config = DrawConfig()

    def eligible_for_group(team: Team, grp_teams: List[Team]):
        # Do not allow more than one team from the same pot in a single group.
        # This ensures we never place two teams from, e.g., pot 4, into the same
        # group when placing pots out-of-order or using fallback logic.
        if any(t.pot == team.pot for t in grp_teams):
            return False

        # Check UEFA group winner constraint if enabled
        if config.uefa_group_winners_separated:
            if not _check_uefa_group_winner_constraint(team, grp_teams):
                return False

        if "|" in team.confederation:
            allowed = [c.strip() for c in team.confederation.split("|") if c.strip()]
            for conf in allowed:
                cnt = sum(1 for t in grp_teams if t.confederation == conf)
                if conf == "UEFA":
                    if cnt >= 2:
                        return False
                else:
                    if cnt >= 1:
                        return False
            return True

        # count same-confed teams for a simple single-confed team
        # Include placeholders that allow this confederation as blocking
        def placeholder_allows(t, conf):
            if not t.confederation:
                return False
            if "|" not in t.confederation:
                return False
            allowed = [c.strip() for c in t.confederation.split("|") if c.strip()]
            return conf in allowed

        same = 0
        for t in grp_teams:
            if t.confederation == team.confederation:
                same += 1
            elif placeholder_allows(t, team.confederation):
                # treat a placeholder that could be this confed as occupying it
                same += 1

        if team.confederation == "UEFA":
            return same < 2
        return same < 1

    # We'll attempt several random shuffles and greedy placements
    teams = list(pot)

    if teams and teams[0].pot == 4:
        specials = [
            t
            for t in teams
            if "|" in (t.confederation or "")
            or "playoff" in t.name.lower()
            or "path" in t.name.lower()
        ]
        others = [t for t in teams if t not in specials]
        # place specials first by ordering them at front of the shuffled list
        teams = specials + others

    # determine expected group size before placing this pot: pot numbers start at 1
    if not teams:
        return groups
    expected_pre_size = teams[0].pot - 1

    for attempt in range(1, max_attempts + 1):
        rng.shuffle(teams)
        # work on a fresh copy of current groups for this attempt
        working = {g: list(v) for g, v in groups.items()}
        failed = False

        for team in teams:
            # If team has a fixed_group, try to place there if eligible
            if team.fixed_group:
                if team.fixed_group not in working:
                    failed = True
                    break
                if not eligible_for_group(team, working[team.fixed_group]):
                    failed = True
                    break
                # Insert into the group's list at the pot-specific position so
                # the group's team list preserves pot ordering (pot1..pot4).
                pos = max(0, team.pot - 1)
                if pos >= len(working[team.fixed_group]):
                    working[team.fixed_group].append(team)
                else:
                    working[team.fixed_group].insert(pos, team)
                continue

            # Determine eligible groups. For pot4 we do NOT require groups to
            # already have `expected_pre_size` teams — instead allow any group
            # with room (<4) that satisfies confederation constraints. For
            # other pots, require groups at the expected slot size to preserve
            # the usual slot-by-slot filling.
            if team.pot == 4:
                # Prefer groups that currently have exactly one team (pot1 placed)
                preferred = [
                    g for g, ts in working.items() if len(ts) == 1 and eligible_for_group(team, ts)
                ]
                if preferred:
                    eligible = preferred
                else:
                    # Fallback: allow any group with room if no preferred groups
                    # are available. This fallback keeps the draw from deadlocking
                    # when the preferred placement is impossible due to confed
                    # constraints.
                    eligible = [
                        g
                        for g, ts in working.items()
                        if len(ts) < 4 and eligible_for_group(team, ts)
                    ]
            else:
                eligible = [
                    g
                    for g, ts in working.items()
                    if len(ts) == expected_pre_size and len(ts) < 4 and eligible_for_group(team, ts)
                ]
            # If nothing matches the expected pre-size, only fall back when
            # we're placing a later pot earlier than the current group sizes
            # (e.g. attempting to place pot4 when groups haven't reached size 3).
            if not eligible:
                current_max = max(len(ts) for ts in working.values())
                # allow fallback either when explicitly requested (allow_early)
                # or when expected_pre_size is larger than current_max (placing
                # a later pot earlier than usual). Note: for pot4 we already
                # considered all groups with room, so fallback here indicates
                # no eligible groups at all and should fail.
                if allow_early or expected_pre_size > current_max:
                    fallback = [
                        g
                        for g, ts in working.items()
                        if len(ts) < 4 and eligible_for_group(team, ts)
                    ]
                    if not fallback:
                        failed = True
                        break
                    # prefer groups with the minimum current size to keep groups balanced
                    min_size = min(len(working[g]) for g in fallback)
                    eligible = [g for g in fallback if len(working[g]) == min_size]
                else:
                    failed = True
                    break
            pick = rng.choice(eligible)
            # Insert the team at the slot corresponding to its pot (0-based)
            pos = max(0, team.pot - 1)
            if pos >= len(working[pick]):
                working[pick].append(team)
            else:
                working[pick].insert(pos, team)

        if not failed:
            # success: copy working back into groups
            for g in groups:
                groups[g] = working[g]
            # Log if we needed more than one attempt
            if attempt > 1:
                try:
                    pot_num = teams[0].pot
                except Exception:
                    pot_num = "?"
                logger.debug("draw_pot: placed pot %s after %d attempts", pot_num, attempt)
            return groups

    # If random attempts failed, try a deterministic backtracking solver
    # as a last resort. This is more expensive but guarantees we explore
    # the search space systematically to find any feasible assignment.
    def compute_eligible(team: Team, working: Dict[str, List[Team]]):
        # reuse the same eligible-group logic as above
        if team.fixed_group:
            if team.fixed_group not in working:
                return []
            return [team.fixed_group] if eligible_for_group(team, working[team.fixed_group]) else []

        if team.pot == 4:
            preferred = [
                g for g, ts in working.items() if len(ts) == 1 and eligible_for_group(team, ts)
            ]
            if preferred:
                return preferred
            return [g for g, ts in working.items() if len(ts) < 4 and eligible_for_group(team, ts)]

        expected = team.pot - 1
        eligible = [
            g
            for g, ts in working.items()
            if len(ts) == expected and len(ts) < 4 and eligible_for_group(team, ts)
        ]
        if eligible:
            return eligible

        current_max = max(len(ts) for ts in working.values())
        if allow_early or expected > current_max:
            fallback = [
                g for g, ts in working.items() if len(ts) < 4 and eligible_for_group(team, ts)
            ]
            if not fallback:
                return []
            min_size = min(len(working[g]) for g in fallback)
            return [g for g in fallback if len(working[g]) == min_size]
        return []

    def backtrack_assign(
        teams_left: List[Team], working: Dict[str, List[Team]]
    ) -> Optional[Dict[str, List[Team]]]:
        if not teams_left:
            return working
        # MRV heuristic: pick team with fewest eligible groups first
        elig_list = [(t, compute_eligible(t, working)) for t in teams_left]
        # If any team has no eligible groups, prune
        for t, elig in elig_list:
            if not elig:
                return None
        teams_left_sorted = sorted(elig_list, key=lambda te: len(te[1]))
        team, elig_groups = teams_left_sorted[0]
        # Try groups in order (deterministic) to keep reproducibility
        for g in elig_groups:
            wk_copy = {gr: list(ts) for gr, ts in working.items()}
            pos = max(0, team.pot - 1)
            if pos >= len(wk_copy[g]):
                wk_copy[g].append(team)
            else:
                wk_copy[g].insert(pos, team)
            remaining = [t for t in teams_left if t is not team]
            result = backtrack_assign(remaining, wk_copy)
            if result is not None:
                return result
        return None

    # Attempt backtracking on a fresh copy of the current groups
    working_start = {g: list(v) for g, v in groups.items()}
    bt_result = backtrack_assign(teams, working_start)
    if bt_result is not None:
        for g in groups:
            groups[g] = bt_result[g]
        return groups

    raise RuntimeError(f"Unable to place pot after {max_attempts} attempts")


def run_full_draw(
    pots: Dict[int, List[Team]],
    seed: Optional[int] = None,
    max_attempts: int = 5000,
    report_fallbacks: bool = False,
    config: Optional[DrawConfig] = None,
):
    """Perform the full draw sequence (pot1, pot2, pot3, pot4) and return
    the resulting groups and the integer seed used.

    This uses the classic tournament ordering: pot1 then pot2 then pot3 then
    pot4. `max_attempts` is forwarded to the underlying placement attempts.

    If `seed` is None a cryptographically-random 32-bit seed is generated.
    The RNG is always initialized from the returned seed so runs are
    reproducible when reusing that value.
    """
    if config is None:
        config = DrawConfig()

    metadata = {"fallback": None}

    if seed is None:
        seed = random.SystemRandom().randint(0, 2**32 - 1)
    rng = random.Random(seed)

    groups = draw_pot1(pots[1], rng=rng)

    # Local copy of eligible check used by the global backtracking fallback.
    def eligible_for_group_local(team: Team, grp_teams: List[Team]):
        if any(t.pot == team.pot for t in grp_teams):
            return False

        # Check UEFA group winner constraint if enabled
        if config.uefa_group_winners_separated:
            if not _check_uefa_group_winner_constraint(team, grp_teams):
                return False

        if "|" in team.confederation:
            allowed = [c.strip() for c in team.confederation.split("|") if c.strip()]
            for conf in allowed:
                cnt = sum(1 for t in grp_teams if t.confederation == conf)
                if conf == "UEFA":
                    if cnt >= 2:
                        return False
                else:
                    if cnt >= 1:
                        return False
            return True

        def placeholder_allows(t, conf):
            if not t.confederation:
                return False
            if "|" not in t.confederation:
                return False
            allowed = [c.strip() for c in t.confederation.split("|") if c.strip()]
            return conf in allowed

        same = 0
        for t in grp_teams:
            if t.confederation == team.confederation:
                same += 1
            elif placeholder_allows(t, team.confederation):
                same += 1

        if team.confederation == "UEFA":
            return same < 2
        return same < 1

    try:
        # Classic ordering: pot2, pot3, then pot4.
        draw_pot(
            pots[2], groups, rng=rng, max_attempts=max_attempts, allow_early=False, config=config
        )
        draw_pot(
            pots[3], groups, rng=rng, max_attempts=max_attempts, allow_early=True, config=config
        )
        draw_pot(
            pots[4], groups, rng=rng, max_attempts=max_attempts, allow_early=True, config=config
        )
        if report_fallbacks:
            return groups, seed, metadata
        return groups, seed
    except RuntimeError:
        # Try several alternate pot ordering fallbacks before attempting the
        # expensive global backtracking solver. Some seeds become feasible if
        # pot3/4 are drawn in a slightly different sequence.
        alternate_orderings = [
            [2, 4, 3],
            [4, 2, 3],
            [3, 4, 2],
        ]
        for ordering in alternate_orderings:
            try:
                alt_groups = draw_pot1(pots[1], rng=rng)
                for p in ordering:
                    # allow_early for later pots to reduce deadlocks
                    allow = True if p >= 3 else False
                    draw_pot(
                        pots[p],
                        alt_groups,
                        rng=rng,
                        max_attempts=max_attempts,
                        allow_early=allow,
                        config=config,
                    )
                metadata["fallback"] = {"type": "alternate_ordering", "ordering": ordering}
                if report_fallbacks:
                    return alt_groups, seed, metadata
                return alt_groups, seed
            except RuntimeError:
                continue

        # As a last-resort fallback, attempt a global backtracking solver that
        # assigns all remaining teams from pots 2..4 simultaneously given the
        # fixed pot1 placement. This is more expensive but can resolve edge
        # cases where greedy incremental placement creates infeasible states.
        remaining = list(pots[2]) + list(pots[3]) + list(pots[4])
        working_start = {g: list(v) for g, v in groups.items()}

        def compute_eligible_full(team, working):
            if team.fixed_group:
                if team.fixed_group not in working:
                    return []
                if eligible_for_group_local(team, working[team.fixed_group]):
                    return [team.fixed_group]
                return []
            return [
                g for g, ts in working.items() if len(ts) < 4 and eligible_for_group_local(team, ts)
            ]

        def backtrack_all(teams_left, working):
            if not teams_left:
                return working
            elig_list = [(t, compute_eligible_full(t, working)) for t in teams_left]
            for t, elig in elig_list:
                if not elig:
                    return None
            teams_left_sorted = sorted(elig_list, key=lambda te: len(te[1]))
            team, elig_groups = teams_left_sorted[0]
            for g in elig_groups:
                wk = {gr: list(ts) for gr, ts in working.items()}
                pos = max(0, team.pot - 1)
                if pos >= len(wk[g]):
                    wk[g].append(team)
                else:
                    wk[g].insert(pos, team)
                remaining2 = [t for t in teams_left if t is not team]
                res = backtrack_all(remaining2, wk)
                if res is not None:
                    return res
            return None

        result = backtrack_all(remaining, working_start)
        if result is None:
            raise
        for g in groups:
            groups[g] = result[g]
        metadata["fallback"] = {"type": "global_backtracking"}
        if report_fallbacks:
            return groups, seed, metadata
        return groups, seed
