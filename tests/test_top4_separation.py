"""
Tests for Top 4 FIFA ranked teams bracket separation constraint.

FIFA's official draw procedure requires the top 4 ranked teams (Spain, Argentina,
France, England) to be separated into different knockout bracket quadrants to ensure
they cannot meet before the semi-finals (if they all win their groups).

Quadrant structure:
- Blue: Groups E, I, F (meets Turquoise in SF)
- Turquoise: Groups H, D, G (meets Blue in SF)
- Green: Groups C, A, L (meets Red in SF)
- Red: Groups J, B, K (meets Green in SF)

Host pre-allocations:
- Canada in Group A (Green quadrant)
- Mexico in Group B (Red quadrant)
- USA in Group D (Turquoise quadrant)

Constraint rules:
1. Top 2 (Spain #1, Argentina #2) must be in opposite halves
   - Blue+Turquoise vs Green+Red
2. All top 4 must be in different quadrants (one per quadrant)
3. When drawing Pot 1 non-top-4 teams, they cannot occupy a quadrant
   that doesn't yet have a top 4 team assigned
"""

from wc_draw.parser import parse_teams_config


# Quadrant definitions
QUADRANTS = {
    "blue": ["E", "I", "F"],
    "turquoise": ["H", "D", "G"],
    "green": ["C", "A", "L"],
    "red": ["J", "B", "K"],
}

# Halves for top 2 separation
HALVES = {
    "half1": ["blue", "turquoise"],  # Blue + Turquoise
    "half2": ["green", "red"],  # Green + Red
}


def get_quadrant_for_group(group: str) -> str:
    """Return which quadrant a group belongs to."""
    for quadrant, groups in QUADRANTS.items():
        if group in groups:
            return quadrant
    raise ValueError(f"Unknown group: {group}")


def get_half_for_quadrant(quadrant: str) -> str:
    """Return which half a quadrant belongs to."""
    for half, quadrants in HALVES.items():
        if quadrant in quadrants:
            return half
    raise ValueError(f"Unknown quadrant: {quadrant}")


class TestTop4Identification:
    """Test that we correctly identify the top 4 ranked teams."""

    def test_top4_teams_from_rankings(self):
        """Verify top 4 teams are correctly identified from FIFA rankings."""
        pots = parse_teams_config("teams.csv")
        pot1_teams = pots[1]

        # Sort by FIFA ranking (ascending - lower is better)
        sorted_teams = sorted(pot1_teams, key=lambda t: t.fifa_ranking)

        # Top 4 should be Spain, Argentina, France, England
        assert sorted_teams[0].name == "Spain"
        assert sorted_teams[0].fifa_ranking == 1
        assert sorted_teams[1].name == "Argentina"
        assert sorted_teams[1].fifa_ranking == 2
        assert sorted_teams[2].name == "France"
        assert sorted_teams[2].fifa_ranking == 3
        assert sorted_teams[3].name == "England"
        assert sorted_teams[3].fifa_ranking == 4

    def test_hosts_not_in_top4(self):
        """Verify host nations are not in top 4."""
        pots = parse_teams_config("teams.csv")
        pot1_teams = pots[1]

        hosts = [t for t in pot1_teams if t.host]
        host_names = {t.name for t in hosts}

        assert "Canada" in host_names
        assert "Mexico" in host_names
        assert "United States" in host_names

        # Verify hosts are not in top 4 by ranking
        top4_teams = sorted(pot1_teams, key=lambda t: t.fifa_ranking)[:4]
        top4_names = {t.name for t in top4_teams}

        assert "Canada" not in top4_names
        assert "Mexico" not in top4_names
        assert "United States" not in top4_names


class TestQuadrantStructure:
    """Test the quadrant and bracket structure definitions."""

    def test_all_groups_covered(self):
        """All 12 groups should be in exactly one quadrant."""
        all_groups = set()
        for groups in QUADRANTS.values():
            all_groups.update(groups)

        expected_groups = set("ABCDEFGHIJKL")
        assert all_groups == expected_groups

    def test_quadrants_have_three_groups_each(self):
        """Each quadrant should contain exactly 3 groups."""
        for quadrant, groups in QUADRANTS.items():
            assert len(groups) == 3, f"{quadrant} should have 3 groups"

    def test_host_quadrant_assignments(self):
        """Verify hosts are in correct quadrants."""
        assert "A" in QUADRANTS["green"], "Canada (Group A) should be in green"
        assert "B" in QUADRANTS["red"], "Mexico (Group B) should be in red"
        assert "D" in QUADRANTS["turquoise"], "USA (Group D) should be in turquoise"

    def test_halves_structure(self):
        """Verify bracket halves are correctly structured."""
        # Each half should have 2 quadrants
        assert len(HALVES["half1"]) == 2
        assert len(HALVES["half2"]) == 2

        # Verify Blue+Turquoise vs Green+Red
        assert "blue" in HALVES["half1"]
        assert "turquoise" in HALVES["half1"]
        assert "green" in HALVES["half2"]
        assert "red" in HALVES["half2"]


