# Feature Toggle Implementation Plan

## Overview
Add two configurable behaviors to the draw simulation:
1. **UEFA Qualifying Group Winner Constraint**: UEFA qualifying group winners cannot be drawn together in the same World Cup group
2. **UEFA Playoff Seeding**: Playoff paths may be seeded in higher pots based on FIFA rankings

## Phase 1: Feature Toggle Framework

### Task 1.1: Create DrawConfig dataclass
**File**: `wc_draw/config.py` (new)

```python
@dataclass
class DrawConfig:
    """Configuration for draw simulation behavior."""
    
    # UEFA qualifying group winner constraint
    uefa_group_winners_separated: bool = False
    
    # UEFA playoff seeding based on FIFA rankings
    uefa_playoffs_seeded: bool = False
    
    # Future toggles can be added here
    # e.g., host_country_groups: bool = True
```

**Benefits**:
- Single source of truth for all feature toggles
- Easy to extend with new features
- Can be serialized for reproducibility

---

## Phase 2: Data Model Updates

### Task 2.1: Add FIFA ranking to Team dataclass
**File**: `wc_draw/parser.py`

Update `Team` dataclass:
```python
@dataclass
class Team:
    name: str
    confederation: str
    pot: int  # Will become computed, not parsed
    host: bool
    fixed_group: Optional[str]
    flag: Optional[str]
    candidates: List[str]
    fifa_ranking: int  # NEW: FIFA world ranking
    uefa_group_winner: bool = False  # NEW: Won a UEFA qualifying group
```

### Task 2.2: Update teams.csv schema
**File**: `teams.csv`

New columns (order matters):
```
name,confederation,pot,host,fixed_group,flag,candidates,fifa_ranking,uefa_group_winner
```

Example rows:
```
England,UEFA,1,false,,,🏴󠁧󠁢󠁥󠁮󠁧󠁿,5,true
Scotland,UEFA,4,false,,,🏴󠁧󠁢󠁳󠁣󠁴󠁿,39,false
UEFA Playoff A,UEFA,4,false,,,🏴󠁧󠁢󠁥󠁮󠁧󠁿/🇮🇹,Wales;Italy,12,false
```

**Notes**:
- Hosts get ranking but it's not used for pot assignment
- Playoff paths get the highest ranking from their candidates
- Only direct qualifiers can be group winners (playoff teams cannot be)

### Task 2.3: Update parse_teams_config()
**File**: `wc_draw/parser.py`

```python
def parse_teams_config(filepath: str) -> dict[int, List[Team]]:
    # Parse new columns: fifa_ranking, uefa_group_winner
    # Handle backward compatibility (old CSV format without new columns)
    # Validate: fifa_ranking > 0
```

---

## Phase 3: Dynamic Pot Assignment

### Task 3.1: Create pot assignment function
**File**: `wc_draw/pot_assignment.py` (new)

```python
def assign_pots(
    teams: List[Team], 
    config: DrawConfig
) -> dict[int, List[Team]]:
    """
    Assign teams to pots based on FIFA rankings and configuration.
    
    Logic:
    1. Hosts always go to Pot 1 (up to 3 hosts)
    2. If uefa_playoffs_seeded=False:
       - Sort all non-host, non-playoff teams by fifa_ranking (lower is better)
       - Assign top (12 - num_hosts) to Pot 1, next 12 to Pot 2, next 12 to Pot 3
       - All playoff paths go to Pot 4 (regardless of candidate ranking)
    3. If uefa_playoffs_seeded=True:
       - UEFA playoff paths are assigned pots based on their highest ranked candidate
       - All teams/slots sorted by FIFA ranking for pot assignment
    
    Returns:
        Dictionary mapping pot number (1-4) to list of teams
    """
```

### Task 3.2: Refactor parse_teams_config
**File**: `wc_draw/parser.py`

```python
def parse_teams_config(filepath: str, config: Optional[DrawConfig] = None) -> dict[int, List[Team]]:
    """
    Parse teams CSV and assign pots dynamically if config provided.
    
    If config is None, use pot column from CSV (legacy behavior).
    If config is provided, ignore pot column and compute pots via assign_pots().
    """
```

---

## Phase 4: UEFA Group Winner Constraint

### Task 4.1: Update eligible_for_group logic
**File**: `wc_draw/draw.py`

```python
def eligible_for_group(
    team: Team, 
    group_teams: List[Team], 
    config: DrawConfig
) -> bool:
    """
    Check if team can be placed in group.
    
    Existing checks:
    - Confederation limits (UEFA ≤2, others ≤1)
    - Placeholder multi-confederation handling
    - Fixed group assignments
    
    NEW check (if config.uefa_group_winners_separated):
    - If team is a UEFA group winner, check that no other UEFA group winner
      is already in the group (regardless of which qualifying groups they won)
    """
```

### Task 4.2: Helper function for UEFA group winner check
**File**: `wc_draw/draw.py`

