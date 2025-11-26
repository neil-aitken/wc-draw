"""
Tests for city probability calculations.

These tests verify that the city probability system correctly:
1. Parses group stage details
2. Maps positions to pots using FIFA's official mappings
3. Calculates city probabilities for individual (group, pot) combinations
4. Aggregates probabilities across all groups for a team
"""

import json
import pytest
from pathlib import Path

from wc_draw.city_probabilities import (
    parse_group_stage_details,
    calculate_pot_city_probabilities,
    calculate_position_city_probabilities,
    build_complete_city_probability_map,
    calculate_team_city_probabilities,
)
from wc_draw.group_positions import get_position_for_pot


class TestParseGroupStageDetails:
    """Test parsing of group stage match details."""

    def test_parse_all_groups(self):
        """Should parse all 12 groups."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        group_data = parse_group_stage_details(details_file)

        assert len(group_data) == 12
        for group in "ABCDEFGHIJKL":
            assert group in group_data

    def test_host_groups_identified(self):
        """Should identify groups A, B, D as host groups."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        group_data = parse_group_stage_details(details_file)

        # Host groups
        assert group_data["A"]["is_host"] is True
        assert group_data["B"]["is_host"] is True
        assert group_data["D"]["is_host"] is True

        # Non-host groups
        assert group_data["C"]["is_host"] is False
        assert group_data["E"]["is_host"] is False

    def test_all_groups_have_six_matches(self):
        """Each group should have 6 matches."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        group_data = parse_group_stage_details(details_file)

        for group, data in group_data.items():
            assert len(data["matches"]) == 6, f"Group {group} should have 6 matches"


class TestPositionCityProbabilities:
    """Test city probability calculations for positions."""

    def test_host_group_position_100_percent(self):
        """Host group positions should have 100% for their assigned cities."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        group_data = parse_group_stage_details(details_file)

        # Group A, Position 2 (Pot 3) should have 100% for its 3 match cities
        city_probs = calculate_position_city_probabilities("A", 2, group_data)

        # Should have exactly 3 cities (one per match)
        assert len(city_probs) == 3

        # All should be 100%
        for city, prob in city_probs.items():
            assert prob == 1.0, f"Host group position should have 100% probability, got {prob}"

    def test_non_host_group_position_probabilities(self):
        """Non-host group positions should have < 100% for most cities."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        group_data = parse_group_stage_details(details_file)

        # Group C, Position 4 (Pot 3) - non-host group
        city_probs = calculate_position_city_probabilities("C", 4, group_data)

        # Should have probabilities (not all 100%)
        assert len(city_probs) > 0

        # At least one city should be < 100% (due to match pairs)
        has_partial = any(0 < prob < 1.0 for prob in city_probs.values())
        assert has_partial, "Non-host group should have some partial probabilities"


class TestPotCityProbabilities:
    """Test city probabilities for (group, pot) combinations."""

    def test_pot3_group_a_uses_position_2(self):
        """Pot 3 in Group A should use position A2."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        group_data = parse_group_stage_details(details_file)

        # Verify mapping
        position = get_position_for_pot("A", 3)
        assert position == 2, "Pot 3 should map to position 2 in Group A"

        # Get city probabilities for Pot 3 in Group A
        pot3_probs = calculate_pot_city_probabilities("A", 3, group_data)
        pos2_probs = calculate_position_city_probabilities("A", 2, group_data)

        # Should be identical
        assert pot3_probs == pos2_probs

    def test_pot2_group_a_uses_position_3(self):
        """Pot 2 in Group A should use position A3."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        group_data = parse_group_stage_details(details_file)

        # Verify mapping
        position = get_position_for_pot("A", 2)
        assert position == 3, "Pot 2 should map to position 3 in Group A"

        # Get city probabilities
        pot2_probs = calculate_pot_city_probabilities("A", 2, group_data)
        pos3_probs = calculate_position_city_probabilities("A", 3, group_data)

        # Should be identical
        assert pot2_probs == pos3_probs


class TestCompleteCityProbabilityMap:
    """Test building complete city probability map."""

    def test_builds_all_combinations(self):
        """Should build map for all 48 (group, pot) combinations."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        city_map = build_complete_city_probability_map(details_file)

        # Should have 12 groups × 4 pots = 48 entries
        assert len(city_map) == 48

        # Verify all combinations exist
        for group in "ABCDEFGHIJKL":
            for pot in [1, 2, 3, 4]:
                assert (group, pot) in city_map

    def test_all_entries_have_city_probs(self):
        """Each (group, pot) entry should have city probabilities."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        city_map = build_complete_city_probability_map(details_file)

        for (group, pot), city_probs in city_map.items():
            assert isinstance(city_probs, dict)
            assert len(city_probs) > 0, f"({group}, {pot}) should have city probabilities"


class TestTeamCityProbabilities:
    """Test team-level city probability calculations."""

    def test_scotland_city_probabilities(self):
        """Test Scotland's city probabilities from FIFA stats."""
        stats_file = Path("fifa_official_stats.json")
        details_file = Path("group-stage-details")

        if not stats_file.exists() or not details_file.exists():
            pytest.skip("Required files not found")

        # Load FIFA stats
        with open(stats_file) as f:
            fifa_stats = json.load(f)

        scotland_groups = fifa_stats["teams"]["Scotland"]

        # Build city probability map
        city_map = build_complete_city_probability_map(details_file)

        # Calculate Scotland's city probabilities (Pot 3)
        scotland_cities = calculate_team_city_probabilities(scotland_groups, 3, city_map)

        # Should have probabilities for multiple cities
        assert len(scotland_cities) > 0

        # All probabilities should be between 0 and 100
        for city, prob in scotland_cities.items():
            assert 0 <= prob <= 100, f"{city} probability {prob} out of range"

        # Group A contribution check
        # Scotland has ~9.08% chance in Group A
        # Group A position 2 (Pot 3) has 100% for 3 cities including Mexico City
        # So Mexico City should have at least 9.08% from Group A alone
        group_a_pct = scotland_groups["A"]
        mexico_city_prob = scotland_cities.get("mexico-city", 0)
        assert mexico_city_prob >= group_a_pct, (
            f"Mexico City prob ({mexico_city_prob}) should be >= "
            f"Group A contribution ({group_a_pct})"
        )

    def test_probabilities_sum_correctly(self):
        """Verify probability calculation is weighted correctly."""
        details_file = Path("group-stage-details")
        if not details_file.exists():
            pytest.skip("group-stage-details file not found")

        city_map = build_complete_city_probability_map(details_file)

        # Test with simple group distribution
        # 100% in Group A only
        group_dist = {chr(65 + i): 0.0 for i in range(12)}  # All zeros
        group_dist["A"] = 100.0

        # Calculate for Pot 3
        city_probs = calculate_team_city_probabilities(group_dist, 3, city_map)

        # Should match exactly the Group A Pot 3 probabilities
        group_a_pot3 = city_map[("A", 3)]

        for city, prob in city_probs.items():
            expected = group_a_pot3.get(city, 0) * 100.0  # Convert to percentage
            assert abs(prob - expected) < 0.01, (
                f"City {city}: expected {expected:.2f}, got {prob:.2f}"
            )


class TestRealWorldData:
    """Test with real FIFA statistics."""

    def test_generated_files_exist(self):
        """Verify output files were generated."""
        json_file = Path("team_city_probabilities.json")
        csv_file = Path("team_city_probabilities.csv")

        # These might not exist in CI, so just warn
        if json_file.exists():
            with open(json_file) as f:
                data = json.load(f)
            assert len(data) > 0, "JSON file should have team data"

        if csv_file.exists():
            with open(csv_file) as f:
                lines = f.readlines()
            assert len(lines) > 1, "CSV should have header + data rows"

    def test_top_teams_have_data(self):
        """Verify top teams have city probability data."""
        json_file = Path("team_city_probabilities.json")
        if not json_file.exists():
            pytest.skip("team_city_probabilities.json not found")

        with open(json_file) as f:
            data = json.load(f)

        top_teams = ["Spain", "Argentina", "France", "England", "Scotland"]

        for team in top_teams:
            assert team in data, f"{team} should be in city probabilities"
            assert len(data[team]) > 0, f"{team} should have city data"
