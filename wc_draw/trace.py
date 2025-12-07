"""Trace logging for draw debugging.

This module provides detailed logging for debugging draw failures.
Enable trace logging to see every eligibility check and constraint evaluation.

Usage:
    from wc_draw.trace import trace, set_trace_enabled
    
    set_trace_enabled(True)  # Enable trace logging
    # ... run draw ...
    set_trace_enabled(False)  # Disable

Or use the context manager:
    with trace_context():
        # ... run draw with tracing ...
"""

import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TextIO

from .parser import Team


# Global trace state
_trace_enabled = False
_trace_output: TextIO = sys.stdout
_trace_indent = 0


def set_trace_enabled(enabled: bool) -> None:
    """Enable or disable trace logging."""
    global _trace_enabled
    _trace_enabled = enabled


def is_trace_enabled() -> bool:
    """Check if trace logging is enabled."""
    return _trace_enabled


def set_trace_output(output: TextIO) -> None:
    """Set the trace output stream."""
    global _trace_output
    _trace_output = output


@contextmanager  # noqa: E302
def trace_context(enabled: bool = True, output: Optional[TextIO] = None):
    """Context manager for trace logging."""
    global _trace_enabled, _trace_output
    old_enabled = _trace_enabled
    old_output = _trace_output
    try:
        _trace_enabled = enabled
        if output is not None:
            _trace_output = output
        yield
    finally:
        _trace_enabled = old_enabled
        _trace_output = old_output


def trace(msg: str, indent_delta: int = 0) -> None:
    """Log a trace message if tracing is enabled."""
    global _trace_indent
    if not _trace_enabled:
        return
    
    if indent_delta < 0:
        _trace_indent = max(0, _trace_indent + indent_delta)
    
    prefix = "  " * _trace_indent
    _trace_output.write(f"{prefix}{msg}\n")
    
    if indent_delta > 0:
        _trace_indent += indent_delta


def trace_start(msg: str) -> None:
    """Start a trace block with increased indent."""
    trace(msg, indent_delta=1)


def trace_end(msg: str = "") -> None:
    """End a trace block with decreased indent."""
    if msg:
        trace(msg, indent_delta=-1)
    else:
        global _trace_indent
        _trace_indent = max(0, _trace_indent - 1)


@dataclass
class EligibilityResult:
    """Result of an eligibility check with detailed breakdown."""
    
    team: str
    group: str
    eligible: bool
    
    # Basic checks
    pot_conflict: bool = False
    confederation_blocked: bool = False
    uefa_minimum_blocked: bool = False
    
    # Lookahead checks (which constraint blocked, if any)
    blocked_by: Optional[str] = None
    
    # Details for debugging
    group_teams: List[str] = field(default_factory=list)
    group_confederations: List[str] = field(default_factory=list)
    alternatives: int = 0
    
    def to_trace(self) -> str:
        """Format as trace message."""
        if self.eligible:
            return f"✓ {self.team} -> {self.group}: eligible"
        
        reason = "unknown"
        if self.pot_conflict:
            reason = "pot conflict"
        elif self.confederation_blocked:
            reason = "confederation limit"
        elif self.uefa_minimum_blocked:
            reason = "UEFA minimum"
        elif self.blocked_by:
            reason = f"blocked by {self.blocked_by}"
        
        return f"✗ {self.team} -> {self.group}: {reason}"


@dataclass
class PlacementEvent:
    """Record of a team placement."""
    
    pot: int
    step: int  # Step within pot (1-indexed)
    team: str
    confederation: str
    group: str
    eligible_groups: List[str]
    
    # State after placement
    groups_state: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_trace(self) -> str:
        """Format as trace message."""
        return (
            f"POT {self.pot} STEP {self.step}: {self.team} ({self.confederation}) -> {self.group} "
            f"(eligible: {', '.join(self.eligible_groups) or 'NONE'})"
        )


