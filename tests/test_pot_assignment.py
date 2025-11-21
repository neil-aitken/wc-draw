"""Tests for dynamic pot assignment."""

from wc_draw.config import DrawConfig
from wc_draw.parser import parse_teams_config
from wc_draw.pot_assignment import assign_pots


def test_assign_pots_defaults():
    """Test pot assignment with default configuration (no features enabled)."""
    teams = parse_teams_config("teams.csv")
    config = DrawConfig()

    new_pots = assign_pots(teams, config)

    # Should have 4 pots with 12 teams each
    assert len(new_pots) == 4
    assert all(len(teams) == 12 for teams in new_pots.values())

    # Hosts should be in Pot 1
    pot1_names = {t.name for t in new_pots[1]}
    assert "Canada" in pot1_names
    assert "Mexico" in pot1_names
    assert "United States" in pot1_names

    # With uefa_playoffs_seeded=False, playoff paths should be in Pot 4
    pot4_names = {t.name for t in new_pots[4]}
    assert "UEFA Playoff A" in pot4_names
    assert "UEFA Playoff B" in pot4_names


def test_assign_pots_uefa_playoffs_seeded():
    """Test pot assignment with uefa_playoffs_seeded=True."""
    teams = parse_teams_config("teams.csv")
    config = DrawConfig(uefa_playoffs_seeded=True)

    new_pots = assign_pots(teams, config)

    # Playoff paths should be sorted by FIFA ranking
    # UEFA Playoff A (rank 12) should be in Pot 2 (9 better teams + 3 hosts in Pot 1)
    pot2_names = {t.name for t in new_pots[2]}
    assert "UEFA Playoff A" in pot2_names  # Italy's rank (12)

    # UEFA Playoff B (rank 20) might be in Pot 2 or 3 depending on other rankings
    all_names_by_pot = {pot: {t.name for t in teams} for pot, teams in new_pots.items()}
    assert any("UEFA Playoff B" in names for names in all_names_by_pot.values())


def test_assign_pots_preserves_all_teams():
    """Test that all teams are preserved during reassignment."""
    teams = parse_teams_config("teams.csv")
    config = DrawConfig()

    original_names = set()
    for teams_list in teams.values():
        original_names.update(t.name for t in teams_list)

    new_pots = assign_pots(teams, config)

    new_names = set()
    for teams_list in new_pots.values():
        new_names.update(t.name for t in teams_list)

    assert original_names == new_names


def test_assign_pots_updates_team_pot_field():
    """Test that team.pot field is updated to match new pot assignment."""
    teams = parse_teams_config("teams.csv")
    config = DrawConfig()

    new_pots = assign_pots(teams, config)

    for pot_num, teams_list in new_pots.items():
        for team in teams_list:
            assert team.pot == pot_num


def test_assign_pots_hosts_always_pot1():
    """Test that hosts are always in Pot 1 regardless of FIFA ranking."""
    teams = parse_teams_config("teams.csv")

    # Test with both configurations
    for config in [DrawConfig(), DrawConfig(uefa_playoffs_seeded=True)]:
        new_pots = assign_pots(teams, config)

        pot1_names = {t.name for t in new_pots[1]}
        assert "Canada" in pot1_names
        assert "Mexico" in pot1_names
        assert "United States" in pot1_names


def test_assign_pots_sorted_by_ranking():
    """Test that non-host teams are sorted by FIFA ranking."""
    teams = parse_teams_config("teams.csv")
    config = DrawConfig(uefa_playoffs_seeded=True)  # Include playoffs in ranking

    new_pots = assign_pots(teams, config)

    # Get non-host teams from Pot 1
    pot1_non_hosts = [t for t in new_pots[1] if not t.host]

    # Should be sorted by ranking (ascending = best first)
    rankings = [t.fifa_ranking for t in pot1_non_hosts]
    assert rankings == sorted(rankings)

    # Top ranked non-host should be in Pot 1
    # Argentina (rank 1) should be in Pot 1
    pot1_names = {t.name for t in new_pots[1]}
    assert "Argentina" in pot1_names


def test_assign_pots_pot_sizes():
    """Test that each pot has exactly 12 teams."""
    teams = parse_teams_config("teams.csv")

    for config in [DrawConfig(), DrawConfig(uefa_playoffs_seeded=True)]:
        new_pots = assign_pots(teams, config)

        for pot_num in [1, 2, 3, 4]:
            assert len(new_pots[pot_num]) == 12, f"Pot {pot_num} should have 12 teams"