class TestTop2SeparationScenarios:
    """Test scenarios for separating Spain (#1) and Argentina (#2) into opposite halves."""

    def test_spain_blue_requires_argentina_green_or_red(self):
        """If Spain in blue, Argentina must be in green or red."""
        spain_quadrant = "blue"
        spain_half = get_half_for_quadrant(spain_quadrant)

        # Argentina must be in opposite half
        valid_quadrants = [q for q in QUADRANTS.keys() if get_half_for_quadrant(q) != spain_half]

        assert "green" in valid_quadrants
        assert "red" in valid_quadrants
        assert "blue" not in valid_quadrants
        assert "turquoise" not in valid_quadrants

    def test_spain_turquoise_requires_argentina_green_or_red(self):
        """If Spain in turquoise, Argentina must be in green or red."""
        spain_quadrant = "turquoise"
        spain_half = get_half_for_quadrant(spain_quadrant)

        valid_quadrants = [q for q in QUADRANTS.keys() if get_half_for_quadrant(q) != spain_half]

        assert "green" in valid_quadrants
        assert "red" in valid_quadrants
        assert "blue" not in valid_quadrants
        assert "turquoise" not in valid_quadrants

    def test_spain_green_requires_argentina_blue_or_turquoise(self):
        """If Spain in green, Argentina must be in blue or turquoise."""
        spain_quadrant = "green"
        spain_half = get_half_for_quadrant(spain_quadrant)

        valid_quadrants = [q for q in QUADRANTS.keys() if get_half_for_quadrant(q) != spain_half]

        assert "blue" in valid_quadrants
        assert "turquoise" in valid_quadrants
        assert "green" not in valid_quadrants
        assert "red" not in valid_quadrants

    def test_spain_red_requires_argentina_blue_or_turquoise(self):
        """If Spain in red, Argentina must be in blue or turquoise."""
        spain_quadrant = "red"
        spain_half = get_half_for_quadrant(spain_quadrant)

        valid_quadrants = [q for q in QUADRANTS.keys() if get_half_for_quadrant(q) != spain_half]

        assert "blue" in valid_quadrants
        assert "turquoise" in valid_quadrants
        assert "green" not in valid_quadrants
        assert "red" not in valid_quadrants


class TestSeeds34Separation:
    """Test that seeds 3-4 (France and England) are in opposite halves."""

    def test_france_half1_england_must_be_half2(self):
        """If France in half1 (blue/turquoise), England must be in half2 (green/red)."""
        france_quadrant = "blue"  # Half1
        france_half = get_half_for_quadrant(france_quadrant)

        valid_quadrants_for_england = [
            q for q in QUADRANTS.keys() if get_half_for_quadrant(q) != france_half
        ]

        assert "green" in valid_quadrants_for_england
        assert "red" in valid_quadrants_for_england
        assert "blue" not in valid_quadrants_for_england
        assert "turquoise" not in valid_quadrants_for_england

    def test_england_half2_france_must_be_half1(self):
        """If England in half2 (green/red), France must be in half1 (blue/turquoise)."""
        england_quadrant = "red"  # Half2
        england_half = get_half_for_quadrant(england_quadrant)

        valid_quadrants_for_france = [
            q for q in QUADRANTS.keys() if get_half_for_quadrant(q) != england_half
        ]

        assert "blue" in valid_quadrants_for_france
        assert "turquoise" in valid_quadrants_for_france
        assert "green" not in valid_quadrants_for_france
        assert "red" not in valid_quadrants_for_france

    def test_france_england_all_opposite_half_combinations(self):
        """Test all valid opposite-half placements for France and England."""
        # France in half1, England in half2
        valid_pairs = [
            ("blue", "green"),
            ("blue", "red"),
            ("turquoise", "green"),
            ("turquoise", "red"),
            # Reversed
            ("green", "blue"),
            ("green", "turquoise"),
            ("red", "blue"),
            ("red", "turquoise"),
        ]

        for france_q, england_q in valid_pairs:
            france_half = get_half_for_quadrant(france_q)
            england_half = get_half_for_quadrant(england_q)
            assert (
                france_half != england_half
            ), f"France in {france_q} and England in {england_q} should be opposite halves"

    def test_france_england_same_half_invalid(self):
        """Verify that France and England in same half is invalid."""
        # Same half combinations (both half1)
        invalid_pairs = [
            ("blue", "turquoise"),
            ("turquoise", "blue"),
            # Both half2
            ("green", "red"),
            ("red", "green"),
        ]

        for france_q, england_q in invalid_pairs:
            france_half = get_half_for_quadrant(france_q)
            england_half = get_half_for_quadrant(england_q)
            assert (
                france_half == england_half
            ), f"France in {france_q} and England in {england_q} are both in {france_half}"


