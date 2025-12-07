"""
Configuration constants for World Cup 2026 tournament simulation.
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple

# Number of Monte Carlo simulations to run
NUM_SIMULATIONS: int = 10_000

# Poisson goal model parameters
# Home advantage is neutralized at World Cup (neutral venues)
HOME_ADVANTAGE: float = 0.0
# Average goals per team per match in World Cup history
AVG_GOALS: float = 1.35

# Elo rating system parameters
ELO_K_FACTOR: float = 40.0  # For match result updates (not used in sim)
ELO_SCALE: float = 400.0    # Standard Elo scaling factor

# Data paths
DATA_DIR: Path = Path(__file__).parent / "data"
ELO_RATINGS_FILE: Path = DATA_DIR / "elo_ratings.json"
SIMULATION_RESULTS_FILE: Path = DATA_DIR / "simulation_results.json"

# Group definitions (from the actual draw)
# Format: group_letter -> list of team names
# "UEFA Path X" and "IC Path Y" are placeholders for playoff winners
GROUPS: Dict[str, List[str]] = {
    "A": ["Mexico", "South Africa", "South Korea", "UEFA Path D"],
    "B": ["Canada", "UEFA Path A", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "UEFA Path C"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "UEFA Path B", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "IC Path 2", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "IC Path 1", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# Placeholder team definitions (will be replaced by playoff simulation)
# We'll add Tunisia to F as it was missing
GROUPS["F"] = ["Netherlands", "Japan", "UEFA Path B", "Tunisia"]

# UEFA Playoff Paths - 4 teams in each path, semifinal + final
UEFA_PLAYOFFS: Dict[str, List[str]] = {
    # Path A: Semifinal: Italy vs Wales, Bosnia vs Northern Ireland
    # Winner of SF1 vs Winner of SF2
    "A": ["Italy", "Wales", "Bosnia and Herzegovina", "Northern Ireland"],
    
    # Path B: Semifinal: Ukraine vs Poland, Albania vs Sweden
    "B": ["Ukraine", "Poland", "Albania", "Sweden"],
    
    # Path C: Semifinal: Turkey vs Slovakia, Kosovo vs Romania
    "C": ["Turkey", "Slovakia", "Kosovo", "Romania"],
    
    # Path D: Semifinal: Denmark vs Czech Republic, Ireland vs North Macedonia
    "D": ["Denmark", "Czech Republic", "Ireland", "North Macedonia"],
}

# Intercontinental Playoff Paths - single-elimination 3-team brackets
IC_PLAYOFFS: Dict[str, List[str]] = {
    # IC Path 1: DR Congo plays winner of Jamaica vs New Caledonia
    "1": ["DR Congo", "Jamaica", "New Caledonia"],
    
    # IC Path 2: Iraq plays winner of Bolivia vs Suriname
    "2": ["Iraq", "Bolivia", "Suriname"],
}

# Mapping of playoff path to group letter (where winner goes)
PLAYOFF_PATH_TO_GROUP: Dict[str, str] = {
    "UEFA Path A": "B",
    "UEFA Path B": "F",
    "UEFA Path C": "D",
    "UEFA Path D": "A",
    "IC Path 1": "K",
    "IC Path 2": "I",
}

# Build mapping of playoff team to their potential group
PLAYOFF_TEAM_GROUPS: Dict[str, str] = {}
for path, teams in UEFA_PLAYOFFS.items():
    group = PLAYOFF_PATH_TO_GROUP[f"UEFA Path {path}"]
    for team in teams:
        PLAYOFF_TEAM_GROUPS[team] = group
for path, teams in IC_PLAYOFFS.items():
    group = PLAYOFF_PATH_TO_GROUP[f"IC Path {path}"]
    for team in teams:
        PLAYOFF_TEAM_GROUPS[team] = group

# Third-place teams advance to R32 based on which 8 of 12 groups they come from
# FIFA has a fixed mapping based on which combination of groups produce third-place qualifiers
# There are C(12,8) = 495 possible combinations
# Each combination has a predetermined assignment of third-place teams to R32 slots

# The 8 R32 slots available for third-place teams (match numbers in bracket)
# These correspond to: A2/3rd, B1/3rd, C2/3rd, D1/3rd, E2/3rd, F1/3rd, G2/3rd, H1/3rd
# The actual third-place assignment varies based on which groups qualify

# FIFA Third-Place-to-R32 Mapping
# Key: Tuple of 8 group letters (sorted) that produced qualifying third-place teams
# Value: Dict mapping each qualifying group to its R32 match slot
# The slot indicates which group winner/runner-up the third-place team faces

# Rather than enumerate all 495 combinations, we use a programmatic approach
# based on FIFA's ranking rules:
# 1. Third-place teams are ranked by points, GD, GF, etc.
# 2. Best 8 of 12 advance
# 3. The best-ranked third goes to the "easiest" slot, worst to "hardest"

# For now, we hardcode a simplified mapping based on the known bracket structure
# The R32 matches that include third-place teams are:
# Match 73: 1A vs 3C/D/E/F (Group A winner vs 3rd place from C/D/E/F)
# Match 74: 2A vs 3D/E/F/G (Group A runner-up vs 3rd from D/E/F/G)
# etc.

# Hardcoded third-place to R32 assignment
# This maps which group's third-place team goes to which R32 slot
# Based on official FIFA documentation for 48-team World Cup

# R32 Match assignments (match_number -> (group_winner, group_runner_up))
# Some matches have a third-place team instead of a runner-up

R32_BRACKET: Dict[int, Tuple[str, str]] = {
    # Upper bracket
    73: ("1A", "2C"),  # Winner A vs Runner-up C
    74: ("1B", "2D"),  # Winner B vs Runner-up D
    75: ("1C", "2A"),  # Winner C vs Runner-up A
    76: ("1D", "2B"),  # Winner D vs Runner-up B
    77: ("1E", "2G"),  # Winner E vs Runner-up G
    78: ("1F", "2H"),  # Winner F vs Runner-up H
    79: ("1G", "2E"),  # Winner G vs Runner-up E
    80: ("1H", "2F"),  # Winner H vs Runner-up F
    
    # Lower bracket (with third-place teams)
    81: ("1I", "3A/B/C/D"),  # Winner I vs 3rd from A/B/C/D
    82: ("1J", "3E/F/G/H"),  # Winner J vs 3rd from E/F/G/H
    83: ("1K", "3I/J/K/L"),  # Winner K vs 3rd from I/J/K/L
    84: ("1L", "3A/B/I/J"),  # Winner L vs 3rd from A/B/I/J
    85: ("2I", "3C/D/K/L"),  # Runner-up I vs 3rd from C/D/K/L
    86: ("2J", "3E/F/I/J"),  # Runner-up J vs 3rd from E/F/I/J
    87: ("2K", "3G/H/K/L"),  # Runner-up K vs 3rd from G/H/K/L
    88: ("2L", "3A/B/G/H"),  # Runner-up L vs 3rd from A/B/G/H
}

# Mapping of which third-place groups can go to which R32 matches
# This is determined by FIFA rules to ensure variety of opponents
THIRD_PLACE_ELIGIBLE_MATCHES: Dict[str, List[int]] = {
    "A": [81, 84, 88],
    "B": [81, 84, 88],
    "C": [81, 85],
    "D": [81, 85],
    "E": [82, 86],
    "F": [82, 86],
    "G": [82, 87, 88],
    "H": [82, 87, 88],
    "I": [83, 86],
    "J": [83, 84, 86],
    "K": [83, 85, 87],
    "L": [83, 85, 87],
}

# Full knockout bracket structure (R16 onwards)
# R16 matches (winners of R32 matches)
R16_BRACKET: Dict[int, Tuple[int, int]] = {
    89: (73, 74),   # W73 vs W74
    90: (75, 76),   # W75 vs W76
    91: (77, 78),   # W77 vs W78
    92: (79, 80),   # W79 vs W80
    93: (81, 82),   # W81 vs W82
    94: (83, 84),   # W83 vs W84
    95: (85, 86),   # W85 vs W86
    96: (87, 88),   # W87 vs W88
}

# Quarterfinals
QF_BRACKET: Dict[int, Tuple[int, int]] = {
    97: (89, 90),   # W89 vs W90
    98: (91, 92),   # W91 vs W92
    99: (93, 94),   # W93 vs W94
    100: (95, 96),  # W95 vs W96
}

# Semifinals
SF_BRACKET: Dict[int, Tuple[int, int]] = {
    101: (97, 98),   # W97 vs W98
    102: (99, 100),  # W99 vs W100
}

# Finals
THIRD_PLACE_MATCH: Tuple[int, int] = (101, 102)  # L101 vs L102
FINAL_MATCH: Tuple[int, int] = (101, 102)        # W101 vs W102

# Outcome labels for tracking results
OUTCOME_LABELS: List[str] = [
    "Did Not Qualify", # -1 (lost playoff, not in tournament)
    "Group 1st",      # 0
    "Group 2nd",      # 1
    "Group 3rd",      # 2
    "Group 4th",      # 3
    "R32 Exit",       # 4 (out in round of 32)
    "R16 Exit",       # 5 (out in round of 16)
    "QF Exit",        # 6 (out in quarterfinals)
    "SF Exit",        # 7 (out in semifinals, but not 3rd/4th)
    "4th Place",      # 8
    "3rd Place",      # 9
    "Runner-up",      # 10
    "Winner",         # 11
]

# All teams that need to play in playoffs (not yet qualified)
# These teams can have "Did Not Qualify" as an outcome
PLAYOFF_TEAMS: Set[str] = set()
for teams in UEFA_PLAYOFFS.values():
    PLAYOFF_TEAMS.update(teams)
for teams in IC_PLAYOFFS.values():
    PLAYOFF_TEAMS.update(teams)

# Group stage tiebreaker rules (in order of application)
# 1. Points
# 2. Goal difference
# 3. Goals scored
# 4. Head-to-head points (among tied teams only)
# 5. Head-to-head goal difference
# 6. Head-to-head goals scored
# 7. Fair play points -> coin flip (random)
# 8. FIFA ranking (if still tied after coin flip, extremely rare)

# For FIFA ranking tiebreaker
FIFA_RANKING_FOR_TIEBREAK: Dict[str, int] = {
    # This will be populated from elo_ratings.json fifa_rank field
}
