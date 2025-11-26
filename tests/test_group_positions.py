"""
Tests for FIFA's official group position assignments.
"""

import pytest
from wc_draw.group_positions import (
    get_position_for_pot,
    get_pot_for_position,
    get_position_order_for_group,
)
from wc_draw.parser import parse_teams_config
from wc_draw.pot_assignment import assign_pots
from wc_draw.draw import run_full_draw
from wc_draw.config import DrawConfig


class TestGroupPositionMappings:
    """Test the group position to pot mappings."""

    def test_group_a_mapping(self):
        """Verify Group A position mapping: 1=Pot1, 2=Pot3, 3=Pot2, 4=Pot4."""
        assert get_pot_for_position("A", 1) == 1
        assert get_pot_for_position("A", 2) == 3  # Pot 3 in position 2
        assert get_pot_for_position("A", 3) == 2  # Pot 2 in position 3
        assert get_pot_for_position("A", 4) == 4

        # Reverse mapping
        assert get_position_for_pot("A", 1) == 1
        assert get_position_for_pot("A", 2) == 3  # Pot 2 goes to position 3
        assert get_position_for_pot("A", 3) == 2  # Pot 3 goes to position 2
        assert get_position_for_pot("A", 4) == 4

    def test_group_b_mapping(self):
        """Verify Group B position mapping: 1=Pot1, 2=Pot4, 3=Pot3, 4=Pot2."""
        assert get_pot_for_position("B", 1) == 1
        assert get_pot_for_position("B", 2) == 4  # Pot 4 in position 2
        assert get_pot_for_position("B", 3) == 3  # Pot 3 in position 3
        assert get_pot_for_position("B", 4) == 2  # Pot 2 in position 4

        # Reverse mapping
        assert get_position_for_pot("B", 1) == 1
        assert get_position_for_pot("B", 2) == 4  # Pot 2 goes to position 4
        assert get_position_for_pot("B", 3) == 3  # Pot 3 goes to position 3
        assert get_position_for_pot("B", 4) == 2  # Pot 4 goes to position 2

    def test_group_c_mapping(self):
        """Verify Group C position mapping: 1=Pot1, 2=Pot2, 3=Pot4, 4=Pot3."""
        assert get_pot_for_position("C", 1) == 1
        assert get_pot_for_position("C", 2) == 2
        assert get_pot_for_position("C", 3) == 4  # Pot 4 in position 3
        assert get_pot_for_position("C", 4) == 3  # Pot 3 in position 4

    @pytest.mark.parametrize(
        "group,expected",
        [
            ("A", [1, 3, 2, 4]),
            ("B", [1, 4, 3, 2]),
            ("C", [1, 2, 4, 3]),
            ("D", [1, 3, 2, 4]),
            ("E", [1, 4, 3, 2]),
            ("F", [1, 2, 4, 3]),
            ("G", [1, 3, 2, 4]),
            ("H", [1, 4, 3, 2]),
            ("I", [1, 2, 4, 3]),
            ("J", [1, 3, 2, 4]),
            ("K", [1, 4, 3, 2]),
            ("L", [1, 2, 4, 3]),
        ],
    )
    def test_all_group_position_orders(self, group, expected):
        """Test position order for all groups."""
        assert get_position_order_for_group(group) == expected

    def test_all_groups_have_all_pots(self):
        """Verify every group has exactly one team from each pot (1-4)."""
        for group in "ABCDEFGHIJKL":
            position_order = get_position_order_for_group(group)
            assert sorted(position_order) == [1, 2, 3, 4], (
                f"Group {group} doesn't have one team from each pot"
            )

    def test_invalid_group_raises_error(self):
        """Test that invalid group labels raise errors."""
        with pytest.raises(ValueError):
            get_pot_for_position("Z", 1)

        with pytest.raises(ValueError):
            get_position_for_pot("M", 1)

    def test_invalid_position_raises_error(self):
        """Test that invalid position numbers raise errors."""
        with pytest.raises(ValueError):
            get_pot_for_position("A", 0)

        with pytest.raises(ValueError):
            get_pot_for_position("A", 5)

    def test_invalid_pot_raises_error(self):
        """Test that invalid pot numbers raise errors."""
        with pytest.raises(ValueError):
            get_position_for_pot("A", 0)

        with pytest.raises(ValueError):
            get_position_for_pot("A", 5)


class TestDrawWithPositionMapping:
    """Test that draw results respect FIFA position mappings."""

    def test_draw_applies_position_mapping(self):
        """Verify that completed draw has teams in correct positions."""
        teams_by_pot = parse_teams_config("teams.csv")
        config = DrawConfig()
        pots = assign_pots(teams_by_pot, config)

        groups, seed = run_full_draw(pots, seed=42, config=config)

        # Check all groups have correct position order
        for group_label, teams in groups.items():
            assert len(teams) == 4, f"Group {group_label} doesn't have 4 teams"

            expected_pot_order = get_position_order_for_group(group_label)
            actual_pot_order = [team.pot for team in teams]

            assert actual_pot_order == expected_pot_order, (
                f"Group {group_label} has incorrect position mapping.\n"
                f"Expected pot order: {expected_pot_order}\n"
                f"Actual pot order:   {actual_pot_order}"
            )

    def test_position_mapping_consistent_across_seeds(self):
        """Test that position mapping is applied correctly across different seeds."""
        teams_by_pot = parse_teams_config("teams.csv")
        config = DrawConfig()
        pots = assign_pots(teams_by_pot, config)

        for seed_val in [42, 123, 456]:
            groups, seed = run_full_draw(pots, seed=seed_val, config=config)

            # All groups should have correct position mapping
            for group_label, teams in groups.items():
                expected_pot_order = get_position_order_for_group(group_label)
                actual_pot_order = [team.pot for team in teams]

                assert actual_pot_order == expected_pot_order, (
                    f"Seed {seed_val}, Group {group_label}: "
                    f"Expected {expected_pot_order}, got {actual_pot_order}"
                )

    def test_group_a_scotland_in_position_2(self):
        """
        Test the Scotland example: If Scotland (Pot 3) is drawn into Group A,
        they should be in position 2 (A2), not position 3.
        """
        teams_by_pot = parse_teams_config("teams.csv")
        config = DrawConfig()
        pots = assign_pots(teams_by_pot, config)

        # Find a seed where Scotland is in Group A
        for seed_val in range(1000):
            groups, seed = run_full_draw(pots, seed=seed_val, config=config)

            # Check if Scotland is in Group A
            scotland_in_a = any(team.name == "Scotland" for team in groups["A"])

            if scotland_in_a:
                # Find Scotland's position in the group
                for position, team in enumerate(groups["A"], 1):
                    if team.name == "Scotland":
                        # Scotland is Pot 3, so should be in position 2 for Group A
                        assert position == 2, (
                            f"Scotland (Pot 3) in Group A should be at position 2, "
                            f"but found at position {position}"
                        )
                        print(f"✓ Seed {seed_val}: Scotland is correctly at position A2")
                        return

        # If we get here, Scotland was never drawn into Group A in 1000 seeds
        pytest.skip("Scotland not drawn into Group A in test seeds")
