"""
Monte Carlo tournament simulator.

Runs many simulations of the World Cup and aggregates probabilities
for each team's outcomes.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set
from tqdm import tqdm

from .config import GROUPS, NUM_SIMULATIONS, OUTCOME_LABELS, SIMULATION_RESULTS_FILE, PLAYOFF_TEAM_GROUPS
from .playoffs import simulate_all_playoffs, replace_playoff_placeholders
from .group_stage import simulate_all_groups
from .knockout import simulate_knockout, TournamentResult


@dataclass
class TeamOutcome:
    """Outcome probabilities for a single team."""
    team: str
    group: Optional[str]
    confederation: str
    simulations: int
    outcomes: Dict[str, int]  # outcome_label -> count

    @property
    def probabilities(self) -> Dict[str, float]:
        """Convert counts to probabilities."""
        return {k: v / self.simulations for k, v in self.outcomes.items()}

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            'team': self.team,
            'group': self.group,
            'confederation': self.confederation,
            'simulations': self.simulations,
            'outcome_counts': self.outcomes,
            'outcome_probabilities': self.probabilities,
        }


class MonteCarloSimulator:
    """
    Runs Monte Carlo simulations of the World Cup.
    """

    def __init__(self, num_simulations: int = NUM_SIMULATIONS):
        self.num_simulations = num_simulations
        self.outcomes: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.team_groups: Dict[str, Optional[str]] = {}  # Maps team -> group (None for playoff teams)
        self.team_confederations: Dict[str, str] = {}

        # Load team confederations from Elo data
        self._load_team_data()

    def _load_team_data(self) -> None:
        """Load team confederation data from Elo ratings file."""
        from .match_engine import get_simulator
        sim = get_simulator()

        for team, data in sim._elo_ratings.items():
            self.team_confederations[team] = data.get('confederation', 'Unknown')
        
        # Pre-populate groups for playoff teams (they have a known target group)
        for team, group in PLAYOFF_TEAM_GROUPS.items():
            self.team_groups[team] = group

    def _record_tournament_result(self, result: TournamentResult, groups: Dict[str, List[str]]) -> None:
        """Record outcomes from a single tournament simulation."""
        # Record group assignments for all teams
        for letter, teams in groups.items():
            for team in teams:
                if team not in self.team_groups:
                    self.team_groups[team] = letter

        # Champion
        self.outcomes[result.champion]['Winner'] += 1

        # Runner-up
        self.outcomes[result.runner_up]['Runner-up'] += 1

        # Third place
        self.outcomes[result.third_place]['3rd Place'] += 1

        # Fourth place
        self.outcomes[result.fourth_place]['4th Place'] += 1

        # SF exits (not counting 3rd/4th who already have their outcomes)
        # Note: semifinalists list includes 3rd and 4th place teams
        # We already recorded them, so we track "SF Exit" separately if needed

        # QF exits
        for team in result.quarterfinalists:
            self.outcomes[team]['QF Exit'] += 1

        # R16 exits
        for team in result.r16_exits:
            self.outcomes[team]['R16 Exit'] += 1

        # R32 exits
        for team in result.r32_exits:
            self.outcomes[team]['R32 Exit'] += 1

        # Third-place eliminated (didn't make knockout)
        for team in result.third_place_eliminated:
            self.outcomes[team]['Group 3rd'] += 1

        # Group 4th place (didn't make knockout)
        for letter, teams in result.group_exits.items():
            for team in teams:
                self.outcomes[team]['Group 4th'] += 1

        # Record group positions for advancing teams
        # Need to determine group positions from group results
        for letter, group_result in result.r32_results.items():
            pass  # Group positions already implicit from the above

        # Actually track group positions more precisely
        # The GroupResult is in knockout.py but we need to access it
        # For now, we track based on outcome

    def _record_group_positions(self, group_results: Dict, groups: Dict[str, List[str]]) -> None:
        """Record group stage positions for all teams."""
        for letter, result in group_results.items():
            standings = result.standings
            # 1st place
            self.outcomes[standings[0].team]['Group 1st'] += 1
            # 2nd place
            self.outcomes[standings[1].team]['Group 2nd'] += 1
            # 3rd and 4th are tracked in _record_tournament_result

    def _record_playoff_losers(self, losers: List[str]) -> None:
        """Record 'Did Not Qualify' for teams that lost their playoff."""
        for team in losers:
            self.outcomes[team]['Did Not Qualify'] += 1
            # Also set their group to None (they never made it to a group)
            if team not in self.team_groups:
                self.team_groups[team] = None

    def simulate_one(self) -> TournamentResult:
        """Run a single tournament simulation."""
        # Simulate playoffs to determine final 48 teams
        playoff_result = simulate_all_playoffs()
        groups = replace_playoff_placeholders(GROUPS, playoff_result)

        # Record playoff losers as "Did Not Qualify"
        self._record_playoff_losers(playoff_result.losers)

        # Simulate group stage
        group_results = simulate_all_groups(groups)

        # Record group positions
        self._record_group_positions(group_results, groups)

        # Simulate knockout stage
        result = simulate_knockout(group_results)

        # Record tournament outcomes
        self._record_tournament_result(result, groups)

        return result

    def run(self, show_progress: bool = True) -> Dict[str, TeamOutcome]:
        """
        Run all simulations and return aggregated outcomes.

        Args:
            show_progress: Whether to show a progress bar

        Returns:
            Dict mapping team name to TeamOutcome
        """
        iterator = range(self.num_simulations)
        if show_progress:
            iterator = tqdm(iterator, desc="Simulating tournaments")

        for _ in iterator:
            self.simulate_one()

        # Build TeamOutcome objects
        results = {}
        for team, outcome_counts in self.outcomes.items():
            group = self.team_groups.get(team)
            confed = self.team_confederations.get(team, 'Unknown')

            results[team] = TeamOutcome(
                team=team,
                group=group,
                confederation=confed,
                simulations=self.num_simulations,
                outcomes=dict(outcome_counts),
            )

        return results

    def save_results(self, results: Dict[str, TeamOutcome], filepath: Optional[Path] = None) -> None:
        """Save simulation results to JSON file."""
        filepath = filepath or SIMULATION_RESULTS_FILE

        output = {
            'num_simulations': self.num_simulations,
            'teams': {team: outcome.to_dict() for team, outcome in results.items()},
        }

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Results saved to {filepath}")


def run_simulation(
    num_simulations: int = NUM_SIMULATIONS,
    show_progress: bool = True,
    save: bool = True,
) -> Dict[str, TeamOutcome]:
    """
    Convenience function to run Monte Carlo simulation.

    Args:
        num_simulations: Number of tournaments to simulate
        show_progress: Whether to show progress bar
        save: Whether to save results to file

    Returns:
        Dict mapping team name to TeamOutcome
    """
    sim = MonteCarloSimulator(num_simulations)
    results = sim.run(show_progress)

    if save:
        sim.save_results(results)

    return results


def print_summary(results: Dict[str, TeamOutcome]) -> None:
    """Print a summary of simulation results."""
    print("\n" + "=" * 80)
    print("WORLD CUP 2026 SIMULATION RESULTS")
    print("=" * 80)

    num_sims = next(iter(results.values())).simulations
    print(f"\nBased on {num_sims:,} simulations\n")

    # Sort by win probability
    by_win_prob = sorted(
        results.items(),
        key=lambda x: x[1].probabilities.get('Winner', 0),
        reverse=True
    )

    print("Top 20 teams by Win Probability:")
    print("-" * 80)
    print(f"{'Rank':<5} {'Team':<20} {'Win%':>7} {'Final%':>8} {'SF%':>8} {'QF%':>8} {'R16%':>8}")
    print("-" * 80)

    for i, (team, outcome) in enumerate(by_win_prob[:20], 1):
        probs = outcome.probabilities
        win = probs.get('Winner', 0) * 100
        final = (probs.get('Winner', 0) + probs.get('Runner-up', 0)) * 100
        sf = final + (probs.get('3rd Place', 0) + probs.get('4th Place', 0)) * 100
        qf = sf + probs.get('QF Exit', 0) * 100
        r16 = qf + probs.get('R16 Exit', 0) * 100

        print(f"{i:<5} {team:<20} {win:>6.1f}% {final:>7.1f}% {sf:>7.1f}% {qf:>7.1f}% {r16:>7.1f}%")

    print("\n")

    # Group stage exit probabilities for notable teams
    print("Teams with highest group stage exit probability:")
    print("-" * 60)

    group_exit_prob = []
    for team, outcome in results.items():
        probs = outcome.probabilities
        exit_prob = probs.get('Group 3rd', 0) + probs.get('Group 4th', 0)
        if exit_prob > 0.2:  # At least 20% chance
            group_exit_prob.append((team, exit_prob, outcome.group))

    group_exit_prob.sort(key=lambda x: -x[1])

    for team, prob, group in group_exit_prob[:15]:
        print(f"  {team:<25} Group {group}: {prob*100:>5.1f}% exit chance")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run World Cup Monte Carlo simulation")
    parser.add_argument(
        "-n", "--num-simulations",
        type=int,
        default=NUM_SIMULATIONS,
        help=f"Number of simulations to run (default: {NUM_SIMULATIONS})"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Don't show progress bar"
    )

    args = parser.parse_args()

    results = run_simulation(
        num_simulations=args.num_simulations,
        show_progress=not args.quiet,
        save=not args.no_save,
    )

    print_summary(results)
