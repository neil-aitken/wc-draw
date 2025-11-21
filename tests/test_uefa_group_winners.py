"""Tests for UEFA group winner constraint."""

from wc_draw.config import DrawConfig
from wc_draw.draw import run_full_draw, _check_uefa_group_winner_constraint
from wc_draw.parser import parse_teams_config, Team


def test_check_uefa_group_winner_constraint_allows_non_winner():
    """Non-UEFA-group-winners can always be placed."""
    team = Team("Scotland", "UEFA", 4, False, None, None, 39, False)
    group_teams = [
        Team("Spain", "UEFA", 1, False, None, None, 1, True),
        Team("Japan", "AFC", 2, False, None, None, 18, False),
    ]

    assert _check_uefa_group_winner_constraint(team, group_teams) is True


def test_check_uefa_group_winner_constraint_blocks_duplicate():
    """UEFA group winners cannot be in same group as another winner."""
    team = Team("England", "UEFA", 1, False, None, None, 4, True)
    group_teams = [
        Team("Spain", "UEFA", 1, False, None, None, 1, True),
        Team("Japan", "AFC", 2, False, None, None, 18, False),
    ]

    assert _check_uefa_group_winner_constraint(team, group_teams) is False


def test_check_uefa_group_winner_constraint_allows_first_winner():
    """First UEFA group winner in a group is allowed."""
    team = Team("Spain", "UEFA", 1, False, None, None, 1, True)
    group_teams = [
        Team("Japan", "AFC", 2, False, None, None, 18, False),
    ]

    assert _check_uefa_group_winner_constraint(team, group_teams) is True


def test_uefa_group_winners_constraint_disabled():
    """When constraint disabled, multiple UEFA group winners can be in same group."""
    teams = parse_teams_config("teams.csv")
    config = DrawConfig(uefa_group_winners_separated=False)

    # Run a draw and check that we can complete it
    # (this doesn't guarantee winners are together, but ensures no artificial blocking)
    groups, seed = run_full_draw(teams, seed=42, config=config)

    # Verify draw completed successfully
    assert len(groups) == 12
    for group_teams in groups.values():
        assert len(group_teams) == 4


def test_uefa_group_winners_constraint_enabled():
    """When constraint enabled, only one UEFA group winner per World Cup group."""
    teams = parse_teams_config("teams.csv")
    config = DrawConfig(uefa_group_winners_separated=True)

    # Run multiple draws to test the constraint
    for seed in range(100, 110):
        groups, _ = run_full_draw(teams, seed=seed, config=config)

        # Verify draw completed successfully
        assert len(groups) == 12

        # Check each group has at most one UEFA group winner
        for group_letter, group_teams in groups.items():
            assert len(group_teams) == 4

            uefa_winners = [t for t in group_teams if t.uefa_group_winner]
            assert len(uefa_winners) <= 1, (
                f"Group {group_letter} has {len(uefa_winners)} UEFA group winners: "
                f"{[t.name for t in uefa_winners]}"
            )


def test_uefa_constraint_with_both_configs():
    """Test that draw works with both constraint modes."""
    teams = parse_teams_config("teams.csv")

    # Test with constraint off
    config_off = DrawConfig(uefa_group_winners_separated=False)
    groups_off, _ = run_full_draw(teams, seed=200, config=config_off)
    assert len(groups_off) == 12

    # Test with constraint on
    config_on = DrawConfig(uefa_group_winners_separated=True)
    groups_on, _ = run_full_draw(teams, seed=200, config=config_on)
    assert len(groups_on) == 12

    # Groups should differ (constraint changes eligible placements)
    # Note: with same seed, RNG sequence is same but eligible groups differ
    # so final placement will typically be different


def test_uefa_constraint_counts_winners_correctly():
    """Verify we correctly identify UEFA group winners from teams.csv."""
    teams = parse_teams_config("teams.csv")

    all_teams = []
    for pot_teams in teams.values():
        all_teams.extend(pot_teams)

    uefa_winners = [t for t in all_teams if t.uefa_group_winner]

    # Should have exactly 10 UEFA group winners (from Phase 2 data)
    assert len(uefa_winners) == 10

    # Verify they're all UEFA teams
    for winner in uefa_winners:
        assert winner.confederation == "UEFA"

    # Verify expected teams are marked as winners
    winner_names = {t.name for t in uefa_winners}
    expected_winners = {
        "Austria",
        "Belgium",
        "Croatia",
        "England",
        "France",
        "Germany",
        "Netherlands",
        "Portugal",
        "Spain",
        "Switzerland",
    }
    assert winner_names == expected_winners


def test_uefa_constraint_playoff_paths_not_winners():
    """Playoff paths cannot be UEFA group winners."""
    teams = parse_teams_config("teams.csv")

    all_teams = []
    for pot_teams in teams.values():
        all_teams.extend(pot_teams)

    playoff_paths = [t for t in all_teams if "Playoff" in t.name]

    # None of the playoff paths should be group winners
    for path in playoff_paths:
        assert path.uefa_group_winner is False
