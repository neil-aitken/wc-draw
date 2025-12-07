"""
Parallel Monte Carlo tournament simulator.

Uses multiprocessing to run simulations across multiple CPU cores
for significant performance improvement.
"""

import json
import multiprocessing as mp
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import numpy as np
from tqdm import tqdm

from .config import (
    GROUPS, NUM_SIMULATIONS, SIMULATION_RESULTS_FILE,
    PLAYOFF_TEAM_GROUPS, UEFA_PLAYOFFS, IC_PLAYOFFS, PLAYOFF_PATH_TO_GROUP
)


@dataclass
class WorkerResult:
    """Result from a single worker process."""
    outcomes: Dict[str, Dict[str, int]]
    conquerors: Dict[str, Dict[str, int]]
    team_groups: Dict[str, Optional[str]]
    num_simulations: int


def _simulate_batch(args: Tuple) -> WorkerResult:
    """
    Run a batch of simulations in a worker process.
    
    Args:
        args: Tuple of (num_sims, worker_id, seed_entropy)
    
    Returns:
        WorkerResult with aggregated outcomes and conquerors
    """
    num_sims, worker_id, seed_entropy = args
    
    # Initialize RNG with worker-specific seed
    seed_seq = np.random.SeedSequence(seed_entropy)
    rng = np.random.default_rng(seed_seq)
    np.random.seed(rng.integers(0, 2**31))
    
    # Import here to avoid issues with multiprocessing
    from .config import GROUPS as CONFIG_GROUPS, PLAYOFF_TEAM_GROUPS as CONFIG_PLAYOFF_TEAM_GROUPS
    from .playoffs import simulate_all_playoffs, replace_playoff_placeholders
    from .group_stage import simulate_all_groups
    from .knockout import simulate_knockout
    
    outcomes: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    conquerors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    team_groups: Dict[str, Optional[str]] = {}
    
    # Pre-populate groups for playoff team
    for team, group in CONFIG_PLAYOFF_TEAM_GROUPS.items():
        team_groups[team] = group
    
    for _ in range(num_sims):
        # Simulate playoffs
        playoff_result = simulate_all_playoffs()
        groups = replace_playoff_placeholders(CONFIG_GROUPS, playoff_result)
        
        # Record playoff losers
        for team in playoff_result.losers:
            outcomes[team]['Did Not Qualify'] += 1
            if team not in team_groups:
                team_groups[team] = PLAYOFF_TEAM_GROUPS.get(team)
        
        # Record group assignments
        for letter, teams in groups.items():
            for team in teams:
                if team not in team_groups:
                    team_groups[team] = letter
        
        # Simulate group stage
        group_results = simulate_all_groups(groups)
        
        # Record group positions
        for letter, result in group_results.items():
            standings = result.standings
            outcomes[standings[0].team]['Group 1st'] += 1
            outcomes[standings[1].team]['Group 2nd'] += 1
        
        # Simulate knockout stage
        result = simulate_knockout(group_results)
        
        # Record tournament outcomes
        outcomes[result.champion]['Winner'] += 1
        outcomes[result.runner_up]['Runner-up'] += 1
        outcomes[result.third_place]['3rd Place'] += 1
        outcomes[result.fourth_place]['4th Place'] += 1
        
        for team in result.quarterfinalists:
            outcomes[team]['QF Exit'] += 1
        
        for team in result.r16_exits:
            outcomes[team]['R16 Exit'] += 1
        
        for team in result.r32_exits:
            outcomes[team]['R32 Exit'] += 1
        
        for team in result.third_place_eliminated:
            outcomes[team]['Group 3rd'] += 1
        
        for letter, teams in result.group_exits.items():
            for team in teams:
                outcomes[team]['Group 4th'] += 1
        
        # Record conquerors from knockout results
        # R32 exits
        for match_num, ko_result in result.r32_results.items():
            conquerors[ko_result.loser][ko_result.winner] += 1
        
        # R16 exits
        for match_num, ko_result in result.r16_results.items():
            conquerors[ko_result.loser][ko_result.winner] += 1
        
        # QF exits
        for match_num, ko_result in result.qf_results.items():
            conquerors[ko_result.loser][ko_result.winner] += 1
        
        # SF exits (losers go to 3rd place match)
        for match_num, ko_result in result.sf_results.items():
            conquerors[ko_result.loser][ko_result.winner] += 1
        
        # Final loser
        conquerors[result.final_result.loser][result.final_result.winner] += 1
        
        # Third place match loser
        conquerors[result.third_place_result.loser][result.third_place_result.winner] += 1
    
    # Convert defaultdicts to regular dicts for pickling
    return WorkerResult(
        outcomes={k: dict(v) for k, v in outcomes.items()},
        conquerors={k: dict(v) for k, v in conquerors.items()},
        team_groups=team_groups,
        num_simulations=num_sims,
    )


