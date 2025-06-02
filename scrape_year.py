#!/usr/bin/env python3
# scrape_year.py

import argparse
import logging
import signal
import sys
import json
from datetime import datetime, timedelta

from download import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROGRESS_FILE = "progress.json"

def load_progress():
    try:
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def bump_date(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d + timedelta(days=1)).strftime("%Y-%m-%d")

def main():
    parser = argparse.ArgumentParser(
        description="Scrape one or more full calendar years of e-Court data, with graceful shutdown & resume"
    )
    parser.add_argument(
        "--court_codes", required=True,
        help="Comma-separated court codes, e.g. '9~13,27~1,19~16,18~6'"
    )
    parser.add_argument(
        "--year", type=int,
        help="Single 4-digit calendar year, e.g. 2000"
    )
    parser.add_argument(
        "--start_year", type=int,
        help="Start of year range, e.g. 2000"
    )
    parser.add_argument(
        "--end_year", type=int, default=None,
        help="End of year range (inclusive). If omitted, same as --start_year"
    )
    parser.add_argument(
        "--max_workers", type=int, default=5,
        help="Parallel threads (courts scraped simultaneously)."
    )
    args = parser.parse_args()

    if args.year is not None:
        start_year = end_year = args.year
    else:
        start_year = args.start_year
        end_year = args.end_year or args.start_year

    def handle_sigint(signum, frame):
        logger.warning("✋ Interrupted—shutting down. Progress saved to %s.", PROGRESS_FILE)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_sigint)

    codes = [c.strip() for c in args.court_codes.split(",")]
    progress = load_progress()

    for yr in range(start_year, end_year + 1):
        for code in codes:
            key = f"{code}_{yr}"
            if key in progress:
                start_date = bump_date(progress[key])
            else:
                start_date = f"{yr}-01-01"
            end_date = f"{yr}-12-31"

            if start_date > end_date:
                logger.info("✅ %s already complete for %s", code, yr)
                continue

            logger.info(f"▶▶▶ Scraping code={code} for {yr}: {start_date} → {end_date} with {args.max_workers} workers")
            run([code], start_date, end_date, step=1, workers=args.max_workers)

            progress[key] = end_date
            save_progress(progress)

    logger.info("✅ ALL YEARS & CODES COMPLETE.")

if __name__ == "__main__":
    main()