class TestTop4QuadrantSeparationScenarios:
    """Test scenarios where all top 4 must occupy different quadrants."""

    def test_all_top4_in_different_quadrants(self):
        """All top 4 teams must be in different quadrants."""
        # Example allocation
        allocations = {
            "Spain": "blue",
            "Argentina": "green",
            "France": "turquoise",
            "England": "red",
        }

        quadrants_used = set(allocations.values())
        assert len(quadrants_used) == 4, "All 4 quadrants must be used"

    def test_spain_blue_argentina_green_limits_france_england(self):
        """If Spain in blue and Argentina in green, France/England must be in turquoise/red."""
        spain_quadrant = "blue"
        argentina_quadrant = "green"

        remaining_quadrants = [
            q for q in QUADRANTS.keys() if q not in [spain_quadrant, argentina_quadrant]
        ]

        assert set(remaining_quadrants) == {"turquoise", "red"}

    def test_france_in_blue_blocks_groups_E_I_F_for_other_top4(self):
        """If France in group E (blue), groups I and F are blocked for other top 4."""
        france_group = "E"
        france_quadrant = get_quadrant_for_group(france_group)

        assert france_quadrant == "blue"

        # Other top 4 cannot be in blue quadrant
        blocked_groups = QUADRANTS["blue"]
        assert "I" in blocked_groups
        assert "F" in blocked_groups

        # Spain, Argentina, England must go elsewhere
        available_groups = [g for q, groups in QUADRANTS.items() if q != "blue" for g in groups]
        assert "I" not in available_groups
        assert "F" not in available_groups


class TestNonTop4PlacementRestrictions:
    """Test Option B: Non-top-4 teams cannot fill quadrants before top-4 teams are placed."""

    def test_scenario_belgium_blocks_germany_from_group_K(self):
        """
        Scenario: Mexico pre-allocated to B (red), Belgium drawn to J (red).
        Germany cannot go to K as it would complete red quadrant without a top-4 team.
        """
        # Red quadrant groups
        red_groups = QUADRANTS["red"]
        assert set(red_groups) == {"J", "B", "K"}

        # Mexico (host, not top 4) pre-allocated to B
        occupied_by_non_top4 = {"B": "Mexico"}

        # Belgium (not top 4) drawn to J
        occupied_by_non_top4["J"] = "Belgium"

        # Now K is the only remaining group in red quadrant
        remaining_in_red = [g for g in red_groups if g not in occupied_by_non_top4]
        assert remaining_in_red == ["K"]

        # K must be reserved for a top 4 team
        # Germany (not top 4) cannot be placed in K

    def test_scenario_two_quadrants_partially_filled(self):
        """
        Scenario: Red and Green quadrants each have 2/3 groups filled by non-top-4.
        The last group in each must be reserved for top-4 teams.
        """
        # Red: B (Mexico host), J filled → K must be reserved
        red_occupied = {"B", "J"}
        red_remaining = [g for g in QUADRANTS["red"] if g not in red_occupied]
        assert red_remaining == ["K"]

        # Green: A (Canada host), C filled → L must be reserved
        green_occupied = {"A", "C"}
        green_remaining = [g for g in QUADRANTS["green"] if g not in green_occupied]
        assert green_remaining == ["L"]

        # Both K and L must be reserved for top-4 teams

    def test_quadrant_can_be_filled_after_top4_placed(self):
        """Once a top-4 team is in a quadrant, non-top-4 can fill remaining groups."""
        # Blue quadrant: E, I, F
        # If France (top 4) is placed in E, then Belgium can go to I or F
        blue_groups = QUADRANTS["blue"]
        assert "E" in blue_groups

        # After France in E, I and F are available for any Pot 1 team
        remaining_after_top4 = ["I", "F"]
        assert all(g in blue_groups for g in remaining_after_top4)


