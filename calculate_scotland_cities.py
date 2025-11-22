#!/usr/bin/env python3
"""Calculate Scotland's probability of playing in each host city across scenarios."""

import json
from pathlib import Path
from collections import defaultdict


# City mapping from parse_group_locations.py
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


def load_group_locations(filepath="group_locations.txt"):
    """Load venue counts per group from the parsed location file."""
    group_locations = {}
    current_group = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith('group-'):
                current_group = line.rstrip(':')
            elif current_group and ':' in line:
                city, count = line.split(':', 1)
                city = city.strip()
                count = int(count.strip())

                if current_group not in group_locations:
                    group_locations[current_group] = {}
                group_locations[current_group][city] = count

    return group_locations


def calculate_city_probabilities(scotland_groups, group_locations):
    """Calculate probability of Scotland playing in each city per scenario."""
    scenario_city_probs = {}

    for scenario, group_pcts in scotland_groups.items():
        city_probs = defaultdict(float)

        for group, group_pct in group_pcts.items():
            # Convert group letter to group-X format
            group_key = f"group-{group.lower()}"

            if group_key in group_locations:
                # For each city in this group, add weighted probability
                for city, match_count in group_locations[group_key].items():
                    # Probability = (% chance in group) * (matches in city / 6 total)
                    # Each group plays 6 matches total (4 teams, 3 matches each,
                    # counting each match twice = 6)
                    city_prob = (group_pct / 100.0) * (match_count / 6.0)
                    city_probs[city] += city_prob

        scenario_city_probs[scenario] = dict(city_probs)

    return scenario_city_probs


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
            # Convert to percentage
            pct = prob * 100
            output.append(f"  {city:20s}: {pct:5.2f}%")

        output.append("")

    return "\n".join(output)


def format_csv(scenario_city_probs):
    """Format as CSV for further analysis."""
    # Get all cities
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
    locations_file = Path("group_locations.txt")

    if not stats_file.exists():
        print(f"Error: {stats_file} not found")
        print("Run the scenario analysis first:")
        print("  python3 scripts/seed_scan_scenarios.py --start 0 --end 10000 --workers 8")
        print("  python3 scripts/aggregate_scenario_stats.py")
        return 1

    if not locations_file.exists():
        print(f"Error: {locations_file} not found")
        print("Run: python3 parse_group_locations.py")
        return 1

    print("Loading scenario data...")
    scotland_groups = load_scenario_stats(stats_file)

    print("Loading venue locations...")
    group_locations = load_group_locations(locations_file)

    print("Calculating city probabilities...\n")
    scenario_city_probs = calculate_city_probabilities(scotland_groups, group_locations)

    # Print formatted output
    print(format_output(scenario_city_probs))

    # Save text output
    output_file = Path("scotland_city_probabilities.txt")
    output_file.write_text(format_output(scenario_city_probs))
    print(f"Saved to {output_file}")

    # Save CSV output
    csv_file = Path("scotland_city_probabilities.csv")
    csv_file.write_text(format_csv(scenario_city_probs))
    print(f"Saved to {csv_file}")

    return 0


if __name__ == "__main__":
    exit(main())
