from pathlib import Path
from wc_draw.parser import parse_teams_config


def test_pots_have_12_teams_each():
    csv_path = Path(__file__).resolve().parents[1] / "teams.csv"
    pots = parse_teams_config(str(csv_path))
    # We expect 4 pots numbered 1..4
    for pot in (1, 2, 3, 4):
        assert pot in pots, f"Pot {pot} missing"
        assert len(pots[pot]) == 12, f"Pot {pot} should have 12 teams, has {len(pots[pot])}"
    # Total teams should be 48
    total = sum(len(v) for v in pots.values())
    assert total == 48, f"Total teams should be 48, found {total}"
