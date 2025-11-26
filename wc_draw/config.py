"""Configuration for draw simulation behavior."""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class DrawConfig:
    """Configuration for draw simulation behavior.

    This class contains feature toggles that control how the draw simulation
    behaves. All features default to False (off) to maintain backward compatibility.

    Attributes:
        uefa_group_winners_separated: If True, UEFA qualifying group winners
            cannot be drawn together in the same World Cup group.
        uefa_playoffs_seeded: If True, UEFA playoff paths are seeded into pots
            based on the highest FIFA ranking of their candidate countries.
            If False, all playoff paths go to Pot 4 regardless of rankings.
        fifa_official_constraints: If True, applies the official FIFA draw
            procedure constraints as published. This includes:
            - Top 2 (Spain #1, Argentina #2) in opposite bracket halves
            - Seeds 3-4 (France #3, England #4) in opposite bracket halves
            - All top 4 must be in different quadrants
            - Non-top-4 cannot fill quadrants before top-4 placement
            The seeds 3-4 constraint prevents deadlock scenarios.
    """

    uefa_group_winners_separated: bool = False
    uefa_playoffs_seeded: bool = False
    fifa_official_constraints: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DrawConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def __str__(self) -> str:
        """Human-readable string representation."""
        features = []
        if self.uefa_group_winners_separated:
            features.append("UEFA group winners separated")
        if self.uefa_playoffs_seeded:
            features.append("UEFA playoffs seeded")
        if self.fifa_official_constraints:
            features.append("FIFA official constraints")

        if not features:
            return "DrawConfig(default - all features off)"
        return f"DrawConfig({', '.join(features)})"
