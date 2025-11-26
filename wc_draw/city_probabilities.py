"""
City probability mappings for all teams based on FIFA's official rules.

This module calculates the probability that a team drawn into a specific group
will play at least one match in each host city, accounting for:

1. FIFA position mappings (group_positions.py) - determines which pot goes to which position
2. Host groups (A, B, D) - have fixed match assignments per position
3. Non-host groups (C, E-L) - have pairs of possible matches per position

The key insight: Once we know a team's pot and group, we can calculate their
city visit probabilities because:
- Position = f(group, pot) via GROUP_POSITION_TO_POT
- Matches = f(group, position) via group stage schedule
- Cities = f(matches) via venue assignments
"""

import re
from collections import defaultdict
from pathlib import Path

from .group_positions import get_position_for_pot


# City name normalizations for consistency
CITY_MAP = {
    "east rutherford": "new-york",
    "santa clara": "san-francisco",
    "inglewood": "los-angeles",
    "zapopan": "guadalajara",
    "guadalupe": "monterrey",
    "foxborough": "boston",
    "miami gardens": "miami",
    "arlington": "dallas",
}


def normalize_city(venue_line: str) -> str | None:
    """Extract and normalize city name from venue line."""
    match = re.search(r",\s*(.+)$", venue_line)
    if match:
        city = match.group(1).strip().lower()
        return CITY_MAP.get(city, city).replace(" ", "-")
    return None


def parse_group_stage_details(filepath: str | Path = "group-stage-details") -> dict:
    """
    Parse the group stage details file to extract match-to-city mappings.
    
    Returns a dict mapping group -> list of matches with their details.
    Each group has is_host flag and list of matches with positions and cities.
    """
    with open(filepath, "r") as f:
        content = f.read()
    
    group_data = {}
    
    # Find each group section
    for match in re.finditer(r"Group ([A-L])\n(.*?)(?=Group [A-L]|\Z)", content, re.DOTALL):
        group_letter = match.group(1)
        group_text = match.group(2)
        
        # Check if it's a host group
        is_host = "(H) Hosts" in group_text or " (H)" in group_text
        
        # Extract all match lines
        lines = group_text.split("\n")
        matches = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for match definitions
            if "Match" in line:
                match_num_match = re.search(r"Match (\d+)", line)
                if match_num_match:
                    match_num = int(match_num_match.group(1))
                    
                    # Next line should have the venue
                    if i + 1 < len(lines):
                        venue_line = lines[i + 1].strip()
                        city = normalize_city(venue_line)
                        
                        if city:
                            # Extract position labels if present (e.g., "A3", "B2")
                            # For hosts, convert "Mexico", "Canada", "United States" to position 1
                            parts = [p.strip() for p in line.split("\t") if p.strip()]
                            position1 = parts[0] if len(parts) > 0 and "Match" not in parts[0] else ""
                            position2 = parts[2] if len(parts) > 2 else ""
                            
                            # Normalize host names to position labels
                            if position1 in ["Mexico", "Canada", "United States"]:
                                position1 = f"{group_letter}1"
                            if position2 in ["Mexico", "Canada", "United States"]:
                                position2 = f"{group_letter}1"
                            
                            matches.append({
                                "match_num": match_num,
                                "position1": position1,
                                "position2": position2,
                                "city": city,
                            })
            i += 1
        
        group_data[group_letter] = {
            "is_host": is_host,
            "matches": matches
        }
    
    return group_data


def calculate_position_city_probabilities(
    group: str, 
    position: int, 
    group_data: dict
) -> dict[str, float]:
    """
    Calculate probability of playing in each city for a given position in a group.
    
    For host groups: Position matches are explicitly labeled (100% probability)
    For non-host groups: Position plays one match from each of 3 pairs (50% each)
    
    Returns dict of city -> probability of playing at least 1 match there
    """
    if group not in group_data:
        return {}
    
    group_info = group_data[group]
    position_label = f"{group}{position}"
    
    # For host groups, find explicit matches for this position
    if group_info["is_host"]:
        city_matches = defaultdict(list)
        for match in group_info["matches"]:
            if match["position1"] == position_label or match["position2"] == position_label:
                # This position plays in this match with 100% probability
                city_matches[match["city"]].append(1.0)
        
        # Calculate "at least 1 match" probability per city
        city_probs = {}
        for city, probs in city_matches.items():
            # P(play in city) = 1 - P(avoid all matches in city)
            prob_avoid = 1.0
            for p in probs:
                prob_avoid *= (1.0 - p)
            city_probs[city] = 1.0 - prob_avoid
        
        return city_probs
    
    # For non-host groups, matches come in pairs
    # Each position plays one match from each pair (50% probability each)
    matches = group_info["matches"]
    if len(matches) != 6:
        return {}
    
    # Matches are in pairs: (0,1), (2,3), (4,5)
    # Each position plays 3 matches total: one from each pair
    city_matches = defaultdict(list)
    
    for pair_start in [0, 2, 4]:
        match1 = matches[pair_start]
        match2 = matches[pair_start + 1]
        
        # This position plays one of these two matches (50% each)
        city_matches[match1["city"]].append(0.5)
        city_matches[match2["city"]].append(0.5)
    
    # Calculate "at least 1 match" probability per city
    city_probs = {}
    for city, probs in city_matches.items():
        # P(play in city) = 1 - P(avoid all matches in city)
        prob_avoid = 1.0
        for p in probs:
            prob_avoid *= (1.0 - p)
        city_probs[city] = 1.0 - prob_avoid
    
    return city_probs


