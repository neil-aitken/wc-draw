#!/usr/bin/env python3
"""Run a large seed scan for the draw and write per-seed results incrementally.

Usage examples:
  python3 scripts/seed_scan_large.py --start 0 --end 10000 --workers 8 --output seed_scan_large.jsonl
  nohup python3 scripts/seed_scan_large.py --start 0 --end 100000 --workers 12 --output seed_scan_large.jsonl &

The script writes JSON lines (one JSON object per seed) to the output file so it can be monitored while running.
Each record:
  {"seed": int, "success": bool, "error": <string or null>, "used_seed": int}

This script is intentionally dependency-free (no tqdm). It uses multiprocessing to speed up runs.
"""

from __future__ import annotations
import argparse
import json
import multiprocessing
import sys
from pathlib import Path
from typing import Optional

# Ensure repo root is on sys.path when script is run from project root (normal case)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wc_draw.parser import parse_teams_config
from wc_draw.draw import run_full_draw


def run_seed_task(args_tuple):
    seed, max_attempts, retry_attempts = args_tuple
    # Each worker constructs its own pots to avoid shared state
    try:
        pots = parse_teams_config(str(Path("teams.csv").resolve()))
    except Exception as e:
        return {
            "seed": seed,
            "success": False,
            "error": f"parse_teams_config error: {e}",
            "used_seed": None,
        }

    try:
        # Request fallback metadata so we can record if an alternate strategy was used
        maybe = run_full_draw(pots, seed=seed, max_attempts=max_attempts, report_fallbacks=True)
        # run_full_draw may return (groups, seed) or (groups, seed, metadata)
        if len(maybe) == 3:
            groups, used_seed, metadata = maybe
        else:
            groups, used_seed = maybe
            metadata = {"fallback": None}

        # Serialize groups to simple lists of team names for downstream aggregation
        groups_serialized = {g: [t.name for t in teams] for g, teams in groups.items()}
        return {
            "seed": seed,
            "success": True,
            "error": None,
            "used_seed": used_seed,
            "groups": groups_serialized,
            "fallback": metadata.get("fallback"),
        }
    except Exception:
        # retry once with a larger budget
        try:
            maybe = run_full_draw(
                pots, seed=seed, max_attempts=retry_attempts, report_fallbacks=True
            )
            if len(maybe) == 3:
                groups, used_seed, metadata = maybe
            else:
                groups, used_seed = maybe
                metadata = {"fallback": None}
            groups_serialized = {g: [t.name for t in teams] for g, teams in groups.items()}
            return {
                "seed": seed,
                "success": True,
                "error": None,
                "used_seed": used_seed,
                "groups": groups_serialized,
                "fallback": metadata.get("fallback"),
            }
        except Exception as e2:
            return {"seed": seed, "success": False, "error": str(e2), "used_seed": None}


def write_jsonl_line(path: Path, obj: dict, lock: Optional[multiprocessing.Lock]):
    line = json.dumps(obj, sort_keys=True)
    # Use a lock if provided (multiprocessing)
    if lock is not None:
        with lock:
            with open(path, "a") as fh:
                fh.write(line + "\n")
    else:
        with open(path, "a") as fh:
            fh.write(line + "\n")


def main():
    parser = argparse.ArgumentParser(description="Large seed scan for wc-draw")
    parser.add_argument("--start", type=int, default=0, help="Start seed (inclusive)")
    parser.add_argument("--end", type=int, default=10000, help="End seed (exclusive)")
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, multiprocessing.cpu_count() - 1),
        help="Number of worker processes",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=2000,
        help="primary max attempts passed to run_full_draw",
    )
    parser.add_argument(
        "--retry-attempts", type=int, default=10000, help="retry attempts if primary attempt fails"
    )
    parser.add_argument(
        "--output", type=str, default="seed_scan_large.jsonl", help="Output JSONL path (appendable)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="How many seeds to queue per batch (for memory control)",
    )
    args = parser.parse_args()

    outpath = Path(args.output)
    # If file exists, do not overwrite; append. But include a header record for metadata.
    if not outpath.exists():
        header = {"meta": {"start": args.start, "end": args.end, "workers": args.workers}}
        outpath.parent.mkdir(parents=True, exist_ok=True)
        outpath.write_text(json.dumps(header) + "\n")

    seeds = range(args.start, args.end)

    # Use a manager lock to coordinate writes
    manager = multiprocessing.Manager()
    lock = manager.Lock()

    pool = multiprocessing.Pool(processes=args.workers)
    try:
        # Prepare iterable of tasks
        tasks = ((s, args.max_attempts, args.retry_attempts) for s in seeds)
        # imap_unordered yields results as workers finish
        it = pool.imap_unordered(run_seed_task, tasks, chunksize=args.chunk_size)
        done = 0
        for res in it:
            write_jsonl_line(outpath, res, lock)
            done += 1
            if done % 1000 == 0:
                print(f"Completed {done} seeds", flush=True)
    except KeyboardInterrupt:
        print("Interrupted, terminating pool", flush=True)
        pool.terminate()
        pool.join()
        sys.exit(1)
    finally:
        pool.close()
        pool.join()

    print(f"Finished seeds {args.start}..{args.end} -> output {outpath}")


if __name__ == "__main__":
    main()
