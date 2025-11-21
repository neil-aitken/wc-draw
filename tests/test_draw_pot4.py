import random
from pathlib import Path
from wc_draw.parser import parse_teams_config
from wc_draw.draw import draw_pot1, draw_pot


def test_draw_pot4_inter_paths_avoid_conflicted_groups():
    csv_path = Path(__file__).resolve().parents[1] / "teams.csv"
    pots = parse_teams_config(str(csv_path))

    rng = random.Random(0)

    groups = draw_pot1(pots[1], rng=rng)
    draw_pot(pots[2], groups, rng=rng)
    draw_pot(pots[3], groups, rng=rng)

    # Now place pot4
    draw_pot(pots[4], groups, rng=rng)

    # Find Inter Path slots and ensure their groups do not contain any of the
    # confederations listed in the slot's confederation field.
    for pot4_team in pots[4]:
        if "|" in pot4_team.confederation:
            allowed = [c.strip() for c in pot4_team.confederation.split("|")]
            # find group containing this slot
            found = None
            for g, ts in groups.items():
                if any(t.name == pot4_team.name for t in ts):
                    found = (g, ts)
                    break
            assert found is not None, f"Slot {pot4_team.name} not placed"
            _, ts = found
            for conf in allowed:
                assert all(t.confederation != conf for t in ts if t.name != pot4_team.name), (
                    f"Slot {pot4_team.name} placed into group containing confederation {conf}"
                )
