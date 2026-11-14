"""
TERRAIN-X Command Line Interface (CLI)
Provides command-line execution for analog ranking, API source checks, and sensitivity reports.
"""

import argparse
import json
import os
import sys

# Ensure data root is on sys.path for direct script execution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if DATA_ROOT not in sys.path:
    sys.path.insert(0, DATA_ROOT)

from modules.science.features.catalog import ANALOG_CATALOG, get_site_by_id
from modules.science.score import DEFAULT_MISSION_PROFILES
from modules.science.validation import (
    format_validation_markdown_table,
    run_benchmark_evaluation,
    run_weight_sensitivity_analysis,
)


def cmd_rank(args):
    mission_id = args.mission
    print(f"\n=======================================================")
    print(f" TERRAIN-X Planetary Analog Ranking Engine")
    print(f" Target Profile: {mission_id}")
    print(f"=======================================================\n")
    assessments = run_benchmark_evaluation(mission_id)
    table_md = format_validation_markdown_table(assessments)
    print(table_md)
    print("\n[Done] All candidate sites evaluated.")


def cmd_sensitivity(args):
    mission_id = args.mission
    print(f"\nRunning weight sensitivity perturbation analysis for {mission_id}...")
    res = run_weight_sensitivity_analysis(mission_id)
    print(f"Perturbation tested: {res['perturbation_tested']}")
    print(f"Ranking stability verified: {res['ranking_order_stable']}\n")
    print(f"{'Site ID':<25} | {'Baseline':<10} | {'Cave-Heavy':<10} | {'Topo-Heavy':<10}")
    print("-" * 65)
    for site_id, traj in res["site_trajectories"].items():
        b = f"{traj['score_baseline']:.4f}" if traj["score_baseline"] else "N/A"
        c = f"{traj['score_cave_heavy']:.4f}" if traj["score_cave_heavy"] else "N/A"
        t = f"{traj['score_topo_heavy']:.4f}" if traj["score_topo_heavy"] else "N/A"
        print(f"{site_id:<25} | {b:<10} | {c:<10} | {t:<10}")


def cmd_site(args):
    site = get_site_by_id(args.id)
    if not site:
        print(f"Error: Site '{args.id}' not found.")
        sys.exit(1)
    print(json.dumps(site.model_dump(), indent=2))


def main():
    parser = argparse.ArgumentParser(description="TERRAIN-X Planetary Analog Evaluation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Rank command
    parser_rank = subparsers.add_parser("rank", help="Rank all catalog sites for a mission profile")
    parser_rank.add_argument("--mission", default="LUNAR_VOLCANIC_CAVITY_V1", choices=list(DEFAULT_MISSION_PROFILES.keys()))
    parser_rank.set_defaults(func=cmd_rank)

    # Sensitivity command
    parser_sens = subparsers.add_parser("sensitivity", help="Run weight sensitivity analysis")
    parser_sens.add_argument("--mission", default="LUNAR_VOLCANIC_CAVITY_V1", choices=list(DEFAULT_MISSION_PROFILES.keys()))
    parser_sens.set_defaults(func=cmd_sensitivity)

    # Site command
    parser_site = subparsers.add_parser("site", help="Inspect a specific candidate site")
    parser_site.add_argument("--id", required=True, help="Site ID (e.g. ES_LANZAROTE_CORONA)")
    parser_site.set_defaults(func=cmd_site)

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