def _merge_results(results: List[WorkerResult]) -> Tuple[Dict, Dict, Dict, int]:
    """Merge results from multiple workers."""
    merged_outcomes: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    merged_conquerors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    merged_groups: Dict[str, Optional[str]] = {}
    total_sims = 0

    for result in results:
        total_sims += result.num_simulations

        # Merge outcomes
        for team, counts in result.outcomes.items():
            for outcome, count in counts.items():
                merged_outcomes[team][outcome] += count

        # Merge conquerors
        for team, eliminators in result.conquerors.items():
            for eliminator, count in eliminators.items():
                merged_conquerors[team][eliminator] += count

        # Merge groups (should be consistent across workers)
        merged_groups.update(result.team_groups)

    return (
        {k: dict(v) for k, v in merged_outcomes.items()},
        {k: dict(v) for k, v in merged_conquerors.items()},
        merged_groups,
        total_sims,
    )


def _build_groups_metadata() -> Dict:
    """Build metadata about groups including playoff team mappings."""
    metadata = {
        'groups': {},
        'playoff_paths': {},
    }

    # Add group info with resolved playoff teams
    for letter, teams in GROUPS.items():
        group_info = {
            'teams': [],
            'has_playoff_slot': False,
        }

        for team in teams:
            if team.startswith('UEFA Path') or team.startswith('IC Path'):
                group_info['has_playoff_slot'] = True
                # Get all teams competing for this slot
                if team.startswith('UEFA Path'):
                    path = team.split()[-1]  # e.g., "A" from "UEFA Path A"
                    playoff_teams = UEFA_PLAYOFFS.get(path, [])
                else:
                    path = team.split()[-1]  # e.g., "1" from "IC Path 1"
                    playoff_teams = IC_PLAYOFFS.get(path, [])

                group_info['teams'].append({
                    'slot': team,
                    'playoff_teams': playoff_teams,
                })
            else:
                group_info['teams'].append({
                    'team': team,
                })

        metadata['groups'][letter] = group_info

    # Add playoff path info
    for path, teams in UEFA_PLAYOFFS.items():
        metadata['playoff_paths'][f'UEFA Path {path}'] = {
            'type': 'UEFA',
            'teams': teams,
            'target_group': PLAYOFF_PATH_TO_GROUP[f'UEFA Path {path}'],
        }

    for path, teams in IC_PLAYOFFS.items():
        metadata['playoff_paths'][f'IC Path {path}'] = {
            'type': 'IC',
            'teams': teams,
            'target_group': PLAYOFF_PATH_TO_GROUP[f'IC Path {path}'],
        }

    return metadata


