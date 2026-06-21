import os
import time
import requests
from datetime import date, datetime, timezone

COMPETITION = "WC"
BASE_URL = "https://api.football-data.org/v4"
_cache: dict = {}


def _headers() -> dict:
    return {"X-Auth-Token": os.environ["UR_TOKEN"]}


def get_matches_for_date(target_date: date | None = None, force_refresh: bool = False) -> list:
    if target_date is None:
        target_date = date.today()

    key = target_date.isoformat()
    now = time.time()

    if not force_refresh and key in _cache and now - _cache[key][0] < 300:
        return _cache[key][1]

    date_str = target_date.isoformat()
    resp = requests.get(
        f"{BASE_URL}/competitions/{COMPETITION}/matches",
        headers=_headers(),
        params={"dateFrom": date_str, "dateTo": date_str},
        timeout=10,
    )
    resp.raise_for_status()
    matches = resp.json().get("matches", [])
    _cache[key] = (now, matches)
    return matches


def parse_kickoff(utc_str: str) -> datetime:
    return datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
