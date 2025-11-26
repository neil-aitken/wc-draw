"""
Check how often a Pot 2 UEFA team and a Pot 3 UEFA team are in the same group.
"""

import json


def load_teams():
    """Load team data from teams.csv."""
    teams = {}
    with open("teams.csv", "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split(",")
            if len(parts) >= 3:
                team_name = parts[0]
                confederation = parts[1]
                pot = int(parts[2])
                teams[team_name] = {"confederation": confederation, "pot": pot}
    return teams


def analyze_uefa_pot2_pot3():
    """Analyze how often Pot 2 and Pot 3 UEFA teams are together."""
    teams = load_teams()

    # Identify UEFA teams by pot
    uefa_pot2 = [
        team for team, info in teams.items() if info["confederation"] == "UEFA" and info["pot"] == 2
    ]
    uefa_pot3 = [
        team for team, info in teams.items() if info["confederation"] == "UEFA" and info["pot"] == 3
    ]

    print("=" * 70)
    print("UEFA Pot 2 and Pot 3 Co-occurrence Analysis")
    print("=" * 70)
    print(f"\nUEFA Pot 2 teams ({len(uefa_pot2)}): {', '.join(uefa_pot2)}")
    print(f"UEFA Pot 3 teams ({len(uefa_pot3)}): {', '.join(uefa_pot3)}")

    # Load draw stats (has pair_pct which is actual pairing probability)
    with open("draw_stats.json", "r") as f:
        draw_stats = json.load(f)

    team_data = draw_stats["teams"]

    print("\n" + "=" * 70)
    print("Pairing Probabilities from draw_stats.json")
    print("=" * 70)

    # Check pairing probabilities
    total_prob = 0
    pair_probs = []

    for pot2_team in uefa_pot2:
        if pot2_team not in team_data:
            continue

        pair_pct = team_data[pot2_team].get("pair_pct", {})

        for pot3_team in uefa_pot3:
            prob = pair_pct.get(pot3_team, 0)
            if prob > 0:
                pair_probs.append((pot2_team, pot3_team, prob))
                total_prob += prob

    print("\nAll UEFA Pot 2 & Pot 3 Pairings:")
    print("-" * 70)
    for pot2, pot3, prob in sorted(pair_probs, key=lambda x: -x[2]):
        print(f"{pot2:15s} + {pot3:15s}: {prob:6.2f}%")

    print("\n" + "=" * 70)
    print("Summary Statistics")
    print("=" * 70)
    print(f"Total probability across all pairs: {total_prob:.2f}%")
    print(f"Expected number of such pairings per draw: {total_prob / 100:.3f}")

    # Calculate average per Pot 3 team
    print("\nPer Pot 3 Team:")
    for pot3_team in uefa_pot3:
        team_total = sum(prob for p2, p3, prob in pair_probs if p3 == pot3_team)
        print(f"  {pot3_team:15s}: {team_total:6.2f}% (faces UEFA Pot 2)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    analyze_uefa_pot2_pot3()
