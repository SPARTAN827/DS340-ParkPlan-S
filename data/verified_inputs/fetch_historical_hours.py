"""Fetch public, date-specific park-hours facts. Does not bypass subscriptions.

Reproduction needs HTTPS access; run from the workspace root. Output preserves
source URLs and HTML hashes, not copies of copyrighted site pages. These are
secondary-source historical schedules, not proof every attraction was operating.
"""
import concurrent.futures
import csv
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
DATES = sorted({r['date'] for r in csv.DictReader((ROOT / 'experiments/replay_pilot/per_day.csv').open())})

def fetch(url):
    with urllib.request.urlopen(url, timeout=40) as response:
        data = response.read()
    raw = data.decode('utf-8', errors='replace')
    raw = re.sub(r'<script\b[^>]*>.*?</script>', ' ', raw, flags=re.S | re.I)
    raw = re.sub(r'<style\b[^>]*>.*?</style>', ' ', raw, flags=re.S | re.I)
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', raw)))
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', data.decode('utf-8', errors='replace'), re.S | re.I)
    heading = html.unescape(re.sub(r'<[^>]+>', '', title_match[1])).strip() if title_match else ''
    return text, hashlib.sha256(data).hexdigest(), heading

def clock(s):
    return dt.datetime.strptime(s.lower().replace(' ', ''), '%I:%M%p').strftime('%H:%M')

def get_day(day):
    url = 'https://touringplans.com/animal-kingdom/wait-times/date/' + day
    try:
        text, digest, heading = fetch(url)
        date = dt.date.fromisoformat(day)
        expected = f"Disney's Animal Kingdom Wait Times - {date.strftime('%A, %B')} {date.day}, {date.year}"
        if heading != expected:
            raise ValueError(f'Date/weekday header mismatch: {heading!r} != {expected!r}')
        match = re.search(r'Animal Kingdom Hours Opening Time (\d+:\d+\s*[ap]m) Closing Time (\d+:\d+\s*[ap]m)', text, re.I)
        if not match:
            raise ValueError('Unrecognized normal-hours table')
        opening, closing = clock(match[1]), clock(match[2])
        minutes = lambda value: int(value[:2]) * 60 + int(value[3:])
        return {'date': day, 'opening_local': opening, 'closing_local': closing,
                'opening_minutes': minutes(opening), 'closing_minutes': minutes(closing),
                'timezone': 'America/New_York', 'source_url': url, 'retrieved_date': '2026-10-14',
                'source_html_sha256': digest, 'date_header_verified': True,
                'source_date_heading': heading, 'status': 'extracted_and_date_header_checked_not_independently_confirmed',
                'scope': 'normal_park_hours_not_individual_attraction_hours'}
    except Exception as e:
        return {'date': day, 'source_url': url, 'error': str(e)}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(get_day, DATES))
    failures = [r for r in rows if 'error' in r]
    good = [r for r in rows if 'error' not in r]
    if good:
        with (OUT / 'historical_park_hours.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(good[0]))
            writer.writeheader()
            writer.writerows(good)
    (OUT / 'hours_fetch_status.json').write_text(json.dumps({'requested': len(DATES), 'retrieved': len(good), 'failures': failures}, indent=2) + '\n')
    print(json.dumps({'requested': len(DATES), 'retrieved': len(good), 'failed': len(failures)}))

if __name__ == '__main__':
    main()
