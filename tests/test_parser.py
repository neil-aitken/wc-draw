import tempfile
import os
from wc_draw.parser import parse_teams_config


def test_parse_non_host_team():
    sample_data = """# team_name, confederation, pot, host, fixed_group
Argentina,CONMEBOL,1,false,
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(sample_data)
        tmp_path = tmp.name
    try:
        pots = parse_teams_config(tmp_path)
        assert 1 in pots
        assert len(pots[1]) == 1
        team = pots[1][0]
        assert team.name == "Argentina"
        assert team.confederation == "CONMEBOL"
        assert team.pot == 1
        assert team.host is False
        assert team.fixed_group is None
    finally:
        os.remove(tmp_path)


def test_parse_host_team():
    sample_data = """# team_name, confederation, pot, host, fixed_group
Mexico,CONCACAF,1,true,A
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(sample_data)
        tmp_path = tmp.name
    try:
        pots = parse_teams_config(tmp_path)
        assert 1 in pots
        assert len(pots[1]) == 1
        team = pots[1][0]
        assert team.name == "Mexico"
        assert team.confederation == "CONCACAF"
        assert team.pot == 1
        assert team.host is True
        assert team.fixed_group == "A"
    finally:
        os.remove(tmp_path)


def test_parse_dict_by_pot():
    sample_data = """# team_name, confederation, pot, host, fixed_group
Argentina,CONMEBOL,1,false,
Japan,AFC,2,false,
Mexico,CONCACAF,1,true,A
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(sample_data)
        tmp_path = tmp.name
    try:
        pots = parse_teams_config(tmp_path)
        assert isinstance(pots, dict)
        assert 1 in pots and 2 in pots
        assert len(pots[1]) == 2
        assert len(pots[2]) == 1
        team_a = pots[1][0]
        team_b = pots[1][1]
        team_c = pots[2][0]
        assert team_a.name == "Argentina"
        assert team_a.confederation == "CONMEBOL"
        assert team_a.pot == 1
        assert team_a.host is False
        assert team_a.fixed_group is None
        assert team_b.name == "Mexico"
        assert team_b.confederation == "CONCACAF"
        assert team_b.pot == 1
        assert team_b.host is True
        assert team_b.fixed_group == "A"
        assert team_c.name == "Japan"
        assert team_c.confederation == "AFC"
        assert team_c.pot == 2
        assert team_c.host is False
        assert team_c.fixed_group is None
    finally:
        os.remove(tmp_path)
