import os
import time
import requests
from datetime import date, datetime, timedelta, timezone

COMPETITION = "WC"
BASE_URL = "https://api.football-data.org/v4"
_cache: dict = {}


def _headers() -> dict:
    return {"X-Auth-Token": os.environ["UR_TOKEN"]}


def get_current_matchday(force_refresh: bool = False) -> int:
    key = "competition_info"
    now = time.time()

    if not force_refresh and key in _cache and now - _cache[key][0] < 300:
        return _cache[key][1]

    resp = requests.get(
        f"{BASE_URL}/competitions/{COMPETITION}",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    matchday = resp.json()["currentSeason"]["currentMatchday"]
    _cache[key] = (now, matchday)
    return matchday


def get_matches_for_matchday(matchday: int | None = None, force_refresh: bool = False) -> tuple[list, int]:
    if matchday is None:
        matchday = get_current_matchday(force_refresh=force_refresh)

    key = f"matchday_{matchday}"
    now = time.time()

    if not force_refresh and key in _cache and now - _cache[key][0] < 300:
        return _cache[key][1], matchday

    resp = requests.get(
        f"{BASE_URL}/competitions/{COMPETITION}/matches",
        headers=_headers(),
        params={"matchday": matchday},
        timeout=10,
    )
    resp.raise_for_status()
    matches = resp.json().get("matches", [])

    # Fall back to a date window when:
    # - matchday returned nothing (knockout rounds don't use matchday), OR
    # - all returned matches are already FINISHED (API stuck on last group-stage matchday)
    all_finished = matches and all(m.get("status") == "FINISHED" for m in matches)
    if not matches or all_finished:
        today = date.today()
        resp = requests.get(
            f"{BASE_URL}/competitions/{COMPETITION}/matches",
            headers=_headers(),
            params={
                "dateFrom": (today - timedelta(days=1)).isoformat(),
                "dateTo": (today + timedelta(days=10)).isoformat(),
            },
            timeout=10,
        )
        resp.raise_for_status()
        upcoming = resp.json().get("matches", [])
        # Only switch to date-range result if it contains non-finished games
        if upcoming and not all(m.get("status") == "FINISHED" for m in upcoming):
            matches = upcoming
            matchday = None  # signal: this is a date-range result, not a matchday

    _cache[key] = (now, matches)
    return matches, matchday


def parse_kickoff(utc_str: str) -> datetime:
    return datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
