"""
Group stage simulator with full FIFA tiebreaker rules.

Simulates all group matches and determines final standings using:
1. Points
2. Goal difference
3. Goals scored
4. Head-to-head points (among tied teams)
5. Head-to-head goal difference
6. Head-to-head goals scored
7. Fair play points (coin flip simulation)
8. FIFA ranking
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from itertools import combinations

from .match_engine import simulate_match, get_simulator, MatchResult


@dataclass
class TeamStanding:
    """Standing record for a team in a group."""
    team: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    def __repr__(self):
        return (f"{self.team}: {self.points}pts ({self.wins}-{self.draws}-{self.losses}) "
                f"GD:{self.goal_difference:+d} GF:{self.goals_for}")


@dataclass
class GroupResult:
    """Result of a group stage simulation."""
    group_letter: str
    teams: List[str]
    standings: List[TeamStanding]  # Ordered by final position
    matches: List[MatchResult]
    h2h_records: Dict[Tuple[str, str], Dict]  # Head-to-head records


class GroupSimulator:
    """
    Simulates a single group and determines final standings.
    """

    def __init__(self, group_letter: str, teams: List[str]):
        if len(teams) != 4:
            raise ValueError(f"Group must have 4 teams, got {len(teams)}")

        self.group_letter = group_letter
        self.teams = teams
        self.standings: Dict[str, TeamStanding] = {
            team: TeamStanding(team=team) for team in teams
        }
        self.matches: List[MatchResult] = []
        self.h2h_records: Dict[Tuple[str, str], Dict] = {}

        # Get FIFA rankings for tiebreaker
        self.simulator = get_simulator()

    def _record_match(self, result: MatchResult) -> None:
        """Record match result in standings and H2H records."""
        self.matches.append(result)

        team_a, team_b = result.team_a, result.team_b
        goals_a, goals_b = result.goals_a, result.goals_b

        # Update standings
        self.standings[team_a].played += 1
        self.standings[team_b].played += 1
        self.standings[team_a].goals_for += goals_a
        self.standings[team_a].goals_against += goals_b
        self.standings[team_b].goals_for += goals_b
        self.standings[team_b].goals_against += goals_a

        if goals_a > goals_b:
            self.standings[team_a].wins += 1
            self.standings[team_a].points += 3
            self.standings[team_b].losses += 1
        elif goals_b > goals_a:
            self.standings[team_b].wins += 1
            self.standings[team_b].points += 3
            self.standings[team_a].losses += 1
        else:
            self.standings[team_a].draws += 1
            self.standings[team_b].draws += 1
            self.standings[team_a].points += 1
            self.standings[team_b].points += 1

        # Record head-to-head
        key_ab = (team_a, team_b) if team_a < team_b else (team_b, team_a)
        if key_ab not in self.h2h_records:
            self.h2h_records[key_ab] = {}

        # Store result from team_a's perspective
        self.h2h_records[key_ab][team_a] = {
            'goals_for': goals_a,
            'goals_against': goals_b,
            'points': 3 if goals_a > goals_b else (1 if goals_a == goals_b else 0)
        }
        self.h2h_records[key_ab][team_b] = {
            'goals_for': goals_b,
            'goals_against': goals_a,
            'points': 3 if goals_b > goals_a else (1 if goals_a == goals_b else 0)
        }

    def simulate_matches(self) -> None:
        """Simulate all 6 matches in the group (each team plays others once)."""
        # All pairings
        pairings = list(combinations(self.teams, 2))

        for team_a, team_b in pairings:
            result = simulate_match(team_a, team_b, knockout=False)
            self._record_match(result)

    def _get_h2h_stats(self, tied_teams: List[str]) -> Dict[str, Dict]:
        """
        Calculate head-to-head statistics among tied teams.

        Returns dict: team -> {points, gd, gf}
        """
        h2h_stats = {team: {'points': 0, 'gd': 0, 'gf': 0} for team in tied_teams}

        # Only consider matches between tied teams
        for (team_a, team_b), records in self.h2h_records.items():
            if team_a in tied_teams and team_b in tied_teams:
                h2h_stats[team_a]['points'] += records[team_a]['points']
                h2h_stats[team_a]['gf'] += records[team_a]['goals_for']
                h2h_stats[team_a]['gd'] += records[team_a]['goals_for'] - records[team_a]['goals_against']

                h2h_stats[team_b]['points'] += records[team_b]['points']
                h2h_stats[team_b]['gf'] += records[team_b]['goals_for']
                h2h_stats[team_b]['gd'] += records[team_b]['goals_for'] - records[team_b]['goals_against']

        return h2h_stats

    def _break_tie(self, tied_teams: List[str]) -> List[str]:
        """
        Break a tie among teams using FIFA rules.

        Returns list of teams in ranked order.
        """
        if len(tied_teams) <= 1:
            return tied_teams

        # Step 1-3 already applied (points, GD, GF)
        # Now apply H2H

        h2h_stats = self._get_h2h_stats(tied_teams)

        def sort_key(team):
            s = self.standings[team]
            h = h2h_stats[team]
            # Primary: overall points (already equal by assumption)
            # Secondary: overall GD (already equal)
            # Tertiary: overall GF (already equal)
            # 4th: H2H points
            # 5th: H2H GD
            # 6th: H2H GF
            # 7th: Fair play (random for simulation)
            # 8th: FIFA ranking
            fair_play_random = random.random()  # Coin flip for fair play
            fifa_rank = self.simulator.get_fifa_rank(team)

            return (
                -s.points,
                -s.goal_difference,
                -s.goals_for,
                -h['points'],
                -h['gd'],
                -h['gf'],
                fair_play_random,  # Random breaks fair play ties
                fifa_rank,  # Lower is better
            )

        return sorted(tied_teams, key=sort_key)

    def get_final_standings(self) -> List[TeamStanding]:
        """
        Get final standings with all tiebreakers applied.

        Returns list of TeamStanding in order from 1st to 4th.
        """
        # First, sort by points, GD, GF
        teams = list(self.standings.keys())

        def primary_key(team):
            s = self.standings[team]
            return (-s.points, -s.goal_difference, -s.goals_for)

        teams.sort(key=primary_key)

        # Group teams with identical primary criteria
        final_order = []
        i = 0
        while i < len(teams):
            # Find all teams tied with teams[i]
            tied = [teams[i]]
            j = i + 1
            while j < len(teams):
                if primary_key(teams[i]) == primary_key(teams[j]):
                    tied.append(teams[j])
                    j += 1
                else:
                    break

            # Break tie among tied teams
            ranked_tied = self._break_tie(tied)
            final_order.extend(ranked_tied)

            i = j

        return [self.standings[team] for team in final_order]

    def simulate(self) -> GroupResult:
        """Run full group simulation and return results."""
        self.simulate_matches()
        standings = self.get_final_standings()

        return GroupResult(
            group_letter=self.group_letter,
            teams=self.teams,
            standings=standings,
            matches=self.matches,
            h2h_records=self.h2h_records,
        )


def simulate_group(group_letter: str, teams: List[str]) -> GroupResult:
    """Convenience function to simulate a single group."""
    sim = GroupSimulator(group_letter, teams)
    return sim.simulate()


def simulate_all_groups(groups: Dict[str, List[str]]) -> Dict[str, GroupResult]:
    """
    Simulate all groups.

    Args:
        groups: Dict mapping group letter to list of teams

    Returns:
        Dict mapping group letter to GroupResult
    """
    results = {}
    for letter, teams in groups.items():
        results[letter] = simulate_group(letter, teams)
    return results


def get_advancing_teams(group_results: Dict[str, GroupResult]) -> Dict[str, Dict[str, str]]:
    """
    Extract advancing teams from group results.

    Returns:
        Dict with:
        - 'winners': {group_letter: team_name}
        - 'runners_up': {group_letter: team_name}
        - 'third_place': {group_letter: TeamStanding} (for ranking)
    """
    winners = {}
    runners_up = {}
    third_place = {}

    for letter, result in group_results.items():
        standings = result.standings
        winners[letter] = standings[0].team
        runners_up[letter] = standings[1].team
        third_place[letter] = standings[2]  # Keep full standing for ranking

    return {
        'winners': winners,
        'runners_up': runners_up,
        'third_place': third_place,
    }


if __name__ == "__main__":
    # Test group simulation
    from .playoffs import get_playoff_qualified_groups

    print("Getting playoff-qualified groups...")
    groups = get_playoff_qualified_groups()

    print()
    print("Simulating all groups...")
    results = simulate_all_groups(groups)

    for letter in sorted(results.keys()):
        result = results[letter]
        print(f"\nGroup {letter}:")
        for i, standing in enumerate(result.standings, 1):
            print(f"  {i}. {standing}")

    print("\n" + "="*50)
    advancing = get_advancing_teams(results)
    print("\nAdvancing teams:")
    print("\nGroup Winners:")
    for letter, team in sorted(advancing['winners'].items()):
        print(f"  {letter}: {team}")

    print("\nRunners-up:")
    for letter, team in sorted(advancing['runners_up'].items()):
        print(f"  {letter}: {team}")

    print("\nThird-place teams:")
    for letter, standing in sorted(advancing['third_place'].items()):
        print(f"  {letter}: {standing}")