def run_parallel_simulation(
    num_simulations: int = NUM_SIMULATIONS,
    num_workers: Optional[int] = None,
    show_progress: bool = True,
    save: bool = True,
    seed: Optional[int] = None,
) -> Dict:
    """
    Run Monte Carlo simulation using multiple processes.

    Args:
        num_simulations: Total number of simulations to run
        num_workers: Number of worker processes (default: CPU count)
        show_progress: Whether to show progress bar
        save: Whether to save results to file
        seed: Random seed for reproducibility

    Returns:
        Dict with simulation results
    """
    if num_workers is None:
        num_workers = mp.cpu_count()

    # Create reproducible but independent random streams
    if seed is None:
        seed = int(np.random.SeedSequence().entropy) % (2**31)

    base_seq = np.random.SeedSequence(seed)
    spawned_seqs = base_seq.spawn(num_workers)

    # Divide simulations among workers
    sims_per_worker = num_simulations // num_workers
    remainder = num_simulations % num_workers

    worker_configs = []
    for i in range(num_workers):
        n = sims_per_worker + (1 if i < remainder else 0)
        # Get entropy from spawned sequence
        entropy = spawned_seqs[i].entropy
        if isinstance(entropy, np.ndarray):
            entropy = int(entropy[0]) if len(entropy) > 0 else i
        worker_configs.append((n, i, entropy))

    print(f"Running {num_simulations:,} simulations across {num_workers} workers...")

    # Run simulations in parallel
    with mp.Pool(num_workers) as pool:
        if show_progress:
            results = list(tqdm(
                pool.imap(_simulate_batch, worker_configs),
                total=num_workers,
                desc="Workers completed"
            ))
        else:
            results = pool.map(_simulate_batch, worker_configs)

    # Merge results from all workers
    outcomes, conquerors, team_groups, total_sims = _merge_results(results)

    # Load team confederation data
    from .match_engine import get_simulator
    sim = get_simulator()
    team_confederations = {
        team: data.get('confederation', 'Unknown')
        for team, data in sim._elo_ratings.items()
    }

    # Build output structure
    teams_output = {}
    for team, outcome_counts in outcomes.items():
        group = team_groups.get(team)
        confed = team_confederations.get(team, 'Unknown')

        # Calculate probabilities
        probs = {k: v / total_sims for k, v in outcome_counts.items()}

        # Get conquerors for this team
        team_conquerors = conquerors.get(team, {})
        conqueror_probs = {k: v / total_sims for k, v in team_conquerors.items()}

        teams_output[team] = {
            'team': team,
            'group': group,
            'confederation': confed,
            'simulations': total_sims,
            'outcome_counts': outcome_counts,
            'outcome_probabilities': probs,
            'conqueror_counts': team_conquerors,
            'conqueror_probabilities': conqueror_probs,
        }

    # Build groups metadata for UI
    groups_metadata = _build_groups_metadata()

    output = {
        'num_simulations': total_sims,
        'seed': seed,
        'num_workers': num_workers,
        'teams': teams_output,
        'groups_metadata': groups_metadata,
    }

    if save:
        filepath = SIMULATION_RESULTS_FILE
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Results saved to {filepath}")

    return output


def print_summary(results: Dict) -> None:
    """Print a summary of simulation results."""
    print("\n" + "=" * 80)
    print("WORLD CUP 2026 SIMULATION RESULTS")
    print("=" * 80)

    num_sims = results['num_simulations']
    num_workers = results.get('num_workers', 1)
    print(f"\nBased on {num_sims:,} simulations ({num_workers} workers)\n")

    # Sort by win probability
    teams = results['teams']
    by_win_prob = sorted(
        teams.items(),
        key=lambda x: x[1]['outcome_probabilities'].get('Winner', 0),
        reverse=True
    )

    print("Top 20 teams by Win Probability:")
    print("-" * 80)
    print(f"{'Rank':<5} {'Team':<20} {'Win%':>7} {'Final%':>8} {'SF%':>8} {'QF%':>8} {'R16%':>8}")
    print("-" * 80)

    for i, (team, data) in enumerate(by_win_prob[:20], 1):
        probs = data['outcome_probabilities']
        win = probs.get('Winner', 0) * 100
        final = (probs.get('Winner', 0) + probs.get('Runner-up', 0)) * 100
        sf = final + (probs.get('3rd Place', 0) + probs.get('4th Place', 0)) * 100
        qf = sf + probs.get('QF Exit', 0) * 100
        r16 = qf + probs.get('R16 Exit', 0) * 100

        print(f"{i:<5} {team:<20} {win:>6.1f}% {final:>7.1f}% {sf:>7.1f}% {qf:>7.1f}% {r16:>7.1f}%")

    print("\n")

    # Group stage exit probabilities
    print("Teams with highest group stage exit probability:")
    print("-" * 60)

    group_exit_prob = []
    for team, data in teams.items():
        probs = data['outcome_probabilities']
        exit_prob = probs.get('Group 3rd', 0) + probs.get('Group 4th', 0)
        if exit_prob > 0.2:
            group_exit_prob.append((team, exit_prob, data['group']))

    group_exit_prob.sort(key=lambda x: -x[1])

    for team, prob, group in group_exit_prob[:15]:
        print(f"  {team:<25} Group {group}: {prob*100:>5.1f}% exit chance")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run parallel World Cup Monte Carlo simulation")
    parser.add_argument(
        "-n", "--num-simulations",
        type=int,
        default=NUM_SIMULATIONS,
        help=f"Number of simulations to run (default: {NUM_SIMULATIONS})"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=None,
        help=f"Number of worker processes (default: CPU count = {mp.cpu_count()})"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Don't show progress"
    )
    
    args = parser.parse_args()
    
    results = run_parallel_simulation(
        num_simulations=args.num_simulations,
        num_workers=args.workers,
        show_progress=not args.quiet,
        save=not args.no_save,
        seed=args.seed,
    )
    
    print_summary(results)
