from pathlib import Path
from typing import Dict, List

import pytest
from wc_draw.parser import parse_teams_config
from wc_draw.draw import run_full_draw


def validate_one_from_each_pot(groups: Dict[str, List]):
    for g, teams in groups.items():
        assert len(teams) == 4, f"Group {g} does not have 4 teams: has {len(teams)}"
        pots = [t.pot for t in teams]
        assert len(set(pots)) == 4, f"Group {g} does not have one from each pot: pots={pots}"


def validate_confederation_rules(groups: Dict[str, List]):
    for g, teams in groups.items():
        # Count only concrete (single-confed) teams first
        counts = {}
        placeholders = []
        for t in teams:
            if "|" in (t.confederation or ""):
                placeholders.append(t)
                continue
            conf = t.confederation
            counts[conf] = counts.get(conf, 0) + 1

        # Check counts for concrete teams
        for conf, cnt in counts.items():
            if conf == "UEFA":
                assert cnt <= 2, f"Group {g} has {cnt} UEFA teams (>2)"
            else:
                assert cnt <= 1, f"Group {g} has {cnt} teams from {conf} (>1)"

        # Now validate placeholders: for each allowed conf in the placeholder,
        # the current concrete counts must be below the placement limit for
        # that conf (this mirrors the eligible_for_group logic used during draw).
        for ph in placeholders:
            allowed = [c.strip() for c in ph.confederation.split("|") if c.strip()]
            for conf in allowed:
                cnt = counts.get(conf, 0)
                limit = 2 if conf == "UEFA" else 1
                assert cnt < limit, (
                    f"Group {g}: placeholder {ph.name} allows {conf} "
                    f"but group already has {cnt} (limit {limit})"
                )


@pytest.mark.slow
def test_run_full_draw_harness_with_several_seeds():
    teams_file = Path(__file__).resolve().parents[1] / "teams.csv"
    pots = parse_teams_config(str(teams_file))
    # Test a broader set of seeds (include known reproducers plus a range)
    seeds = [1769482225, 42, 123456789] + list(range(2000))

    # Prepare statistics collectors
    teams = [t for p in pots.values() for t in p]
    team_names = [t.name for t in teams]
    total_runs = 0

    # group_counts[team][group] = count
    group_counts = {name: {chr(ord("A") + i): 0 for i in range(12)} for name in team_names}
    # pair_counts[team][other] = count (other != team)
    pair_counts = {name: {other: 0 for other in team_names if other != name} for name in team_names}

    for seed in seeds:
        try:
            groups, used_seed = run_full_draw(pots, seed=seed, max_attempts=2000)
        except RuntimeError as e:
            # Retry with a larger budget and then surface the seed on failure
            try:
                groups, used_seed = run_full_draw(pots, seed=seed, max_attempts=10000)
            except RuntimeError:
                raise AssertionError(f"run_full_draw failed for seed {seed}: {e}")

        # basic invariant: returned seed matches requested
        assert used_seed == seed
        validate_one_from_each_pot(groups)
        validate_confederation_rules(groups)

        # accumulate statistics
        total_runs += 1
        for g, teams_in_group in groups.items():
            names = [t.name for t in teams_in_group]
            for name in names:
                group_counts[name][g] += 1
                for other in names:
                    if other == name:
                        continue
                    pair_counts[name][other] += 1

    # After all seeds, compute percentages and write results
    if total_runs > 0:
        stats = {"total_runs": total_runs, "teams": {}}
        for name in team_names:
            gcounts = group_counts[name]
            pcounts = pair_counts[name]
            stats["teams"][name] = {
                "group_pct": {g: round(c / total_runs * 100, 3) for g, c in gcounts.items()},
                "pair_pct": {other: round(c / total_runs * 100, 3) for other, c in pcounts.items()},
            }

        out = Path(__file__).resolve().parents[1] / "draw_stats.json"
        import json

        with open(out, "w") as fh:
            json.dump(stats, fh, indent=2, sort_keys=True)

        # Print a concise top-5 summary per team
        for name in team_names:
            pairs = sorted(stats["teams"][name]["pair_pct"].items(), key=lambda x: -x[1])[:5]
            groups_top = sorted(stats["teams"][name]["group_pct"].items(), key=lambda x: -x[1])[:3]
            print(f"{name}: top pairs -> {pairs}; top groups -> {groups_top}")
