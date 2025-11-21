from pathlib import Path

from wc_draw.parser import parse_teams_config, parse_slots_config


def test_parse_mixed_team_and_slot_escapes(tmp_path: Path):
    # Create a small CSV that mixes backslash-escaped unicode with literal emoji
    csv_path = tmp_path / "mixed.csv"
    # Use a raw string so backslashes are preserved in the written file
    content = r"""
Mixed,UEFA,4,false,,\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F/🇮🇹
UEFA Playoff X,UEFA,4,false,,\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F/🇮🇹,Wales;Italy
"""  # noqa: E501
    csv_path.write_text(content.strip() + "\n", encoding="utf-8")

    pots = parse_teams_config(str(csv_path))
    # Ensure the team flag was unescaped into real Unicode and preserves the '/' separator
    team = pots[4][0]
    expected = "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f/🇮🇹"
    assert team.flag == expected

    slots = parse_slots_config(str(csv_path))
    # There should be one playoff slot and its flags should be decoded similarly
    assert len(slots) == 1
    slot = slots[0]
    assert slot.flags == expected
