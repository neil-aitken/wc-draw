#!/usr/bin/env python3
"""
Calculate Scotland's probability of playing in each host city (refined).

This version accounts for:
1. Scotland is always pot 3 (A3, B3, C3, etc.)
2. For host groups (A, B, D), exact matches are known by pot
3. For non-host groups (C, E-L), pot 3 plays specific match pairs
4. Scotland plays exactly 3 games, visiting 1-3 different cities
"""

import json
import re
from pathlib import Path
from collections import defaultdict


CITY_MAP = {
    'east rutherford': 'new-york',
    'santa clara': 'san-francisco',
    'inglewood': 'los-angeles',
    'zapopan': 'guadalajara',
    'guadalupe': 'monterrey',
    'foxborough': 'boston',
    'miami gardens': 'miami',
    'arlington': 'dallas',
}


def normalize_city(venue_line):
    """Extract city from venue line and normalize to broad recognition."""
    match = re.search(r',\s*(.+)$', venue_line)
    if match:
        city = match.group(1).strip().lower()
        return CITY_MAP.get(city, city).replace(' ', '-')
    return None


def parse_group_matches(filepath="group-stage-details"):
    """Parse match details for all groups, identifying pot 3 match alternatives.

    For host groups (A, B, D): pot 3 matches are explicitly labeled
    For non-host groups: pot 3 plays one match from each pair:
      - One of matches 1-2 (50% each)
      - One of matches 3-4 (50% each)
      - One of matches 5-6 (50% each)
    """
    with open(filepath, 'r') as f:
        content = f.read()

    group_matches = {}

    # Find each group section
    for match in re.finditer(r'Group ([A-L])\n(.*?)(?=Group [A-L]|\Z)', content, re.DOTALL):
        group_letter = match.group(1)
        group_text = match.group(2)

        # Check if it's a host group
        is_host = '(H) Hosts' in group_text or ' (H)' in group_text

        # Extract all match lines (team pairs and venues)
        lines = group_text.split('\n')
        matches = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for match definitions - can be "Team1\tMatch X\tTeam2" or just "Match X\t"
            if 'Match' in line:
                # Extract match number
                match_num_match = re.search(r'Match (\d+)', line)
                if match_num_match:
                    match_num = int(match_num_match.group(1))

                    # Next line should have the venue
                    if i + 1 < len(lines):
                        venue_line = lines[i + 1].strip()
                        city = normalize_city(venue_line)

                        if city:
                            # Extract team labels if present
                            parts = [p.strip() for p in line.split('\t') if p.strip()]
                            team1 = parts[0] if len(parts) > 0 and 'Match' not in parts[0] else ''
                            team2 = parts[2] if len(parts) > 2 else ''

                            matches.append({
                                'match_num': match_num,
                                'team1': team1,
                                'team2': team2,
                                'city': city,
                                'pot3_probability': 0.0  # Will be set below
                            })
            i += 1

        # Determine pot 3 probabilities
        if is_host:
            # Host groups: explicit pot labels, 100% probability
            for m in matches:
                if f'{group_letter}3' in m['team1'] or f'{group_letter}3' in m['team2']:
                    m['pot3_probability'] = 1.0
        elif len(matches) == 6:
            # Non-host groups: pot 3 plays one match from each pair (50% each)
            # Pairs: (0,1), (2,3), (4,5)
            for pair_start in [0, 2, 4]:
                matches[pair_start]['pot3_probability'] = 0.5
                matches[pair_start + 1]['pot3_probability'] = 0.5

        # Store all matches with their pot 3 probabilities
        group_matches[f'group-{group_letter.lower()}'] = {
            'is_host': is_host,
            'matches': matches
        }

    return group_matches


