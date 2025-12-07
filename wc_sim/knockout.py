"""
Knockout bracket simulator for World Cup 2026.

Simulates the entire knockout stage from R32 through the final,
including the third-place match.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .config import (
    R32_BRACKET, R16_BRACKET, QF_BRACKET, SF_BRACKET,
    THIRD_PLACE_MATCH, FINAL_MATCH
)
from .match_engine import simulate_match, MatchResult
from .group_stage import GroupResult, TeamStanding
from .third_place import (
    rank_third_place_teams, get_advancing_thirds,
    get_r32_third_place_matchups
)


@dataclass
class KnockoutResult:
    """Result of a knockout match."""
    match_number: int
    team_a: str
    team_b: str
    winner: str
    loser: str
    match_result: MatchResult


@dataclass
class TournamentResult:
    """Complete tournament result."""
    champion: str
    runner_up: str
    third_place: str
    fourth_place: str
    semifinalists: List[str]  # Lost in SF (includes 3rd and 4th)
    quarterfinalists: List[str]  # Lost in QF
    r16_exits: List[str]  # Lost in R16
    r32_exits: List[str]  # Lost in R32
    group_exits: Dict[str, List[str]]  # {group: [4th place team]}
    third_place_eliminated: List[str]  # Third place teams that didn't advance

    # Full bracket for detailed tracking
    r32_results: Dict[int, KnockoutResult]
    r16_results: Dict[int, KnockoutResult]
    qf_results: Dict[int, KnockoutResult]
    sf_results: Dict[int, KnockoutResult]
    third_place_result: KnockoutResult
    final_result: KnockoutResult


class KnockoutSimulator:
    """
    Simulates the knockout stage of the tournament.
    """

    def __init__(self, group_results: Dict[str, GroupResult]):
        self.group_results = group_results
        self._extract_advancing_teams()

    def _extract_advancing_teams(self) -> None:
        """Extract winners, runners-up, and third-place teams from groups."""
        self.winners = {}
        self.runners_up = {}
        self.third_place = {}

        for letter, result in self.group_results.items():
            standings = result.standings
            self.winners[letter] = standings[0].team
            self.runners_up[letter] = standings[1].team
            self.third_place[letter] = standings[2]  # Full standing for ranking

        # Rank third-place teams
        self.ranked_thirds = rank_third_place_teams(self.third_place)
        self.advancing_thirds = get_advancing_thirds(self.ranked_thirds)
        self.eliminated_thirds = [s.team for _, s in self.ranked_thirds[8:]]

        # Get R32 matchups for third-place teams
        self.third_place_matchups = get_r32_third_place_matchups(
            self.advancing_thirds,
            self.winners,
            self.runners_up
        )

    def _get_r32_matchups(self) -> Dict[int, Tuple[str, str]]:
        """Build complete R32 matchups."""
        matchups = {}

        # Matches 73-80: Group winners vs runners-up
        for match_num, (team_a_id, team_b_id) in R32_BRACKET.items():
            if match_num <= 80:
                # Direct group winner vs runner-up matches
                # team_a_id format: "1A" or "2A"
                if team_a_id.startswith('1'):
                    group_a = team_a_id[1]
                    team_a = self.winners[group_a]
                else:
                    group_a = team_a_id[1]
                    team_a = self.runners_up[group_a]

                if team_b_id.startswith('1'):
                    group_b = team_b_id[1]
                    team_b = self.winners[group_b]
                else:
                    group_b = team_b_id[1]
                    team_b = self.runners_up[group_b]

                matchups[match_num] = (team_a, team_b)

        # Matches 81-88: Include third-place teams from our assignment
        for match_num, (opponent, third) in self.third_place_matchups.items():
            matchups[match_num] = (opponent, third)

        return matchups

    def simulate_round(self, matchups: Dict[int, Tuple[str, str]]) -> Dict[int, KnockoutResult]:
        """Simulate a round of knockout matches."""
        results = {}

        for match_num, (team_a, team_b) in matchups.items():
            match_result = simulate_match(team_a, team_b, knockout=True)
            winner = match_result.winner
            loser = match_result.loser

            results[match_num] = KnockoutResult(
                match_number=match_num,
                team_a=team_a,
                team_b=team_b,
                winner=winner,
                loser=loser,
                match_result=match_result,
            )

        return results

    def _build_next_round_matchups(
        self,
        bracket: Dict[int, Tuple[int, int]],
        previous_results: Dict[int, KnockoutResult]
    ) -> Dict[int, Tuple[str, str]]:
        """Build matchups for next round based on previous round winners."""
        matchups = {}

        for match_num, (prev_a, prev_b) in bracket.items():
            team_a = previous_results[prev_a].winner
            team_b = previous_results[prev_b].winner
            matchups[match_num] = (team_a, team_b)

        return matchups

    def simulate(self) -> TournamentResult:
        """Simulate the entire knockout stage."""
        # R32
        r32_matchups = self._get_r32_matchups()
        r32_results = self.simulate_round(r32_matchups)
        r32_exits = [r.loser for r in r32_results.values()]

        # R16
        r16_matchups = self._build_next_round_matchups(R16_BRACKET, r32_results)
        r16_results = self.simulate_round(r16_matchups)
        r16_exits = [r.loser for r in r16_results.values()]

        # Quarterfinals
        qf_matchups = self._build_next_round_matchups(QF_BRACKET, r16_results)
        qf_results = self.simulate_round(qf_matchups)
        qf_exits = [r.loser for r in qf_results.values()]

        # Semifinals
        sf_matchups = self._build_next_round_matchups(SF_BRACKET, qf_results)
        sf_results = self.simulate_round(sf_matchups)

        # Get SF losers (for 3rd place match)
        sf_losers = [r.loser for r in sf_results.values()]
        sf_winners = [r.winner for r in sf_results.values()]

        # Third-place match
        third_match = simulate_match(sf_losers[0], sf_losers[1], knockout=True)
        third_place_result = KnockoutResult(
            match_number=103,
            team_a=sf_losers[0],
            team_b=sf_losers[1],
            winner=third_match.winner,
            loser=third_match.loser,
            match_result=third_match,
        )

        # Final
        final_match = simulate_match(sf_winners[0], sf_winners[1], knockout=True)
        final_result = KnockoutResult(
            match_number=104,
            team_a=sf_winners[0],
            team_b=sf_winners[1],
            winner=final_match.winner,
            loser=final_match.loser,
            match_result=final_match,
        )

        # Get group 4th place exits
        group_exits = {}
        for letter, result in self.group_results.items():
            fourth = result.standings[3].team
            group_exits[letter] = [fourth]

        return TournamentResult(
            champion=final_result.winner,
            runner_up=final_result.loser,
            third_place=third_place_result.winner,
            fourth_place=third_place_result.loser,
            semifinalists=sf_losers,
            quarterfinalists=qf_exits,
            r16_exits=r16_exits,
            r32_exits=r32_exits,
            group_exits=group_exits,
            third_place_eliminated=self.eliminated_thirds,
            r32_results=r32_results,
            r16_results=r16_results,
            qf_results=qf_results,
            sf_results=sf_results,
            third_place_result=third_place_result,
            final_result=final_result,
        )


def simulate_knockout(group_results: Dict[str, GroupResult]) -> TournamentResult:
    """Convenience function to simulate knockout stage."""
    sim = KnockoutSimulator(group_results)
    return sim.simulate()


if __name__ == "__main__":
    from .playoffs import get_playoff_qualified_groups
    from .group_stage import simulate_all_groups

    print("Simulating playoffs...")
    groups = get_playoff_qualified_groups()

    print("Simulating group stage...")
    group_results = simulate_all_groups(groups)

    print("Simulating knockout stage...")
    result = simulate_knockout(group_results)

    print("\n" + "=" * 60)
    print("TOURNAMENT RESULTS")
    print("=" * 60)

    print(f"\n🏆 CHAMPION: {result.champion}")
    print(f"🥈 Runner-up: {result.runner_up}")
    print(f"🥉 Third place: {result.third_place}")
    print(f"4th place: {result.fourth_place}")

    print(f"\nSemifinalists (lost in SF): {', '.join(result.semifinalists)}")
    print(f"Quarterfinalists (lost in QF): {', '.join(result.quarterfinalists)}")
    print(f"R16 exits: {', '.join(result.r16_exits)}")
    print(f"R32 exits: {', '.join(result.r32_exits)}")
    print(f"Third-place eliminated: {', '.join(result.third_place_eliminated)}")

    print("\nGroup 4th place (group stage exit):")
    for letter in sorted(result.group_exits.keys()):
        print(f"  Group {letter}: {', '.join(result.group_exits[letter])}")

    print("\n" + "-" * 60)
    print("KNOCKOUT BRACKET")
    print("-" * 60)

    print("\nR32 Results:")
    for match_num in sorted(result.r32_results.keys()):
        r = result.r32_results[match_num]
        mr = r.match_result
        et = " (aet)" if mr.extra_time else ""
        pk = " (pen)" if mr.penalties else ""
        print(f"  M{match_num}: {r.team_a} {mr.goals_a}-{mr.goals_b} {r.team_b}{et}{pk} -> {r.winner}")

    print("\nR16 Results:")
    for match_num in sorted(result.r16_results.keys()):
        r = result.r16_results[match_num]
        mr = r.match_result
        et = " (aet)" if mr.extra_time else ""
        pk = " (pen)" if mr.penalties else ""
        print(f"  M{match_num}: {r.team_a} {mr.goals_a}-{mr.goals_b} {r.team_b}{et}{pk} -> {r.winner}")

    print("\nQuarterfinal Results:")
    for match_num in sorted(result.qf_results.keys()):
        r = result.qf_results[match_num]
        mr = r.match_result
        et = " (aet)" if mr.extra_time else ""
        pk = " (pen)" if mr.penalties else ""
        print(f"  M{match_num}: {r.team_a} {mr.goals_a}-{mr.goals_b} {r.team_b}{et}{pk} -> {r.winner}")

    print("\nSemifinal Results:")
    for match_num in sorted(result.sf_results.keys()):
        r = result.sf_results[match_num]
        mr = r.match_result
        et = " (aet)" if mr.extra_time else ""
        pk = " (pen)" if mr.penalties else ""
        print(f"  M{match_num}: {r.team_a} {mr.goals_a}-{mr.goals_b} {r.team_b}{et}{pk} -> {r.winner}")

    print("\nThird Place Match:")
    r = result.third_place_result
    mr = r.match_result
    et = " (aet)" if mr.extra_time else ""
    pk = " (pen)" if mr.penalties else ""
    print(f"  {r.team_a} {mr.goals_a}-{mr.goals_b} {r.team_b}{et}{pk} -> {r.winner}")

    print("\nFinal:")
    r = result.final_result
    mr = r.match_result
    et = " (aet)" if mr.extra_time else ""
    pk = " (pen)" if mr.penalties else ""
    print(f"  {r.team_a} {mr.goals_a}-{mr.goals_b} {r.team_b}{et}{pk} -> {r.winner} 🏆")
