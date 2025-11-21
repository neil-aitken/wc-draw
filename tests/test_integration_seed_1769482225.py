import random
from pathlib import Path

from wc_draw.parser import parse_teams_config
from wc_draw.draw import draw_pot1, draw_pot


def test_seed_1769482225_group_j_has_two_pot4_teams():
    """Integration test reproducing the reported failure for seed 1769482225.

    The test performs the full draw in the same order used by the CLI
    (pot1, pot4, pot2, pot3) and asserts that group 'J' contains two teams
    from pot 4. This captures the regression so it can be fixed later.
    """
    teams_file = Path(__file__).resolve().parents[1] / "teams.csv"
    pots = parse_teams_config(str(teams_file))

    rng = random.Random(1769482225)

    groups = draw_pot1(pots[1], rng=rng)
    # place pot4 early as the CLI does for a full draw
    draw_pot(pots[4], groups, rng=rng, allow_early=True)
    draw_pot(pots[2], groups, rng=rng, allow_early=True)
    draw_pot(pots[3], groups, rng=rng, allow_early=True)

    pot4_count_in_j = sum(1 for t in groups.get("J", []) if t.pot == 4)
    assert pot4_count_in_j == 1, f"expected 1 pot-4 team in group J, got {pot4_count_in_j}"
