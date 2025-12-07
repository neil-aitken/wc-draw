"""
Playoff simulator for determining World Cup qualifiers.

Simulates:
1. UEFA Playoffs - 4 paths with 4-team brackets (semifinal + final)
2. Intercontinental Playoffs - 2 paths with 3-team single elimination
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import UEFA_PLAYOFFS, IC_PLAYOFFS
from .match_engine import simulate_match


@dataclass
class PlayoffResult:
    """Result of playoff simulation for a single path."""
    path: str
    winner: str
    runner_up: Optional[str] = None  # Semifinal loser for 3-team path
    bracket: List[str] = None        # All teams in the bracket
    semifinal_results: List[tuple] = None  # Tuple of (team_a, team_b, winner)
    final_result: Optional[tuple] = None   # (team_a, team_b, winner)


def simulate_uefa_playoff(path: str, teams: List[str]) -> PlayoffResult:
    """
    Simulate a UEFA playoff path (4-team bracket).

    Bracket structure:
    - Semifinal 1: teams[0] vs teams[1]
    - Semifinal 2: teams[2] vs teams[3]
    - Final: Winner SF1 vs Winner SF2

    Args:
        path: Path identifier (A, B, C, D)
        teams: List of 4 teams in bracket order

    Returns:
        PlayoffResult with the winner
    """
    if len(teams) != 4:
        raise ValueError(f"UEFA playoff requires 4 teams, got {len(teams)}")

    # Semifinal 1
    sf1 = simulate_match(teams[0], teams[1], knockout=True)
    sf1_winner = sf1.winner

    # Semifinal 2
    sf2 = simulate_match(teams[2], teams[3], knockout=True)
    sf2_winner = sf2.winner

    # Final
    final = simulate_match(sf1_winner, sf2_winner, knockout=True)
    final_winner = final.winner

    return PlayoffResult(
        path=f"UEFA Path {path}",
        winner=final_winner,
        bracket=teams,
        semifinal_results=[
            (teams[0], teams[1], sf1_winner),
            (teams[2], teams[3], sf2_winner),
        ],
        final_result=(sf1_winner, sf2_winner, final_winner),
    )


def simulate_ic_playoff(path: str, teams: List[str]) -> PlayoffResult:
    """
    Simulate an Intercontinental playoff path (3-team single elimination).

    Bracket structure:
    - Play-in: teams[1] vs teams[2] (lower seeds play first)
    - Final: teams[0] vs Winner of play-in

    Args:
        path: Path identifier (1, 2)
        teams: List of 3 teams [bye_team, play_in_team_1, play_in_team_2]

    Returns:
        PlayoffResult with the winner
    """
    if len(teams) != 3:
        raise ValueError(f"IC playoff requires 3 teams, got {len(teams)}")

    bye_team = teams[0]  # Higher seed gets bye

    # Play-in match
    playin = simulate_match(teams[1], teams[2], knockout=True)
    playin_winner = playin.winner
    playin_loser = playin.loser

    # Final
    final = simulate_match(bye_team, playin_winner, knockout=True)
    final_winner = final.winner

    return PlayoffResult(
        path=f"IC Path {path}",
        winner=final_winner,
        runner_up=playin_loser,
        bracket=teams,
        semifinal_results=[
            (teams[1], teams[2], playin_winner),
        ],
        final_result=(bye_team, playin_winner, final_winner),
    )


@dataclass
class AllPlayoffsResult:
    """Combined result of all playoff simulations."""
    winners: Dict[str, str]  # Path -> winner team
    losers: List[str]        # All teams that lost their playoff (did not qualify)


def simulate_all_playoffs() -> AllPlayoffsResult:
    """
    Simulate all playoff paths and return winners and losers.

    Returns:
        AllPlayoffsResult with winners dict and list of all losers
    """
    winners = {}
    losers = []

    # UEFA Playoffs (4 paths)
    for path, teams in UEFA_PLAYOFFS.items():
        result = simulate_uefa_playoff(path, teams)
        winners[result.path] = result.winner
        # All teams except winner are losers
        losers.extend([t for t in teams if t != result.winner])

    # IC Playoffs (2 paths)
    for path, teams in IC_PLAYOFFS.items():
        result = simulate_ic_playoff(path, teams)
        winners[result.path] = result.winner
        # All teams except winner are losers
        losers.extend([t for t in teams if t != result.winner])

    return AllPlayoffsResult(winners=winners, losers=losers)


def replace_playoff_placeholders(groups: Dict[str, List[str]],
                                  playoff_result: AllPlayoffsResult) -> Dict[str, List[str]]:
    """
    Replace playoff placeholders in groups with actual winners.

    Args:
        groups: Group definitions with placeholders like "UEFA Path A"
        playoff_result: Result containing mapping of path to winner team

    Returns:
        New groups dict with placeholders replaced
    """
    new_groups = {}

    for group_letter, teams in groups.items():
        new_teams = []
        for team in teams:
            if team in playoff_result.winners:
                new_teams.append(playoff_result.winners[team])
            else:
                new_teams.append(team)
        new_groups[group_letter] = new_teams

    return new_groups


# Convenience function for quick simulation
def get_playoff_qualified_groups() -> Dict[str, List[str]]:
    """
    Run playoff simulation and return groups with qualified teams.

    Returns:
        Groups with playoff placeholders replaced by winners
    """
    from .config import GROUPS
    result = simulate_all_playoffs()
    return replace_playoff_placeholders(GROUPS, result)


if __name__ == "__main__":
    # Test playoff simulation
    print("Simulating playoffs...")
    print()

    result = simulate_all_playoffs()
    print("Playoff Winners:")
    for path, winner in sorted(result.winners.items()):
        print(f"  {path}: {winner}")

    print()
    print(f"Did Not Qualify ({len(result.losers)} teams):")
    for team in sorted(result.losers):
        print(f"  {team}")

    print()
    print("Final groups:")
    from .config import GROUPS
    groups = replace_playoff_placeholders(GROUPS, result)
    for letter, teams in sorted(groups.items()):
        print(f"  Group {letter}: {', '.join(teams)}")
