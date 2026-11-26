"""
AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
Unified Pipeline Orchestrator (engine/run_pipeline.py)

Orchestrates Stages 1 through 6 sequentially:
  Stage 1: Discovery (1_discover.py - YouTube & HN developer inquiries)
  Stage 2: Grounded Drafting (2_draft.py - Gemini + 4-tier fact registry)
  Stage 3: Expert Dispatch (3_expert_dispatch.py - tokenized email dispatch)
  Stage 4: Static Site Export (exporter.py - strict human gate, hard 20-cap, Section Kit)
  Stage 5: Social Distribution (5_social.py - scheduled Bluesky posts, 3/day cap)
  Stage 6: Measurement & AI Topics (6_measure.py - crawler analytics & topic recommender)

CLI Flags:
  --ingest  : Runs Stage 1 & Stage 2 (Discovery + Drafting)
  --publish : Runs Stage 4 & Stage 5 (Static Export + Social Scheduling)
  --all     : Runs Stages 1 through 6 sequentially (default)
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from engine.database import init_db
import importlib

# Dynamic imports for numeric module filenames
discover_mod = importlib.import_module("engine.1_discover")
draft_mod = importlib.import_module("engine.2_draft")
dispatch_mod = importlib.import_module("engine.3_expert_dispatch")
exporter_mod = importlib.import_module("engine.exporter")
social_mod = importlib.import_module("engine.5_social")
measure_mod = importlib.import_module("engine.6_measure")


def log_banner(stage_num: int, title: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bar = "=" * 70
    print(f"\n{bar}\n[{ts}] STAGE {stage_num}: {title}\n{bar}")


def run_stage_1() -> Dict[str, Any]:
    log_banner(1, "Question Discovery (YouTube Data API v3 & Hacker News)")
    stats = discover_mod.run_discovery()
    return stats


def run_stage_2() -> Dict[str, Any]:
    log_banner(2, "Grounded AI Drafting (Gemini JSON + Fact Registry)")
    stats = draft_mod.run_drafting(max_new_drafts=5)
    return stats


def run_stage_3() -> Dict[str, Any]:
    log_banner(3, "Expert Review Notification & Dispatch")
    stats = dispatch_mod.dispatch_pending_drafts()
    return stats


def run_stage_4() -> Dict[str, Any]:
    log_banner(4, "Static Site Export (Strict Human Gate & Section Kit)")
    stats = exporter_mod.run_export()
    return stats


def run_stage_5() -> Dict[str, Any]:
    log_banner(5, "Social Automation (Bluesky Scheduled Distribution)")
    sched_count = social_mod.schedule_approved_answers()
    post_stats = social_mod.run_scheduled_posts()
    return {
        "newly_scheduled": sched_count,
        "due_posts": post_stats.get("due_count", 0),
        "posted": post_stats.get("posted", 0),
        "dry_run": post_stats.get("dry_run", True)
    }


def run_stage_6() -> Dict[str, Any]:
    log_banner(6, "Measurement, Bot Analytics & Next-Topic Recommender")
    summary = measure_mod.get_analytics_summary()
    recs = measure_mod.recommend_next_topics()
    return {
        "total_requests": summary.get("total_requests", 0),
        "ai_crawler_hits": summary.get("ai_crawler_hits", 0),
        "ab_verdict": summary.get("ab_experiment", {}).get("verdict", "N/A"),
        "topics_recommended": len(recs),
        "top_recommendation": recs[0]["suggested_title"] if recs else None
    }


def main():
    parser = argparse.ArgumentParser(
        description="AI Atlas India — Plate 05 Indic Language AI Unified Pipeline Orchestrator"
    )
    parser.add_argument("--ingest", action="store_true", help="Run Stage 1 (Discover) & Stage 2 (Draft)")
    parser.add_argument("--publish", action="store_true", help="Run Stage 4 (Export) & Stage 5 (Social)")
    parser.add_argument("--all", action="store_true", help="Run all 6 stages sequentially (default)")
    args = parser.parse_args()

    # Default to running all stages if no specific stage flag is provided
    run_all = args.all or (not args.ingest and not args.publish)

    start_time = datetime.now()
    print("=" * 70)
    print("AI ATLAS INDIA — PLATE 05: INDIC LANGUAGE AI")
    print("Automated Content Discovery, Human Verification & Publishing Pipeline")
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Initialize database
    init_db()

    pipeline_summary = {
        "status": "SUCCESS",
        "started_at": start_time.isoformat(),
        "stages_executed": {}
    }

    try:
        if args.ingest:
            pipeline_summary["stages_executed"]["stage_1_discovery"] = run_stage_1()
            pipeline_summary["stages_executed"]["stage_2_drafting"] = run_stage_2()
        elif args.publish:
            pipeline_summary["stages_executed"]["stage_4_export"] = run_stage_4()
            pipeline_summary["stages_executed"]["stage_5_social"] = run_stage_5()
        elif run_all:
            pipeline_summary["stages_executed"]["stage_1_discovery"] = run_stage_1()
            pipeline_summary["stages_executed"]["stage_2_drafting"] = run_stage_2()
            pipeline_summary["stages_executed"]["stage_3_dispatch"] = run_stage_3()
            pipeline_summary["stages_executed"]["stage_4_export"] = run_stage_4()
            pipeline_summary["stages_executed"]["stage_5_social"] = run_stage_5()
            pipeline_summary["stages_executed"]["stage_6_measurement"] = run_stage_6()

        end_time = datetime.now()
        pipeline_summary["completed_at"] = end_time.isoformat()
        pipeline_summary["duration_seconds"] = round((end_time - start_time).total_seconds(), 2)

        print("\n" + "=" * 70)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 70)
        print(json.dumps(pipeline_summary, indent=2))
        print("=" * 70)
        sys.exit(0)

    except Exception as e:
        print(f"\n[Pipeline:FATAL] Pipeline aborted with exception: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
