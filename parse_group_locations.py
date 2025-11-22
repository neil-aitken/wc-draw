#!/usr/bin/env python3
"""Parse group stage details and count venue usage per group."""

import re
from collections import defaultdict
from pathlib import Path


def normalize_location(venue_line):
    """Extract and normalize city name from venue line."""
    # City remapping to broader recognized names
    city_map = {
        'east rutherford': 'new-york',
        'santa clara': 'san-francisco',
        'inglewood': 'los-angeles',
        'zapopan': 'guadalajara',
        'guadalupe': 'monterrey',
        'foxborough': 'boston',
        'miami gardens': 'miami',
        'arlington': 'dallas',
    }

    # Common patterns: "Stadium Name, City" or "Stadium Name, City Name"
    match = re.search(r',\s*(.+)$', venue_line)
    if match:
        city = match.group(1).strip().lower()
        # Apply remapping if available
        city_normalized = city_map.get(city, city)
        # Convert spaces to hyphens
        return city_normalized.replace(' ', '-')
    return None


def parse_group_locations(filepath):
    """Parse group-stage-details file and return venue counts per group."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Split by groups
    group_pattern = r'Group ([A-L])\n.*?(?=Group [A-L]|\Z)'

    group_locations = {}

    for match in re.finditer(group_pattern, content, re.DOTALL):
        group_letter = match.group(1)
        group_text = match.group(0)

        # Find all venue lines (lines containing stadium names and cities)
        venue_lines = re.findall(r'^[A-Z].*?,\s*[A-Z].*$', group_text, re.MULTILINE)

        # Count locations
        location_counts = defaultdict(int)
        for venue_line in venue_lines:
            location = normalize_location(venue_line)
            if location:
                location_counts[location] += 1

        if location_counts:
            group_locations[f"group-{group_letter.lower()}"] = dict(location_counts)

    return group_locations


def format_output(group_locations):
    """Format the location counts as YAML-style output."""
    output = []
    for group in sorted(group_locations.keys()):
        output.append(f"{group}:")
        locations = group_locations[group]
        # Sort by count (descending), then by name
        sorted_locs = sorted(locations.items(), key=lambda x: (-x[1], x[0]))
        for location, count in sorted_locs:
            output.append(f"  {location}: {count}")
        output.append("")  # Blank line between groups
    return "\n".join(output)


def main():
    input_file = Path("group-stage-details")

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    group_locations = parse_group_locations(input_file)

    if not group_locations:
        print("No groups found in input file")
        return 1

    print(format_output(group_locations))

    # Optional: write to output file
    output_file = Path("group_locations.txt")
    output_file.write_text(format_output(group_locations))
    print(f"\nAlso saved to {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
