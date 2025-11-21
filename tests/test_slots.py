import tempfile
import os
from wc_draw.parser import parse_slots_config


def test_parse_uefa_playoff_slots():
    sample_data = """# name, confederation, pot, host, fixed_group, candidates
UEFA Playoff A,UEFA,4,false,,Wales;Bosnia;Italy;Northern Ireland
UEFA Playoff B,UEFA,4,false,,Ukraine;Sweden;Poland;Albania
UEFA Playoff C,UEFA,4,false,,Slovakia;Kosovo;Turkey;Romania
UEFA Playoff D,UEFA,4,false,,Czechia;Ireland;Denmark;Macedonia
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(sample_data)
        tmp_path = tmp.name
    try:
        slots = parse_slots_config(tmp_path)
        assert len(slots) == 4
        names = [s.name for s in slots]
        assert "UEFA Playoff A" in names
        assert "UEFA Playoff B" in names
        assert all(s.pot == 4 for s in slots)
        assert all(s.allowed_confederations == ["UEFA"] for s in slots)
        # verify candidates parsed
        assert slots[0].candidates == ["Wales", "Bosnia", "Italy", "Northern Ireland"]
        assert slots[1].candidates == ["Ukraine", "Sweden", "Poland", "Albania"]
    finally:
        os.remove(tmp_path)


def test_parse_interconfed_slots():
    sample_data = """# name, confederation, pot, host, fixed_group, candidates
Inter Path 1,CAF|OFC|CONCACAF,4,false,,DR Congo;New Caledonia;Jamaica
Inter Path 2,AFC|CONMEBOL|CONCACAF,4,false,,Iraq;Bolivia;Suriname
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(sample_data)
        tmp_path = tmp.name
    try:
        slots = parse_slots_config(tmp_path)
        assert len(slots) == 2
        p1 = next(s for s in slots if s.name == "Inter Path 1")
        p2 = next(s for s in slots if s.name == "Inter Path 2")
        assert p1.allowed_confederations == ["CAF", "OFC", "CONCACAF"]
        assert p1.candidates == ["DR Congo", "New Caledonia", "Jamaica"]
        assert p2.allowed_confederations == ["AFC", "CONMEBOL", "CONCACAF"]
        assert p2.candidates == ["Iraq", "Bolivia", "Suriname"]
    finally:
        os.remove(tmp_path)
