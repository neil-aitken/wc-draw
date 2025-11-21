import random
from pathlib import Path
from wc_draw.parser import parse_teams_config
from wc_draw.draw import draw_pot1, draw_pot


def confed_counts_ok(groups):
    for g, teams in groups.items():
        # count teams per confederation
        confed_map = {}
        for t in teams:
            confed_map.setdefault(t.confederation, 0)
            confed_map[t.confederation] += 1
        for confed, cnt in confed_map.items():
            if confed == "UEFA":
                if cnt > 2:
                    return False
            else:
                if cnt > 1:
                    return False
    return True


def test_draw_pots_2_and_3_respect_confederation_limits():
    csv_path = Path(__file__).resolve().parents[1] / "teams.csv"
    pots = parse_teams_config(str(csv_path))

    rng = random.Random(0)

    # Start with pot1
    groups = draw_pot1(pots[1], rng=rng)

    # Place pot2
    draw_pot(pots[2], groups, rng=rng)
    # After pot2 placement, groups should have size 2
    assert all(len(v) == 2 for v in groups.values())
    assert confed_counts_ok(groups)

    # Place pot3
    draw_pot(pots[3], groups, rng=rng)
    # After pot3 placement, groups should have size 3
    assert all(len(v) == 3 for v in groups.values())
    assert confed_counts_ok(groups)
