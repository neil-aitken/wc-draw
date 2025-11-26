#!/usr/bin/env python3
"""Aggregate FIFA official constraints draw statistics from JSONL."""

import json
from collections import defaultdict
from pathlib import Path

def aggregate_fifa_draws(jsonl_path):
    """Aggregate draw statistics from FIFA official JSONL file."""
    
    total_runs = 0
    successes = 0
    group_counts = defaultdict(lambda: defaultdict(int))
    pair_counts = defaultdict(lambda: defaultdict(int))
    
    print(f"Reading {jsonl_path}...")
    with open(jsonl_path, 'r') as fh:
        for line in fh:
            obj = json.loads(line)
            
            # Skip metadata header
            if 'meta' in obj:
                continue
            
            total_runs += 1
            if not obj.get('success', False):
                continue
            
            successes += 1
            groups = obj.get('groups', {})
            
            # Aggregate group occupancy
            for group_label, team_names in groups.items():
                for team_name in team_names:
                    group_counts[team_name][group_label] += 1
            
            # Aggregate pairwise co-occurrence (undirected)
            for group_label, team_names in groups.items():
                for i, team1 in enumerate(team_names):
                    for team2 in team_names[i + 1:]:
                        pair_counts[team1][team2] += 1
                        pair_counts[team2][team1] += 1
    
    # Convert counts to percentages
    teams_stats = {}
    for team in sorted(group_counts.keys()):
        group_pct = {
            grp: (count / successes * 100.0) if successes > 0 else 0.0
            for grp, count in sorted(group_counts[team].items())
        }
        pair_pct = {
            opp: (count / successes * 100.0) if successes > 0 else 0.0
            for opp, count in sorted(pair_counts[team].items())
        }
        teams_stats[team] = {
            'group_pct': group_pct,
            'pair_pct': pair_pct
        }
    
    return {
        'total_runs': total_runs,
        'successes': successes,
        'success_rate': (successes / total_runs) if total_runs > 0 else 0.0,
        'teams': teams_stats
    }

if __name__ == '__main__':
    input_file = Path('seed_scan_fifa_official.jsonl')
    output_file = Path('draw_stats.json')
    
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        exit(1)
    
    print("=" * 70)
    print("FIFA Official Constraints - Statistics Aggregation")
    print("=" * 70)
    
    stats = aggregate_fifa_draws(input_file)
    
    print(f"\nResults:")
    print(f"  Total runs:    {stats['total_runs']:,}")
    print(f"  Successes:     {stats['successes']:,}")
    print(f"  Success rate:  {stats['success_rate']:.2%}")
    print(f"  Teams:         {len(stats['teams'])}")
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2, sort_keys=True)
    
    print(f"\n✓ Wrote statistics to {output_file}")
    print("=" * 70)
    
    # Show top 4 summary
    top4 = ['Spain', 'Argentina', 'France', 'England']
    print("\nTop 4 Teams - Most Likely Groups:")
    print("=" * 70)
    for team in top4:
        if team in stats['teams']:
            team_groups = stats['teams'][team]['group_pct']
            top_groups = sorted(team_groups.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"{team:12} ", end="")
            for grp, pct in top_groups:
                print(f"{grp}:{pct:5.2f}%  ", end="")
            print()
    
    # Show sample opponent pairings
    print("\nSample Opponent Probabilities (Argentina):")
    print("=" * 70)
    if 'Argentina' in stats['teams']:
        arg_pairs = stats['teams']['Argentina']['pair_pct']
        top_opponents = sorted(arg_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
        for opp, pct in top_opponents:
            print(f"  {opp:20} {pct:6.2f}%")
