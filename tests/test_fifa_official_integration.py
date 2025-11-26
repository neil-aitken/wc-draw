"""
Integration tests for FIFA official draw constraints with top 4 bracket separation.
"""

import pytest
from wc_draw.config import DrawConfig
from wc_draw.parser import parse_teams_config
from wc_draw.pot_assignment import assign_pots
from wc_draw.draw import run_full_draw
from wc_draw.top4_separation import (
    get_quadrant_for_group,
    get_half_for_quadrant,
    identify_top4_teams,
)


class TestFIFAOfficialConstraints:
    """Test complete draw with FIFA official constraints enabled."""

    def test_official_flag_enables_top4_separation(self):
        """Verify fifa_official_constraints flag enables top 4 bracket separation."""
        teams_by_pot = parse_teams_config("teams.csv")
        config = DrawConfig(fifa_official_constraints=True)
        pots = assign_pots(teams_by_pot, config)

        groups, seed = run_full_draw(pots, seed=42, config=config)

        # Verify draw completed successfully
        assert len(groups) == 12
        assert all(len(teams) == 4 for teams in groups.values())

        # Find top 4 team placements
        top4 = identify_top4_teams(pots[1])
        top4_placements = {}

        for team in top4:
            for grp, teams in groups.items():
                if teams[0].name == team.name:
                    quadrant = get_quadrant_for_group(grp)
                    half = get_half_for_quadrant(quadrant)
                    top4_placements[team.name] = {
                        "group": grp,
                        "quadrant": quadrant,
                        "half": half,
                        "rank": team.fifa_ranking,
                    }
                    break

        # Verify all top 4 are placed
        assert len(top4_placements) == 4

        # Verify all in different quadrants
        quadrants = [p["quadrant"] for p in top4_placements.values()]
        assert len(set(quadrants)) == 4, "Top 4 must be in different quadrants"

        # Verify top 2 (Spain, Argentina) in opposite halves
        spain = next(p for p in top4_placements.values() if p["rank"] == 1)
        argentina = next(p for p in top4_placements.values() if p["rank"] == 2)

        assert spain["half"] != argentina["half"], (
            f"Spain and Argentina must be in opposite halves: "
            f"Spain={spain['half']}, Argentina={argentina['half']}"
        )

    def test_multiple_seeds_satisfy_constraints(self):
        """Test that different seeds all satisfy top 4 constraints."""
        teams_by_pot = parse_teams_config("teams.csv")
        config = DrawConfig(fifa_official_constraints=True)
        pots = assign_pots(teams_by_pot, config)

        test_seeds = [42, 123, 456, 789, 1111]

        for seed_val in test_seeds:
            groups, seed = run_full_draw(pots, seed=seed_val, config=config)

            # Find top 4 placements
            top4 = identify_top4_teams(pots[1])
            placements = {}

            for team in top4:
                for grp, teams in groups.items():
                    if teams[0].name == team.name:
                        quadrant = get_quadrant_for_group(grp)
                        half = get_half_for_quadrant(quadrant)
                        placements[team.fifa_ranking] = {
                            "name": team.name,
                            "quadrant": quadrant,
                            "half": half,
                        }
                        break

            # Check constraints
            quadrants = [p["quadrant"] for p in placements.values()]
            assert len(set(quadrants)) == 4, f"Seed {seed_val}: Not all different quadrants"

            spain = placements[1]  # Rank 1
            argentina = placements[2]  # Rank 2
            assert spain["half"] != argentina["half"], (
                f"Seed {seed_val}: Top 2 not in opposite halves"
            )

    def test_without_official_flag_no_top4_separation(self):
        """Verify that without fifa_official_constraints, no top 4 separation is enforced."""
        teams_by_pot = parse_teams_config("teams.csv")
        config = DrawConfig(fifa_official_constraints=False)  # Disabled
        pots = assign_pots(teams_by_pot, config)

        # Should complete without enforcing top 4 separation
        groups, seed = run_full_draw(pots, seed=42, config=config)

        assert len(groups) == 12
        assert all(len(teams) == 4 for teams in groups.values())

        # Note: We don't assert that constraints are violated, just that
        # the draw completes without the constraint enforcement

    def test_hosts_pre_allocated_correctly(self):
        """Verify host nations are correctly pre-allocated and don't interfere with top 4."""
        teams_by_pot = parse_teams_config("teams.csv")
        config = DrawConfig(fifa_official_constraints=True)
        pots = assign_pots(teams_by_pot, config)

        groups, seed = run_full_draw(pots, seed=42, config=config)

        # Verify all three hosts are allocated in pot 1
        pot1_teams = {grp: teams[0].name for grp, teams in groups.items()}
        host_nations = {"Canada", "Mexico", "United States"}

        hosts_in_draw = set(pot1_teams.values()) & host_nations
        assert len(hosts_in_draw) == 3, f"Expected all 3 hosts in Pot 1, found: {hosts_in_draw}"

        # Verify hosts are not top 4
        top4 = identify_top4_teams(pots[1])
        top4_names = {t.name for t in top4}

        assert not (top4_names & host_nations), "Host nations should not be in top 4"

    def test_top4_teams_identified_correctly(self):
        """Verify top 4 teams are correctly identified from FIFA rankings."""
        pots = parse_teams_config("teams.csv")

        top4 = identify_top4_teams(pots[1])

        assert len(top4) == 4
        assert top4[0].name == "Spain"
        assert top4[0].fifa_ranking == 1
        assert top4[1].name == "Argentina"
        assert top4[1].fifa_ranking == 2
        assert top4[2].name == "France"
        assert top4[2].fifa_ranking == 3
        assert top4[3].name == "England"
        assert top4[3].fifa_ranking == 4

    @pytest.mark.parametrize("seed_val", [42, 123, 456, 789, 1111, 2222, 3333, 4444, 5555, 6666])
    def test_draw_consistency_with_seed(self, seed_val):
        """Test that draws with same seed produce consistent results."""
        teams_by_pot = parse_teams_config("teams.csv")
        config = DrawConfig(fifa_official_constraints=True)
        pots = assign_pots(teams_by_pot, config)

        # Run draw twice with same seed
        groups1, seed1 = run_full_draw(pots, seed=seed_val, config=config)
        groups2, seed2 = run_full_draw(pots, seed=seed_val, config=config)

        # Should produce identical results
        assert seed1 == seed2 == seed_val

        for grp in groups1.keys():
            teams1 = [t.name for t in groups1[grp]]
            teams2 = [t.name for t in groups2[grp]]
            assert teams1 == teams2, f"Group {grp} differs between runs"
