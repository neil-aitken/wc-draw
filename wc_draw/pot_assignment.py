"""Dynamic pot assignment based on FIFA rankings and configuration."""

from typing import Dict, List
from wc_draw.config import DrawConfig
from wc_draw.parser import Team


def assign_pots(teams_by_pot: Dict[int, List[Team]], config: DrawConfig) -> Dict[int, List[Team]]:
    """
    Assign teams to pots.

    Args:
        teams_by_pot: Teams organized by their default pot assignment (from CSV)
        config: Draw configuration with feature toggles

    Returns:
        Teams organized by pot

    If config.use_csv_pots=True (default): Returns the input unchanged,
    using the pot assignments directly from the CSV file.

    If config.use_csv_pots=False: Dynamically assigns teams based on FIFA rankings.
    """
    # Default: use pot assignments directly from CSV
    if config.use_csv_pots:
        return teams_by_pot
    # Flatten all teams
    all_teams = []
    for teams_list in teams_by_pot.values():
        all_teams.extend(teams_list)

    # Separate hosts and non-hosts
    hosts = sorted([t for t in all_teams if t.host], key=lambda t: t.name)
    non_hosts = [t for t in all_teams if not t.host]

    # Handle playoff paths based on configuration
    # Both UEFA Playoff and Inter Path teams are playoff qualifiers
    playoff_paths = [t for t in non_hosts if t.name.startswith("UEFA Playoff") or t.name.startswith("Inter Path")]
    non_playoff_teams = [t for t in non_hosts if not (t.name.startswith("UEFA Playoff") or t.name.startswith("Inter Path"))]

    if not config.uefa_playoffs_seeded:
        # Playoff paths forced to Pot 4, sort others by ranking
        sorted_teams = sorted(non_playoff_teams, key=lambda t: t.fifa_ranking)
    else:
        # All teams including playoff paths sorted by ranking
        sorted_teams = sorted(non_hosts, key=lambda t: t.fifa_ranking)

    # Calculate pot sizes
    num_hosts = len(hosts)
    pot1_size = 12
    pot2_size = 12
    pot3_size = 12

    # Assign teams to pots
    new_pots: Dict[int, List[Team]] = {1: [], 2: [], 3: [], 4: []}

    # Pot 1: Hosts + top-ranked teams
    new_pots[1].extend(hosts)
    remaining_pot1 = pot1_size - num_hosts

    if config.uefa_playoffs_seeded:
        new_pots[1].extend(sorted_teams[:remaining_pot1])
        sorted_teams = sorted_teams[remaining_pot1:]
    else:
        # Take from non-playoff teams only
        new_pots[1].extend(sorted_teams[:remaining_pot1])
        sorted_teams = sorted_teams[remaining_pot1:]

    # Pot 2: Next 12 teams
    new_pots[2].extend(sorted_teams[:pot2_size])
    sorted_teams = sorted_teams[pot2_size:]

    # Pot 3: Next 12 teams
    new_pots[3].extend(sorted_teams[:pot3_size])
    sorted_teams = sorted_teams[pot3_size:]

    # Pot 4: Remaining teams + playoff paths (if unseeded)
    if config.uefa_playoffs_seeded:
        new_pots[4].extend(sorted_teams)
    else:
        new_pots[4].extend(sorted_teams)
        new_pots[4].extend(playoff_paths)

    # Update pot assignments on team objects
    for pot_num, teams_list in new_pots.items():
        for team in teams_list:
            team.pot = pot_num

    return new_pots
