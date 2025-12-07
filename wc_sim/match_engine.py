"""
Match simulation engine using Elo ratings and Poisson goal distribution.

This module provides the core match simulation functionality:
1. Convert Elo ratings to expected goals
2. Simulate match outcomes using Poisson distribution
3. Handle extra time and penalties for knockout matches
"""

import json
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
from scipy import stats

from .config import ELO_SCALE, AVG_GOALS, HOME_ADVANTAGE, ELO_RATINGS_FILE


@dataclass
class MatchResult:
    """Result of a single match simulation."""
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    extra_time: bool = False
    penalties: bool = False
    penalty_winner: Optional[str] = None

    @property
    def winner(self) -> Optional[str]:
        """Return winner or None for draw (group stage only)."""
        if self.goals_a > self.goals_b:
            return self.team_a
        elif self.goals_b > self.goals_a:
            return self.team_b
        elif self.penalties and self.penalty_winner:
            return self.penalty_winner
        return None

    @property
    def loser(self) -> Optional[str]:
        """Return loser or None for draw."""
        if self.goals_a > self.goals_b:
            return self.team_b
        elif self.goals_b > self.goals_a:
            return self.team_a
        elif self.penalties and self.penalty_winner:
            return self.team_a if self.penalty_winner == self.team_b else self.team_b
        return None


class GoalModel(ABC):
    """Abstract base class for goal simulation models."""

    @abstractmethod
    def expected_goals(self, elo_a: float, elo_b: float) -> Tuple[float, float]:
        """Calculate expected goals for each team based on ratings."""
        pass

    @abstractmethod
    def simulate_goals(self, expected_a: float, expected_b: float) -> Tuple[int, int]:
        """Simulate actual goals scored using expected values."""
        pass


class PoissonGoalModel(GoalModel):
    """
    Poisson-based goal model using Elo ratings.

    Expected goals are derived from the Elo win expectancy formula,
    scaled to produce realistic goal distributions.
    """

    def __init__(self, avg_goals: float = AVG_GOALS, home_advantage: float = HOME_ADVANTAGE):
        self.avg_goals = avg_goals
        self.home_advantage = home_advantage

    def _win_expectancy(self, elo_diff: float) -> float:
        """
        Calculate win expectancy from Elo difference.

        We = 1 / (1 + 10^(-dr/400))
        """
        return 1.0 / (1.0 + 10 ** (-elo_diff / ELO_SCALE))

    def expected_goals(self, elo_a: float, elo_b: float) -> Tuple[float, float]:
        """
        Convert Elo ratings to expected goals.

        Higher Elo differential means the better team is expected to score more
        and concede less. We scale around the average goals per team.
        """
        elo_diff = elo_a - elo_b

        # Win expectancy for team A
        we_a = self._win_expectancy(elo_diff + self.home_advantage)
        we_b = 1.0 - we_a

        # Scale expected goals based on win expectancy
        # If we_a = 0.5 (equal teams), both get avg_goals
        # If we_a = 0.7, team A gets more, team B gets less
        # Using a formula that preserves total expected goals around 2*avg_goals

        total_goals = 2 * self.avg_goals

        # Distribute total goals based on win expectancy
        # But also factor in defensive strength (better teams concede less)
        attack_factor_a = 0.5 + (we_a - 0.5) * 0.8  # How much of attack goes to A
        attack_factor_b = 1.0 - attack_factor_a

        xg_a = total_goals * attack_factor_a
        xg_b = total_goals * attack_factor_b

        # Ensure minimum expected goals (teams rarely shut out completely)
        xg_a = max(0.3, xg_a)
        xg_b = max(0.3, xg_b)

        return xg_a, xg_b

    def simulate_goals(self, expected_a: float, expected_b: float) -> Tuple[int, int]:
        """Simulate goals using Poisson distribution."""
        goals_a = np.random.poisson(expected_a)
        goals_b = np.random.poisson(expected_b)
        return int(goals_a), int(goals_b)


