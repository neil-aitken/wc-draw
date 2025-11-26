"""
Analyze Inter Path 2 group stage opponents.

Inter Path 2 consists of AFC/CONMEBOL/CONCACAF (Iraq/Bolivia/Suriname).
This script checks how often Inter Path 2 is grouped with African teams.
"""

import json
from pathlib import Path

# African teams in the tournament
AFRICAN_TEAMS = {
    "Algeria",
    "Cape Verde",
    "Egypt",
    "Ghana",
    "Ivory Coast",
    "Morocco",
    "Senegal",
    "South Africa",
    "Tunisia",
}

# European teams in the tournament
EUROPEAN_TEAMS = {
    "Austria",
    "Belgium",
    "Croatia",
    "England",
    "France",
    "Germany",
    "Netherlands",
    "Norway",
    "Portugal",
    "Scotland",
    "Spain",
    "Switzerland",
    "UEFA Playoff A",
    "UEFA Playoff B",
    "UEFA Playoff C",
    "UEFA Playoff D",
}

# Pot 1 teams (hosts + top ranked)
POT_1_TEAMS = {
    "Mexico",
    "Canada",
    "United States",
    "Argentina",
    "Brazil",
    "Spain",
    "Belgium",
    "England",
    "France",
    "Germany",
    "Netherlands",
    "Portugal",
}

# Non-European Pot 1 teams
NON_EUROPEAN_POT_1 = {
    "Mexico",
    "Canada",
    "United States",
    "Argentina",
    "Brazil",
}


def check_inter_path_2_opponents():
    """Analyze Inter Path 2 group compositions."""
    data_file = Path(__file__).parent.parent / "seed_scan_fifa_official.jsonl"

    if not data_file.exists():
        print(f"Error: {data_file} not found")
        return

    draws_with_african_opponent = []
    draws_with_two_europeans = []
    draws_without_two_europeans = []
    draws_with_non_euro_pot1 = []
    draws_without_non_euro_pot1 = []
    total_draws = 0

    with open(data_file, "r") as f:
        for line_num, line in enumerate(f, 1):
            draw_data = json.loads(line)

            # Skip metadata line
            if "meta" in draw_data:
                continue

            total_draws += 1

            # Find all groups with Inter Path 2
            for group_name, teams in draw_data["groups"].items():
                if "Inter Path 2" in teams:
                    # Check if any other team in the group is African
                    other_teams = [t for t in teams if t != "Inter Path 2"]
                    has_african_opponent = any(team in AFRICAN_TEAMS for team in other_teams)

                    if has_african_opponent:
                        draws_with_african_opponent.append(
                            {
                                "draw_number": total_draws,
                                "group": group_name,
                                "teams": teams,
                            }
                        )

                    # Count European teams in the group (excluding Inter Path 2)
                    european_count = sum(1 for team in other_teams if team in EUROPEAN_TEAMS)

                    if european_count == 2:
                        draws_with_two_europeans.append(
                            {
                                "draw_number": total_draws,
                                "group": group_name,
                                "teams": teams,
                                "european_teams": [t for t in other_teams if t in EUROPEAN_TEAMS],
                            }
                        )
                    else:
                        draws_without_two_europeans.append(
                            {
                                "draw_number": total_draws,
                                "group": group_name,
                                "teams": teams,
                                "european_count": european_count,
                            }
                        )

                    # Check for non-European pot 1 teams
                    has_non_euro_pot1 = any(team in NON_EUROPEAN_POT_1 for team in teams)

                    if has_non_euro_pot1:
                        non_euro_pot1_team = [t for t in teams if t in NON_EUROPEAN_POT_1][0]
                        draws_with_non_euro_pot1.append(
                            {
                                "draw_number": total_draws,
                                "group": group_name,
                                "teams": teams,
                                "pot1_team": non_euro_pot1_team,
                            }
                        )
                    else:
                        draws_without_non_euro_pot1.append(
                            {
                                "draw_number": total_draws,
                                "group": group_name,
                                "teams": teams,
                            }
                        )

    # Print results
    print("=" * 70)
    print("Inter Path 2 Opponent Analysis")
    print("=" * 70)
    print(f"\nTotal draws analyzed: {total_draws:,}")

    print("\n--- African Teams ---")
    print(f"Draws where Inter Path 2 faces an African team: {len(draws_with_african_opponent):,}")

    if draws_with_african_opponent:
        print(f"Percentage: {len(draws_with_african_opponent) / total_draws * 100:.2f}%")
        print("\nFirst 5 examples:")
        print("-" * 70)
        for draw in draws_with_african_opponent[:5]:
            print(f"Draw #{draw['draw_number']}")
            print(f"  Group {draw['group']}: {', '.join(draw['teams'])}")
    else:
        print("Inter Path 2 never grouped with African teams in this dataset.")

    print("\n--- European Teams ---")
    print(
        f"Draws where Inter Path 2 has exactly 2 European opponents: "
        f"{len(draws_with_two_europeans):,}"
    )

    if draws_with_two_europeans:
        print(f"Percentage: {len(draws_with_two_europeans) / total_draws * 100:.2f}%")
        print("\nFirst 5 examples:")
        print("-" * 70)
        for draw in draws_with_two_europeans[:5]:
            euro_teams = ", ".join(draw["european_teams"])
            print(f"Draw #{draw['draw_number']}")
            print(f"  Group {draw['group']}: {', '.join(draw['teams'])}")
            print(f"  European teams: {euro_teams}")
    else:
        print("Inter Path 2 never has exactly 2 European opponents.")

    if draws_without_two_europeans:
        print(f"\nDraws with other European counts: {len(draws_without_two_europeans):,}")
        print(f"Percentage: {len(draws_without_two_europeans) / total_draws * 100:.2f}%")
        print("\nFirst 5 examples:")
        print("-" * 70)
        for draw in draws_without_two_europeans[:5]:
            print(f"Draw #{draw['draw_number']}")
            print(f"  Group {draw['group']}: {', '.join(draw['teams'])}")
            print(f"  European team count: {draw['european_count']}")

    print("\n--- Non-European Pot 1 Teams ---")
    print(
        f"Draws where Inter Path 2 has a non-European Pot 1 opponent: "
        f"{len(draws_with_non_euro_pot1):,}"
    )

    if draws_with_non_euro_pot1:
        print(f"Percentage: {len(draws_with_non_euro_pot1) / total_draws * 100:.2f}%")
        print("\nFirst 5 examples:")
        print("-" * 70)
        for draw in draws_with_non_euro_pot1[:5]:
            print(f"Draw #{draw['draw_number']}")
            print(f"  Group {draw['group']}: {', '.join(draw['teams'])}")
            print(f"  Non-European Pot 1: {draw['pot1_team']}")
    else:
        print("Inter Path 2 never grouped with non-European Pot 1 teams.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    check_inter_path_2_opponents()