@dataclass
class ConstraintCheckResult:
    """Result of a single lookahead constraint check."""
    
    constraint: str  # e.g., "L9"
    constraint_name: str  # e.g., "caf_slots"
    passed: bool
    details: str = ""
    
    def to_trace(self) -> str:
        """Format as trace message."""
        status = "✓" if self.passed else "✗"
        msg = f"{status} {self.constraint} ({self.constraint_name})"
        if self.details:
            msg += f": {self.details}"
        return msg


class DrawTracer:
    """Collects trace events during a draw for later analysis."""
    
    def __init__(self):
        self.placements: List[PlacementEvent] = []
        self.failed_team: Optional[str] = None
        self.failed_group_checks: Dict[str, EligibilityResult] = {}
        
    def record_placement(self, event: PlacementEvent) -> None:
        """Record a successful placement."""
        self.placements.append(event)
        if is_trace_enabled():
            trace(event.to_trace())
    
    def record_failure(self, team: str, group_checks: Dict[str, EligibilityResult]) -> None:
        """Record a failed placement (no eligible groups)."""
        self.failed_team = team
        self.failed_group_checks = group_checks
        if is_trace_enabled():
            trace(f"FAILURE: {team} has no eligible groups")
            for group, result in sorted(group_checks.items()):
                trace(f"  {result.to_trace()}")
    
    def print_summary(self, output: TextIO = sys.stdout) -> None:
        """Print a summary of the draw attempt."""
        output.write("=" * 60 + "\n")
        output.write("DRAW TRACE SUMMARY\n")
        output.write("=" * 60 + "\n\n")
        
        # Print all placements by pot
        current_pot = 0
        for p in self.placements:
            if p.pot != current_pot:
                current_pot = p.pot
                output.write(f"\n--- POT {current_pot} ---\n")
            output.write(f"  {p.step}. {p.team} ({p.confederation}) -> {p.group}\n")
            output.write(f"     Eligible: {', '.join(p.eligible_groups)}\n")
        
        if self.failed_team:
            output.write(f"\n--- FAILURE ---\n")
            output.write(f"Team {self.failed_team} could not be placed\n\n")
            output.write("Group analysis:\n")
            for group, result in sorted(self.failed_group_checks.items()):
                output.write(f"  {group}: {result.to_trace()}\n")
                if result.group_teams:
                    output.write(f"     Teams: {', '.join(result.group_teams)}\n")


# Global tracer instance (can be replaced per-draw)
_current_tracer: Optional[DrawTracer] = None


def get_tracer() -> Optional[DrawTracer]:
    """Get the current draw tracer."""
    return _current_tracer


def set_tracer(tracer: Optional[DrawTracer]) -> None:
    """Set the current draw tracer."""
    global _current_tracer
    _current_tracer = tracer


@contextmanager
def tracer_context():
    """Context manager that creates and manages a DrawTracer."""
    global _current_tracer
    old_tracer = _current_tracer
    _current_tracer = DrawTracer()
    try:
        yield _current_tracer
    finally:
        _current_tracer = old_tracer


def format_group_state(groups: Dict[str, List[Team]]) -> str:
    """Format group state for trace output."""
    lines = []
    for g in sorted(groups.keys()):
        teams = groups[g]
        team_strs = [f"{t.name}({t.confederation})" for t in teams]
        lines.append(f"  {g}: {', '.join(team_strs) if team_strs else '(empty)'}")
    return "\n".join(lines)


def format_remaining_teams(teams: List[Team], by_pot: bool = True) -> str:
    """Format remaining teams for trace output."""
    if not teams:
        return "  (none)"
    
    if by_pot:
        by_pot_dict: Dict[int, List[str]] = {}
        for t in teams:
            by_pot_dict.setdefault(t.pot, []).append(f"{t.name}({t.confederation})")
        lines = []
        for pot in sorted(by_pot_dict.keys()):
            lines.append(f"  Pot {pot}: {', '.join(by_pot_dict[pot])}")
        return "\n".join(lines)
    else:
        return "  " + ", ".join(f"{t.name}({t.confederation})" for t in teams)
