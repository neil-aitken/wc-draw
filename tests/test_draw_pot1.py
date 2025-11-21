import random
from pathlib import Path
from wc_draw.parser import parse_teams_config
from wc_draw.draw import draw_pot1


def test_draw_pot1_hosts_and_counts():
    csv_path = Path(__file__).resolve().parents[1] / "teams.csv"
    pots = parse_teams_config(str(csv_path))
    pot1 = pots[1]
    rng = random.Random(0)
    groups = draw_pot1(pot1, rng=rng)

    # All groups A..L should exist and have exactly one pot1 team
    assert len(groups) == 12
    for g in [chr(ord("A") + i) for i in range(12)]:
        assert g in groups
        assert len(groups[g]) == 1

    # Hosts placed in fixed groups
    # Mexico -> A, Canada -> B, United States -> D per teams.csv
    assert any(t.name == "Mexico" for t in groups["A"])
    assert any(t.name == "Canada" for t in groups["B"])
    assert any(t.name == "United States" for t in groups["D"])

    # Ensure pot1 now has been fully distributed (implicit by group sizes)
    # (No further assertion required here; group sizes already validate distribution)