class MatchSimulator:
    """
    Main match simulation class.

    Handles loading Elo ratings and simulating matches with various
    options for group stage vs knockout matches.
    """

    def __init__(self, goal_model: Optional[GoalModel] = None):
        self.goal_model = goal_model or PoissonGoalModel()
        self._elo_ratings: Dict[str, Dict] = {}
        self._load_elo_ratings()

    def _load_elo_ratings(self) -> None:
        """Load Elo ratings from JSON file."""
        if ELO_RATINGS_FILE.exists():
            with open(ELO_RATINGS_FILE, 'r') as f:
                data = json.load(f)
                self._elo_ratings = data.get('teams', {})

    def get_elo(self, team: str) -> float:
        """Get Elo rating for a team."""
        if team in self._elo_ratings:
            return float(self._elo_ratings[team]['elo'])
        # Default rating for unknown teams
        return 1500.0

    def get_fifa_rank(self, team: str) -> int:
        """Get FIFA ranking for a team (used for tiebreakers)."""
        if team in self._elo_ratings:
            return self._elo_ratings[team].get('fifa_rank', 999)
        return 999

    def simulate_group_match(self, team_a: str, team_b: str) -> MatchResult:
        """
        Simulate a group stage match.

        Group matches can end in a draw (no extra time/penalties).
        """
        elo_a = self.get_elo(team_a)
        elo_b = self.get_elo(team_b)

        xg_a, xg_b = self.goal_model.expected_goals(elo_a, elo_b)
        goals_a, goals_b = self.goal_model.simulate_goals(xg_a, xg_b)

        return MatchResult(
            team_a=team_a,
            team_b=team_b,
            goals_a=goals_a,
            goals_b=goals_b,
        )

    def simulate_knockout_match(self, team_a: str, team_b: str) -> MatchResult:
        """
        Simulate a knockout match.

        If tied after regular time, goes to extra time then penalties.
        """
        elo_a = self.get_elo(team_a)
        elo_b = self.get_elo(team_b)

        xg_a, xg_b = self.goal_model.expected_goals(elo_a, elo_b)
        goals_a, goals_b = self.goal_model.simulate_goals(xg_a, xg_b)

        extra_time = False
        penalties = False
        penalty_winner = None

        if goals_a == goals_b:
            # Extra time - reduced expected goals (30 mins vs 90)
            extra_time = True
            et_factor = 0.33  # 30 mins is 1/3 of 90 mins

            et_xg_a, et_xg_b = xg_a * et_factor, xg_b * et_factor
            et_goals_a, et_goals_b = self.goal_model.simulate_goals(et_xg_a, et_xg_b)

            goals_a += et_goals_a
            goals_b += et_goals_b

            if goals_a == goals_b:
                # Penalties - slightly favor better team
                penalties = True
                we_a = 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / ELO_SCALE))
                # Penalty shootouts are relatively random - compress toward 50/50
                penalty_prob_a = 0.5 + (we_a - 0.5) * 0.2

                if random.random() < penalty_prob_a:
                    penalty_winner = team_a
                else:
                    penalty_winner = team_b

        return MatchResult(
            team_a=team_a,
            team_b=team_b,
            goals_a=goals_a,
            goals_b=goals_b,
            extra_time=extra_time,
            penalties=penalties,
            penalty_winner=penalty_winner,
        )


# Create a default simulator instance for convenience
_default_simulator: Optional[MatchSimulator] = None


def get_simulator() -> MatchSimulator:
    """Get or create the default match simulator."""
    global _default_simulator
    if _default_simulator is None:
        _default_simulator = MatchSimulator()
    return _default_simulator


def simulate_match(team_a: str, team_b: str, knockout: bool = False) -> MatchResult:
    """
    Convenience function to simulate a match.

    Args:
        team_a: First team name
        team_b: Second team name
        knockout: If True, use knockout rules (extra time, penalties)

    Returns:
        MatchResult with the outcome
    """
    sim = get_simulator()
    if knockout:
        return sim.simulate_knockout_match(team_a, team_b)
    return sim.simulate_group_match(team_a, team_b)