def calculate_city_probabilities_refined(scotland_groups, group_matches):
    """
    Calculate probability of Scotland playing in each city per scenario.

    Accounts for:
    - Host groups: pot 3 has specific fixtures (100% probability)
    - Non-host groups: pot 3 plays one match from each pair (50% probability per match in pair)
    - Scotland visits a city if ANY of their 3 matches are there
    """
    scenario_city_probs = {}

    for scenario, group_pcts in scotland_groups.items():
        city_probs = defaultdict(float)

        for group, group_pct in group_pcts.items():
            group_key = f"group-{group.lower()}"

            if group_key in group_matches:
                # Calculate probability of playing in each city within this group
                # P(visit city | in group) = 1 - P(avoid city in all 3 matches)

                group_data = group_matches[group_key]
                city_match_probs = defaultdict(list)

                # Collect probabilities for each match in each city
                for match in group_data['matches']:
                    if match['pot3_probability'] > 0:
                        city_match_probs[match['city']].append(match['pot3_probability'])

                # Calculate probability of visiting each city
                for city, match_probs in city_match_probs.items():
                    # P(visit city) = 1 - P(avoid city in all matches)
                    # P(avoid city) = product of (1 - p) for each match
                    prob_avoid = 1.0
                    for p in match_probs:
                        prob_avoid *= (1.0 - p)

                    prob_visit = 1.0 - prob_avoid

                    # Add weighted by probability of being in this group
                    city_probs[city] += (group_pct / 100.0) * prob_visit

        scenario_city_probs[scenario] = dict(city_probs)

    return scenario_city_probs


def load_scenario_stats(filepath="scenario_stats.json"):
    """Load Scotland's group distribution from scenario stats."""
    with open(filepath, 'r') as f:
        stats = json.load(f)

    scotland_groups = {}
    for scenario in stats:
        if "Scotland" in stats[scenario]["teams"]:
            group_pct = stats[scenario]["teams"]["Scotland"]["group_pct"]
            scotland_groups[scenario] = group_pct
        else:
            scotland_groups[scenario] = {}

    return scotland_groups


def format_output(scenario_city_probs):
    """Format city probabilities as readable text."""
    output = []

    scenario_names = {
        "baseline": "Baseline (Standard FIFA Rules)",
        "playoff_seeding": "Playoff Seeding Only",
        "both_features": "Both Features (Winner Separation + Playoff Seeding)"
    }

    for scenario in sorted(scenario_city_probs.keys()):
        output.append("=" * 70)
        output.append(scenario_names.get(scenario, scenario))
        output.append("=" * 70)

        city_probs = scenario_city_probs[scenario]
        sorted_cities = sorted(city_probs.items(), key=lambda x: -x[1])

        for city, prob in sorted_cities:
            pct = prob * 100
            output.append(f"  {city:20s}: {pct:5.2f}%")

        output.append("")

    return "\n".join(output)


def format_csv(scenario_city_probs):
    """Format as CSV for further analysis."""
    all_cities = set()
    for city_probs in scenario_city_probs.values():
        all_cities.update(city_probs.keys())

    lines = []
    lines.append("city," + ",".join(sorted(scenario_city_probs.keys())))

    for city in sorted(all_cities):
        row = [city]
        for scenario in sorted(scenario_city_probs.keys()):
            prob = scenario_city_probs[scenario].get(city, 0.0) * 100
            row.append(f"{prob:.2f}")
        lines.append(",".join(row))

    return "\n".join(lines)


def main():
    stats_file = Path("scenario_stats.json")
    details_file = Path("group-stage-details")

    if not stats_file.exists():
        print(f"Error: {stats_file} not found")
        return 1

    if not details_file.exists():
        print(f"Error: {details_file} not found")
        return 1

    print("Loading scenario data...")
    scotland_groups = load_scenario_stats(stats_file)

    print("Parsing group match details...")
    group_matches = parse_group_matches(details_file)

    print("Calculating city probabilities (refined)...\n")
    scenario_city_probs = calculate_city_probabilities_refined(scotland_groups, group_matches)

    # Print formatted output
    print(format_output(scenario_city_probs))

    # Save text output
    output_file = Path("scotland_city_probabilities_refined.txt")
    output_file.write_text(format_output(scenario_city_probs))
    print(f"Saved to {output_file}")

    # Save CSV output
    csv_file = Path("scotland_city_probabilities_refined.csv")
    csv_file.write_text(format_csv(scenario_city_probs))
    print(f"Saved to {csv_file}")

    return 0


if __name__ == "__main__":
    exit(main())
