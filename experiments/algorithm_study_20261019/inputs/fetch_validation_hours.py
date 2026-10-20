#!/usr/bin/env python3
"""Read-only public validation-hours retrieval using the preserved shared parser.

Does not run or modify the old fetcher's main(), validation splits, raw waits,
algorithms, or outcome files. Missing source dates are recorded as failures;
this file never invents operating hours or writes analysis-window fallbacks.
"""
from __future__ import annotations

import concurrent.futures
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPLIT_PATH = HERE / 'splits.json'
PARSER_PATH = ROOT / 'data/verified_inputs/fetch_historical_hours.py'
OUTPUT_CSV = HERE / 'validation_park_hours.csv'
OUTPUT_STATUS = HERE / 'validation_hours_status.json'
RETRIEVED_DATE = '2026-10-19'
FIELDS = ['date', 'opening_local', 'closing_local', 'opening_minutes',
          'closing_minutes', 'timezone', 'source_url', 'retrieved_date',
          'source_html_sha256', 'date_header_verified', 'source_date_heading',
          'status', 'scope']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    splits = json.loads(SPLIT_PATH.read_text())
    dates = splits['splits']['validation']
    if not isinstance(dates, list) or len(dates) != 115 or dates != sorted(set(dates)):
        raise ValueError('Expected the 115 unique sorted frozen validation dates')
    before_split_sha = sha(SPLIT_PATH)
    before_parser_sha = sha(PARSER_PATH)
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('preserved_park_hours_parser', PARSER_PATH)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    rows = []
    print(json.dumps({'stage': 'started', 'requested': len(dates), 'workers': 3,
                      'first_date': dates[0], 'last_date': dates[-1]}), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        tasks = {pool.submit(parser.get_day, day): day for day in dates}
        for task in concurrent.futures.as_completed(tasks):
            row = task.result()
            if 'error' not in row:
                row['retrieved_date'] = RETRIEVED_DATE
            rows.append(row)
            if len(rows) % 10 == 0 or len(rows) == len(dates):
                print(json.dumps({'stage': 'fetching', 'finished': len(rows),
                                  'requested': len(dates),
                                  'errors_so_far': sum('error' in r for r in rows)}), flush=True)
    rows.sort(key=lambda r: r['date'])
    good = [r for r in rows if 'error' not in r]
    failures = [r for r in rows if 'error' in r]
    assert {r['date'] for r in rows} == set(dates)
    assert all(r['date_header_verified'] is True for r in good)
    assert sha(SPLIT_PATH) == before_split_sha and sha(PARSER_PATH) == before_parser_sha
    with OUTPUT_CSV.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(good)
    status = {
        'retrieved_date': RETRIEVED_DATE,
        'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'source': 'TouringPlans.com public date-specific Animal Kingdom normal park-hours pages',
        'requested': len(dates), 'retrieved': len(good), 'failed': len(failures),
        'max_concurrency': 3,
        'requested_first_date': dates[0], 'requested_last_date': dates[-1],
        'split_sha256': before_split_sha, 'reused_parser_sha256': before_parser_sha,
        'csv_sha256': sha(OUTPUT_CSV),
        'date_heading_verified_successes': sum(r['date_header_verified'] for r in good),
        'date_heading_conflicts': [r for r in failures if 'header mismatch' in r['error']],
        'independent_cross_source_calendar_check_performed': False,
        'source_conflicts': 'Not independently assessed; successful extraction/date-heading checks are not cross-source agreement.',
        'failures': failures,
        'fallback_policy': 'No fallback hours written. Parent protocol may use an explicitly labeled 20:00 analysis deadline for failed source dates; that is not asserted to be historical park closing time.',
        'limitations': [
            'Published secondary-source historical schedules are not independently verified operating logs.',
            'Normal public park hours exclude early-entry Extra Magic Hours.',
            'Park hours do not establish individual attraction opening or closing times.',
            'No ride waits or validation outcomes are used to retrieve or select dates.',
            'Source pages may be revised; each fetched HTML response is SHA-256 hashed.'
        ],
        'preserved_inputs_unchanged': True,
    }
    OUTPUT_STATUS.write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({'stage': 'done', 'requested': len(dates), 'retrieved': len(good),
                      'failed': len(failures), 'date_heading_conflicts': len(status['date_heading_conflicts'])}), flush=True)


if __name__ == '__main__':
    main()
