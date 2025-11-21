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
    """

    uefa_group_winners_separated: bool = False
    uefa_playoffs_seeded: bool = False

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

        if not features:
            return "DrawConfig(default - all features off)"
        return f"DrawConfig({', '.join(features)})"
