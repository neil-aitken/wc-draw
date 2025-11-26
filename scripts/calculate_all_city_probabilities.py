#!/usr/bin/env python3
"""
Calculate city visit probabilities for all teams based on FIFA official constraints.

This script:
1. Loads the 50k FIFA draw results
2. Parses the group stage details and FIFA position mappings
3. Calculates for each team the probability of playing at least 1 match in each city
4. Outputs results in JSON and CSV formats
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to import wc_draw module
sys.path.insert(0, str(Path(__file__).parent.parent))

from wc_draw.city_probabilities import (
    build_complete_city_probability_map,
    calculate_all_teams_city_probabilities,
)


# Pot assignments for all teams
POT_ASSIGNMENTS = {
    # Pot 1 (top seeds + hosts)
    "Spain": 1,
    "Argentina": 1,
    "France": 1,
    "England": 1,
    "Brazil": 1,
    "Belgium": 1,
    "Netherlands": 1,
    "Portugal": 1,
    "Germany": 1,
    "Croatia": 1,
    "Mexico": 1,  # Host
    "United States": 1,  # Host
    "Canada": 1,  # Host
    
    # Pot 2
    "Uruguay": 2,
    "Colombia": 2,
    "Senegal": 2,
    "Iran": 2,
    "Japan": 2,
    "Morocco": 2,
    "Switzerland": 2,
    "Australia": 2,
    "South Korea": 2,
    "Egypt": 2,
    "Algeria": 2,
    "Tunisia": 2,
    
    # Pot 3
    "Scotland": 3,
    "Austria": 3,
    "Norway": 3,
    "Ecuador": 3,
    "Ghana": 3,
    "Saudi Arabia": 3,
    "Qatar": 3,
    "Uzbekistan": 3,
    "South Africa": 3,
    "Ivory Coast": 3,
    "Cape Verde": 3,
    "Jordan": 3,
    
    # Pot 4
    "New Zealand": 4,
    "Paraguay": 4,
    "Curacao": 4,
    "Panama": 4,
    "Haiti": 4,
    "Inter Path 1": 4,
    "Inter Path 2": 4,
    "UEFA Playoff A": 4,
    "UEFA Playoff B": 4,
    "UEFA Playoff C": 4,
    "UEFA Playoff D": 4,
}


def load_fifa_stats(filepath="fifa_official_stats.json"):
    """Load FIFA statistics from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def format_city_probs_for_output(all_team_city_probs):
    """Format city probabilities for JSON output."""
    # Round to 2 decimal places for cleaner output
    formatted = {}
    for team, city_probs in all_team_city_probs.items():
        formatted[team] = {
            city: round(prob, 2)
            for city, prob in sorted(city_probs.items(), key=lambda x: -x[1])
        }
    return formatted


def save_json_output(all_team_city_probs, output_file="team_city_probabilities.json"):
    """Save city probabilities to JSON file."""
    formatted = format_city_probs_for_output(all_team_city_probs)
    
    with open(output_file, "w") as f:
        json.dump(formatted, f, indent=2)
    
    print(f"✓ Saved JSON to {output_file}")


def save_csv_output(all_team_city_probs, output_file="team_city_probabilities.csv"):
    """Save city probabilities to CSV file (teams as rows, cities as columns)."""
    # Get all unique cities
    all_cities = set()
    for city_probs in all_team_city_probs.values():
        all_cities.update(city_probs.keys())
    
    sorted_cities = sorted(all_cities)
    
    lines = []
    # Header
    lines.append("team," + ",".join(sorted_cities))
    
    # Data rows
    for team in sorted(all_team_city_probs.keys()):
        city_probs = all_team_city_probs[team]
        row = [team]
        for city in sorted_cities:
            prob = city_probs.get(city, 0.0)
            row.append(f"{prob:.2f}")
        lines.append(",".join(row))
    
    with open(output_file, "w") as f:
        f.write("\n".join(lines))
    
    print(f"✓ Saved CSV to {output_file}")


def print_sample_results(all_team_city_probs, sample_teams=None):
    """Print sample results for verification."""
    if sample_teams is None:
        sample_teams = ["Scotland", "Spain", "Argentina", "France", "England"]
    
    print("\n" + "=" * 70)
    print("Sample City Probabilities (Top 5 cities per team)")
    print("=" * 70)
    
    for team in sample_teams:
        if team not in all_team_city_probs:
            continue
        
        print(f"\n{team}:")
        city_probs = all_team_city_probs[team]
        sorted_cities = sorted(city_probs.items(), key=lambda x: -x[1])[:5]
        
        for city, prob in sorted_cities:
            print(f"  {city:20s}: {prob:5.2f}%")


def main():
    print("=" * 70)
    print("City Probability Calculator - FIFA Official Constraints")
    print("=" * 70)
    
    # Check for required files
    stats_file = Path("fifa_official_stats.json")
    details_file = Path("group-stage-details")
    
    if not stats_file.exists():
        print(f"\nError: {stats_file} not found")
        print("Run: python3 scripts/aggregate_fifa_stats.py")
        return 1
    
    if not details_file.exists():
        print(f"\nError: {details_file} not found")
        return 1
    
    # Load FIFA statistics
    print(f"\nLoading FIFA statistics from {stats_file}...")
    fifa_stats = load_fifa_stats(stats_file)
    print(f"  Teams: {len(fifa_stats['teams'])}")
    print(f"  Runs: {fifa_stats['total_runs']:,}")
    
    # Build city probability map
    print(f"\nParsing group stage details from {details_file}...")
    city_prob_map = build_complete_city_probability_map(details_file)
    print(f"  Mapped {len(city_prob_map)} (group, pot) combinations")
    
    # Calculate city probabilities for all teams
    print("\nCalculating city probabilities for all teams...")
    all_team_city_probs = calculate_all_teams_city_probabilities(
        fifa_stats, city_prob_map, POT_ASSIGNMENTS
    )
    print(f"  Calculated for {len(all_team_city_probs)} teams")
    
    # Save outputs
    print("\nSaving results...")
    save_json_output(all_team_city_probs, "team_city_probabilities.json")
    save_csv_output(all_team_city_probs, "team_city_probabilities.csv")
    
    # Print sample results
    print_sample_results(all_team_city_probs)
    
    print("\n" + "=" * 70)
    print("✓ Complete!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
