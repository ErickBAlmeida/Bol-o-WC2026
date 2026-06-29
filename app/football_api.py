import os
import time
import requests
from datetime import datetime, timezone

COMPETITION = "WC"
BASE_URL = "https://api.football-data.org/v4"
_cache: dict = {}

KNOCKOUT_STAGES = ["LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "THIRD_PLACE", "FINAL"]


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


def get_matches_for_stage(stage: str, force_refresh: bool = False) -> list:
    key = f"stage_{stage}"
    now = time.time()

    if not force_refresh and key in _cache and now - _cache[key][0] < 300:
        return _cache[key][1]

    resp = requests.get(
        f"{BASE_URL}/competitions/{COMPETITION}/matches",
        headers=_headers(),
        params={"stage": stage},
        timeout=10,
    )
    resp.raise_for_status()
    matches = resp.json().get("matches", [])
    _cache[key] = (now, matches)
    return matches


def get_matches_for_matchday(matchday: int | None = None, force_refresh: bool = False) -> tuple[list, int | None, str | None]:
    if matchday is None:
        matchday = get_current_matchday(force_refresh=force_refresh)

    key = f"matchday_{matchday}"
    now = time.time()

    if not force_refresh and key in _cache and now - _cache[key][0] < 300:
        cached_matches, cached_matchday, cached_stage = _cache[key][1]
        return cached_matches, cached_matchday, cached_stage

    resp = requests.get(
        f"{BASE_URL}/competitions/{COMPETITION}/matches",
        headers=_headers(),
        params={"matchday": matchday},
        timeout=10,
    )
    resp.raise_for_status()
    matches = resp.json().get("matches", [])

    # When group-stage matchday is empty or fully finished, find the active knockout stage
    all_finished = bool(matches) and all(m.get("status") == "FINISHED" for m in matches)
    if not matches or all_finished:
        for stage in KNOCKOUT_STAGES:
            ko_matches = get_matches_for_stage(stage, force_refresh=force_refresh)
            if ko_matches and not all(m.get("status") == "FINISHED" for m in ko_matches):
                _cache[key] = (now, (ko_matches, None, stage))
                return ko_matches, None, stage

    _cache[key] = (now, (matches, matchday, None))
    return matches, matchday, None


def parse_kickoff(utc_str: str) -> datetime:
    return datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
