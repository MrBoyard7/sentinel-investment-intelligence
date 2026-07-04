"""
Command-line entry point.

    python -m sentinel.cli run            # one pipeline pass
    python -m sentinel.cli schedule        # long-running scheduler
    python -m sentinel.cli dashboard       # start the Flask dashboard
    python -m sentinel.cli daily-digest    # send the daily digest now
    python -m sentinel.cli weekly-digest   # send the weekly digest now
    python -m sentinel.cli seed-demo       # run once in demo mode and print a summary
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel", description="Sentinel CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run", help="Run one full pipeline pass")
    schedule_parser = subparsers.add_parser(
        "schedule", help="Start the long-running scheduler"
    )
    schedule_parser.add_argument(
        "--interval-minutes", type=int, default=30, help="Scan interval in minutes"
    )
    subparsers.add_parser("dashboard", help="Start the Flask dashboard")
    subparsers.add_parser("daily-digest", help="Send the daily digest now")
    subparsers.add_parser("weekly-digest", help="Send the weekly digest now")
    subparsers.add_parser(
        "seed-demo", help="Run one pipeline pass against local demo fixtures"
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        from sentinel.pipeline import run_once

        print(json.dumps(run_once(), indent=2))

    elif args.command == "schedule":
        from sentinel.pipeline import run_scheduler

        run_scheduler(scan_interval_minutes=args.interval_minutes)

    elif args.command == "dashboard":
        from sentinel.dashboard.app import create_app

        app = create_app()
        from sentinel.settings import settings

        app.run(host=settings.dashboard_host, port=settings.dashboard_port, debug=False)

    elif args.command == "daily-digest":
        from sentinel.pipeline import run_daily_digest

        print(json.dumps(run_daily_digest(), indent=2))

    elif args.command == "weekly-digest":
        from sentinel.pipeline import run_weekly_digest

        print(json.dumps(run_weekly_digest(), indent=2))

    elif args.command == "seed-demo":
        from sentinel.settings import settings

        if not settings.demo_mode:
            print(
                "Warning: DEMO_MODE is not enabled. 'seed-demo' is intended to be run "
                "with DEMO_MODE=true so it uses local fixtures instead of live sources."
            )
        from sentinel.pipeline import run_once

        summary = run_once()
        print("Demo pipeline run complete:")
        print(json.dumps(summary, indent=2))
        print("\nStart the dashboard with: python -m sentinel.cli dashboard")

    return 0


if __name__ == "__main__":
    sys.exit(main())