```python
def _check_uefa_group_winner_constraint(
    team: Team,
    group_teams: List[Team]
) -> bool:
    """
    Return True if team can be placed without violating UEFA group winner rule.
    
    Rule: At most one UEFA qualifying group winner per World Cup group.
    
    If the team being placed is a UEFA group winner, ensure no other 
    UEFA group winner is already in the group.
    """
    if not team.uefa_group_winner:
        return True
    
    # Check if any existing team is also a UEFA group winner
    for existing in group_teams:
        if existing.uefa_group_winner:
            return False
    
    return True
```

---

## Phase 5: Draw Function Integration

### Task 5.1: Update draw_pot1, draw_pot signatures
**File**: `wc_draw/draw.py`

```python
def draw_pot1(
    teams: List[Team],
    slots: List[Slot],
    groups: Dict[str, List[Team]],
    config: DrawConfig,  # NEW
    rng: Optional[random.Random] = None
) -> Dict[str, List[Team]]:
    # Pass config to eligible_for_group calls
```

### Task 5.2: Update run_full_draw signature
**File**: `wc_draw/draw.py`

```python
def run_full_draw(
    pots: Dict[int, List[Team]],
    seed: Optional[int] = None,
    max_attempts: int = 500,
    report_fallbacks: bool = False,
    config: Optional[DrawConfig] = None,  # NEW
):
    """
    If config is None, use default DrawConfig (all features off).
    """
    if config is None:
        config = DrawConfig()
```

---

## Phase 6: CLI Integration

### Task 6.1: Add CLI arguments
**File**: `wc_draw/cli.py`

```python
parser.add_argument(
    "--uefa-group-winners-separated",
    action="store_true",
    help="Prevent UEFA qualifying group winners from same group being drawn together"
)

parser.add_argument(
    "--uefa-playoffs-seeded",
    action="store_true",
    help="Seed UEFA playoff paths based on highest FIFA ranking of candidates"
)

# Build config from args
config = DrawConfig(
    uefa_group_winners_separated=args.uefa_group_winners_separated,
    uefa_playoffs_seeded=args.uefa_playoffs_seeded,
)

# Parse teams with config
pots = parse_teams_config(args.teams, config)

# Run draw with config
groups, seed = run_full_draw(pots, seed=args.seed, config=config)
```

---

## Phase 7: Testing

### Task 7.1: Add config tests
**File**: `tests/test_config.py` (new)

```python
def test_default_config():
    """Test default DrawConfig has all features disabled."""
    
def test_config_serialization():
    """Test DrawConfig can be converted to/from dict for JSON storage."""
```

### Task 7.2: Add pot assignment tests
**File**: `tests/test_pot_assignment.py` (new)

```python
def test_pot_assignment_legacy_mode():
    """When uefa_playoffs_seeded=False, verify correct pot assignment."""
    
def test_pot_assignment_with_playoff_seeding():
    """When uefa_playoffs_seeded=True, verify playoff paths get correct pots."""
    
def test_hosts_always_pot1():
    """Regardless of FIFA ranking, hosts go to Pot 1."""
```

### Task 7.3: Add UEFA group winner constraint tests
**File**: `tests/test_uefa_group_winners.py` (new)

```python
def test_uefa_group_winners_can_be_separated():
    """When constraint enabled, only one UEFA group winner per World Cup group."""
    
def test_uefa_group_winners_constraint_disabled():
    """When constraint disabled, multiple UEFA group winners can be in same group."""
```

### Task 7.4: Update existing tests
**Files**: `tests/test_draw_*.py`, `tests/test_run_full_draw_harness.py`

- Pass `DrawConfig()` (default) to maintain existing behavior
- Update integration test to test both modes

---

## Phase 8: Scanner & Stats Integration

### Task 8.1: Update seed_scan_large.py
**File**: `scripts/seed_scan_large.py`

```python
parser.add_argument("--uefa-group-winners-separated", action="store_true")
parser.add_argument("--uefa-playoffs-seeded", action="store_true")

# Build config
config = DrawConfig(
    uefa_group_winners_separated=args.uefa_group_winners_separated,
    uefa_playoffs_seeded=args.uefa_playoffs_seeded,
)

# Pass config to run_full_draw
groups, used_seed, metadata = run_full_draw(
    pots, 
    seed=seed, 
    max_attempts=max_attempts, 
    report_fallbacks=True,
    config=config
)

# Store config in JSONL output
result["config"] = {
    "uefa_group_winners_separated": config.uefa_group_winners_separated,
    "uefa_playoffs_seeded": config.uefa_playoffs_seeded,
}
```

### Task 8.2: Create multi-scenario scanner script
**File**: `scripts/seed_scan_scenarios.py` (new)

