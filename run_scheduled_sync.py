"""Scheduled Inbenta synchronization and optional historical backfill."""

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

APP_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(APP_ROOT))

from reporting_dashboard.config import REFRESH_DAYS, get_reporting_today  # noqa: E402
from reporting_dashboard.db import init_db  # noqa: E402
from reporting_dashboard.sync import sync  # noqa: E402

logger = logging.getLogger("merz.scheduled_sync")


def _run_range(start: date, end: date, label: str) -> bool:
    logger.info("Starting %s sync: %s through %s", label, start, end)
    try:
        result = sync(start, end, force_api=True)
        logger.info("%s sync complete: %s", label, result["message"])
        return True
    except Exception:
        logger.exception("%s sync failed", label)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill-start", type=date.fromisoformat)
    parser.add_argument("--backfill-end", type=date.fromisoformat)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if bool(args.backfill_start) != bool(args.backfill_end):
        parser.error("--backfill-start and --backfill-end must be provided together")
    if args.backfill_start and args.backfill_end:
        if args.backfill_start > args.backfill_end:
            parser.error("--backfill-end must be on or after --backfill-start")
        init_db()
        return 0 if _run_range(args.backfill_start, args.backfill_end, "backfill") else 1

    init_db()
    today = get_reporting_today()
    last_complete_day = today - timedelta(days=1)
    rolling_start = last_complete_day - timedelta(days=max(REFRESH_DAYS, 1) - 1)

    succeeded = _run_range(rolling_start, last_complete_day, "rolling refresh")
    if today.day == 2:
        previous_month_end = today.replace(day=1) - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)
        succeeded = _run_range(
            previous_month_start, previous_month_end, "monthly reconciliation"
        ) and succeeded

    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