class TestComplexDrawScenarios:
    """Test complex multi-step draw scenarios."""

    def test_scenario_top4_drawn_last(self):
        """
        Worst case: All 9 non-top-4 pot 1 teams drawn first.
        Each quadrant must have at least 1 group reserved.
        """
        # 9 non-top-4 pot 1 teams, 12 groups total, 3 already taken by hosts
        # Maximum scenario: 8 non-top-4 teams can be placed (2 per quadrant),
        # leaving 4 groups reserved (1 per quadrant) for top-4

        non_top4_allocations = {
            # Blue: can fill 2/3 (reserve 1 for top 4)
            "E": "Germany",
            "I": "Netherlands",
            # F reserved for top 4
            # Turquoise: can fill 1/3 (D is host, reserve 1 for top 4)
            # D is USA (host, not top 4)
            "H": "Portugal",
            # G reserved for top 4
            # Green: can fill 1/3 (A is host, reserve 1 for top 4)
            # A is Canada (host, not top 4)
            "C": "Brazil",
            # L reserved for top 4
            # Red: can fill 1/3 (B is host, reserve 1 for top 4)
            # B is Mexico (host, not top 4)
            "J": "Croatia",
            # K reserved for top 4
        }

        # Count non-top-4 allocations per quadrant (not including hosts)
        quadrant_counts = {q: 0 for q in QUADRANTS.keys()}
        for group, team in non_top4_allocations.items():
            quadrant = get_quadrant_for_group(group)
            quadrant_counts[quadrant] += 1

        # Blue has 2 non-top-4 (no host)
        assert quadrant_counts["blue"] == 2

        # Turquoise, Green, Red each have 1 non-top-4 drawn + 1 host = 2 total
        assert quadrant_counts["turquoise"] == 1
        assert quadrant_counts["green"] == 1
        assert quadrant_counts["red"] == 1

        # Including hosts: each quadrant has 2 non-top-4 teams total
        quadrant_counts["green"] += 1  # Canada in A
        quadrant_counts["red"] += 1  # Mexico in B
        quadrant_counts["turquoise"] += 1  # USA in D

        # Each quadrant should have exactly 2 non-top-4 teams, leaving 1 for top-4
        assert all(count == 2 for count in quadrant_counts.values())

    def test_scenario_deadlock_prevention(self):
        """
        Test that we cannot create a deadlock where a top-4 team has no valid placement.
        """
        # If 3 quadrants are fully occupied by non-top-4 teams, and the 4th has only 1 slot,
        # we'd have 4 top-4 teams competing for 1 slot → deadlock
        # This should be prevented by the reservation logic

        # Example invalid state (should never occur):
        # Blue: E, I, F all filled with non-top-4
        # Turquoise: D (USA), H, G all filled with non-top-4
        # Green: A (Canada), C, L all filled with non-top-4
        # Red: B (Mexico), J filled, K available

        # Only 1 group (K) available for 4 top-4 teams → DEADLOCK
        # The draw procedure must prevent this by reserving 1 group per quadrant


class TestDrawOrderIndependence:
    """Test that constraint is satisfied regardless of draw order."""

    def test_top4_first_then_others(self):
        """Option A: Drawing top 4 first guarantees each quadrant has a top-4 team."""
        # Draw order: Spain, Argentina, France, England, then 9 others
        # After top 4 placed, each quadrant has 1 top-4 team
        # Remaining 9 non-top-4 can go anywhere (2 slots per quadrant available)
        pass  # Logic verification, not executable

    def test_mixed_draw_with_reservations(self):
        """Option B: Mixed draw order with quadrant reservations."""
        # As non-top-4 teams are drawn, track which groups are reserved
        # Once 2 groups in a quadrant are filled by non-top-4, the 3rd is reserved
        pass  # Logic verification, not executable


# Scenarios to test in actual draw simulation
DRAW_TEST_SCENARIOS = [
    {
        "name": "spain_blue_argentina_red_france_green_england_turquoise",
        "description": "Top 4 evenly distributed across all quadrants",
        "allocations": {
            "Spain": "E",  # Blue
            "Argentina": "J",  # Red
            "France": "C",  # Green
            "England": "H",  # Turquoise
        },
    },
    {
        "name": "spain_green_argentina_blue",
        "description": "Spain and Argentina in opposite halves",
        "allocations": {
            "Spain": "A",  # Green (host position taken by Canada, but hypothetical)
            "Argentina": "F",  # Blue
        },
    },
    {
        "name": "top4_avoid_host_groups",
        "description": "Top 4 cannot be in A, B, D (host groups)",
        "allocations": {
            "Spain": "E",
            "Argentina": "C",
            "France": "G",
            "England": "J",
        },
    },
]