```python
"""
Run seed scans for all 4 combinations of feature toggles:
1. Both off (baseline)
2. UEFA group winners separated only
3. UEFA playoffs seeded only
4. Both on

Outputs separate JSONL files for each scenario.
"""

SCENARIOS = [
    {"name": "baseline", "uefa_group_winners_separated": False, "uefa_playoffs_seeded": False},
    {"name": "group_winners_sep", "uefa_group_winners_separated": True, "uefa_playoffs_seeded": False},
    {"name": "playoffs_seeded", "uefa_group_winners_separated": False, "uefa_playoffs_seeded": True},
    {"name": "both_features", "uefa_group_winners_separated": True, "uefa_playoffs_seeded": True},
]

# For each scenario, call seed_scan_large with appropriate flags
# Output: scenario_baseline.jsonl, scenario_group_winners_sep.jsonl, etc.
```

### Task 8.3: Aggregate stats per scenario
**File**: `scripts/aggregate_scenario_stats.py` (new)

```python
"""
Aggregate each scenario's JSONL into separate draw_stats files:
- draw_stats_baseline.json
- draw_stats_group_winners_sep.json
- draw_stats_playoffs_seeded.json
- draw_stats_both_features.json
"""
```

### Task 8.4: Create scenario comparison notebook
**File**: `notebooks/scenario_comparison.ipynb` (new)

```python
# Load all 4 draw_stats files
stats = {
    "Baseline": load_json("draw_stats_baseline.json"),
    "Group Winners Sep": load_json("draw_stats_group_winners_sep.json"),
    "Playoffs Seeded": load_json("draw_stats_playoffs_seeded.json"),
    "Both Features": load_json("draw_stats_both_features.json"),
}

# Create 2x2 grid of Scotland opponent charts
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("Scotland Opponents by Scenario", fontsize=16)

for idx, (scenario_name, scenario_stats) in enumerate(stats.items()):
    ax = axes[idx // 2, idx % 2]
    scotland_opponents = scenario_stats["teams"]["Scotland"]["pair_pct"]
    # Create bar chart for Scotland opponents
    # ...
    ax.set_title(scenario_name)

plt.tight_layout()
plt.savefig("notebooks/output/scotland_scenarios_comparison.png")

# Also create CSV comparing top-10 opponents across all scenarios
comparison_df = build_scotland_comparison_table(stats)
comparison_df.to_csv("notebooks/output/scotland_scenarios_comparison.csv")
```

### Task 8.5: Add group occupancy scenario comparison
**File**: `notebooks/scenario_comparison.ipynb` (continuation)

```python
# Create 2x2 grid of Scotland group occupancy charts
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("Scotland Group Placement by Scenario", fontsize=16)

for idx, (scenario_name, scenario_stats) in enumerate(stats.items()):
    ax = axes[idx // 2, idx % 2]
    scotland_groups = scenario_stats["teams"]["Scotland"]["group_pct"]
    # Create bar chart showing group A-L percentages
    # ...
    ax.set_title(scenario_name)

plt.tight_layout()
plt.savefig("notebooks/output/scotland_group_scenarios_comparison.png")
```

---

## Phase 9: Documentation

### Task 9.1: Update README
**File**: `README.md`

Document:
- New CSV columns and format
- Feature toggle CLI arguments
- Example usage scenarios
- How to research different rule interpretations

### Task 9.2: Add migration guide
**File**: `MIGRATION.md` (new)

For users with existing `teams.csv`:
- How to add FIFA rankings
- How to identify UEFA group winners
- Backward compatibility notes

---

## Implementation Order (Recommended)

1. **Phase 1**: Feature toggle framework (foundation)
2. **Phase 2**: Data model updates (enables everything else)
3. **Phase 3**: Dynamic pot assignment (independent feature)
4. **Phase 4**: UEFA group winner constraint (independent feature)
5. **Phase 5**: Integration into draw functions
6. **Phase 6**: CLI integration
7. **Phase 7**: Comprehensive testing
8. **Phase 8**: Scanner integration
9. **Phase 9**: Documentation

**Checkpoints**:
- After Phase 3: Test pot assignment in isolation
- After Phase 4: Test UEFA constraint in isolation
- After Phase 5: Full integration tests
- After Phase 8: Large-scale simulations with different configs

---

## Backward Compatibility Strategy

1. **CSV Format**: Make new columns optional, default to `None`/`0`/`false`
2. **Config Parameter**: Default to `None` → uses `DrawConfig()` with features off
3. **Existing Tests**: Add default `DrawConfig()` to preserve behavior
4. **Parser**: Auto-detect CSV format (old vs new) and handle accordingly

---

## Future Extensions

Once framework is in place, easy to add:
- `host_country_confederation_limit: bool` (different UEFA limits for host groups)
- `allow_same_continent_rematches: bool` (prevent recent competition matchups)
- `political_restrictions: Dict[str, List[str]]` (certain countries can't be grouped)
- `tv_market_distribution: bool` (balance groups for broadcast appeal)
