import json
from wc_draw.cli import main


def test_cli_json_output(capsys):
    # Run CLI with --json to get machine-parseable output
    main(["--json"])  # uses default teams.csv in repo
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert "pots" in data and "slots" in data
    pots = data["pots"]
    # check pots 1..4 exist and each has 12 teams
    for pot in ("1", "2", "3", "4"):
        assert pot in pots, f"Pot {pot} missing in CLI output"
        assert len(pots[pot]) == 12, f"Pot {pot} should have 12 teams"

    # total slots expected: 6 (4 UEFA playoff + 2 inter paths)
    assert len(data["slots"]) == 6
    names = {s["name"] for s in data["slots"]}
    assert "UEFA Playoff A" in names
    assert "Inter Path 1" in names