def calculate_pot_city_probabilities(
    group: str,
    pot: int,
    group_data: dict
) -> dict[str, float]:
    """
    Calculate probability of playing in each city for a given pot in a group.
    
    Uses FIFA position mappings to determine which position the pot occupies,
    then calculates city probabilities for that position.
    """
    position = get_position_for_pot(group, pot)
    return calculate_position_city_probabilities(group, position, group_data)


def build_complete_city_probability_map(
    details_file: str | Path = "group-stage-details"
) -> dict[tuple[str, int], dict[str, float]]:
    """
    Build complete mapping of (group, pot) -> {city: probability}.
    
    This precomputes city probabilities for all 48 (group, pot) combinations,
    accounting for FIFA's position mappings.
    
    Returns:
        Dict mapping (group_letter, pot_number) -> {city_name: probability}
        
    Example:
        >>> city_map = build_complete_city_probability_map()
        >>> city_map[("A", 3)]  # Pot 3 team in Group A (position A2)
        {"mexico-city": 1.0, "zapopan": 1.0, "monterrey": 1.0}
        >>> city_map[("C", 3)]  # Pot 3 team in Group C (position C4)
        {"boston": 0.875, "new-york": 0.875, "philadelphia": 0.5, ...}
    """
    group_data = parse_group_stage_details(details_file)
    
    city_prob_map = {}
    
    # Calculate for all 12 groups and 4 pots
    for group in "ABCDEFGHIJKL":
        for pot in [1, 2, 3, 4]:
            city_probs = calculate_pot_city_probabilities(group, pot, group_data)
            city_prob_map[(group, pot)] = city_probs
    
    return city_prob_map


def calculate_team_city_probabilities(
    team_group_distribution: dict[str, float],
    pot: int,
    city_prob_map: dict[tuple[str, int], dict[str, float]]
) -> dict[str, float]:
    """
    Calculate overall city probabilities for a team given their group distribution.
    
    Args:
        team_group_distribution: Dict of group -> percentage (e.g., {"A": 8.5, "B": 7.2, ...})
        pot: Which pot the team is in (1-4)
        city_prob_map: Precomputed city probabilities from build_complete_city_probability_map()
        
    Returns:
        Dict of city -> probability (0-100) of playing at least 1 match there
        
    Example:
        >>> city_map = build_complete_city_probability_map()
        >>> scotland_groups = {"A": 9.084, "B": 9.01, "C": 8.176, ...}
        >>> calculate_team_city_probabilities(scotland_groups, 3, city_map)
        {"mexico-city": 9.084, "zapopan": 18.094, "atlanta": 17.26, ...}
    """
    overall_city_probs = defaultdict(float)
    
    for group, group_pct in team_group_distribution.items():
        # Get city probabilities for this (group, pot) combination
        city_probs = city_prob_map.get((group, pot), {})
        
        # Weight by probability of being in this group
        for city, city_prob in city_probs.items():
            overall_city_probs[city] += (group_pct / 100.0) * city_prob
    
    # Convert back to percentages
    return {city: prob * 100.0 for city, prob in overall_city_probs.items()}


def calculate_all_teams_city_probabilities(
    fifa_stats: dict,
    city_prob_map: dict[tuple[str, int], dict[str, float]],
    pot_assignments: dict[str, int]
) -> dict[str, dict[str, float]]:
    """
    Calculate city probabilities for all teams in the draw.
    
    Args:
        fifa_stats: FIFA statistics with team group distributions
        city_prob_map: Precomputed city probabilities
        pot_assignments: Dict mapping team_name -> pot_number
        
    Returns:
        Dict mapping team_name -> {city: probability_percentage}
    """
    all_team_city_probs = {}
    
    for team_name, team_data in fifa_stats["teams"].items():
        if team_name not in pot_assignments:
            continue
        
        pot = pot_assignments[team_name]
        
        # team_data is already the group distribution dict
        city_probs = calculate_team_city_probabilities(team_data, pot, city_prob_map)
        all_team_city_probs[team_name] = city_probs
    
    return all_team_city_probs
