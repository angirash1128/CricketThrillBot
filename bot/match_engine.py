# match_engine.py
# Live match data fetch + thrill detection
# API calls SIRF background polling se
# User clicks pe 0 API calls

import os
import requests
from datetime import datetime
from ipl_schedule import get_cache, update_cache

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"


# ─────────────────────────────────────────
# API CALLS (Background polling se only)
# ─────────────────────────────────────────

def fetch_live_match():
    """
    1 API call - live IPL match check karo
    Result cache mein save karo
    SIRF background polling se call hogi
    """
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        now = datetime.now().strftime("%I:%M %p")
        update_cache("last_updated", now)

        if response.status_code != 200:
            print(f"API error: {response.status_code}")
            return None

        data = response.json()

        # API limit check
        info = data.get("info", {})
        hits = info.get("hitsToday", 0)
        limit = info.get("hitsLimit", 100)
        print(f"API: {hits}/{limit} hits used")

        if data.get("status") != "success":
            print(f"API status: {data.get('status')}")
            return None

        matches = data.get("data", [])

        for match in matches:
            # Series check
            series = (
                match.get("series", "") or
                match.get("seriesName", "") or ""
            ).upper()

            if "IPL" not in series and "INDIAN PREMIER" not in series:
                continue

            # Match state
            ms = (match.get("ms", "") or "").lower()
            is_active = (
                "live" in ms or
                "progress" in ms or
                "innings" in ms or
                "break" in ms or
                "toss" in ms
            )

            if not is_active:
                continue

            # Team names
            t1 = _get_team_name(match, 0)
            t2 = _get_team_name(match, 1)

            match_id = str(match.get("id", "") or "")
            status = match.get("status", "") or "Live"
            toss = match.get("tpiw", "") or match.get("toss", "") or ""
            t1s = match.get("t1s", "") or ""
            t2s = match.get("t2s", "") or ""

            live_data = {
                "match_id": match_id,
                "team1": t1,
                "team2": t2,
                "status": status,
                "state": ms,
                "toss": toss,
                "t1_score": t1s,
                "t2_score": t2s,
            }

            update_cache("live_match", live_data)
            print(f"✅ IPL Live: {t1} vs {t2} | {ms}")
            return live_data

        # Koi live match nahi
        update_cache("live_match", None)
        print("No live IPL match")
        return None

    except Exception as e:
        print(f"fetch_live_match error: {e}")
        return None


def _get_team_name(match, index):
    """Team name extract karo - multiple fields try karo"""
    # Method 1: t1/t2
    if index == 0:
        t = match.get("t1", "") or ""
    else:
        t = match.get("t2", "") or ""

    if t:
        return t

    # Method 2: teamInfo array
    team_info = match.get("teamInfo", [])
    if team_info and len(team_info) > index:
        t = (team_info[index].get("name", "") or
             team_info[index].get("shortname", "") or "")
        if t:
            return t

    # Method 3: name field
    name = match.get("name", "") or match.get("matchName", "") or ""
    if " vs " in name:
        parts = name.split(" vs ")
        if index < len(parts):
            return parts[index].strip()

    return f"Team {index + 1}"


def fetch_scorecard(match_id):
    """
    1 API call - match ka scorecard lao
    Cache mein save karo
    SIRF background polling se
    """
    try:
        url = f"{BASE_URL}/match_info"
        params = {"apikey": CRICAPI_KEY, "id": match_id}
        response = requests.get(url, params=params, timeout=15)

        now = datetime.now().strftime("%I:%M %p")
        update_cache("last_updated", now)

        if response.status_code != 200:
            print(f"Scorecard error: {response.status_code}")
            return None

        data = response.json()
        if data.get("status") != "success":
            return None

        match_data = data.get("data", None)
        update_cache("live_scorecard", match_data)
        return match_data

    except Exception as e:
        print(f"fetch_scorecard error: {e}")
        return None


# ─────────────────────────────────────────
# CACHE GETTERS (0 API calls)
# ─────────────────────────────────────────

def get_live_ipl_match():
    """Cache se live match (0 API calls)"""
    return get_cache()["live_match"]


def get_match_scorecard(match_id):
    """Cache se scorecard (0 API calls)"""
    return get_cache()["live_scorecard"]


# ─────────────────────────────────────────
# INNINGS PARSING (0 API calls)
# ─────────────────────────────────────────

def parse_current_innings(match_data):
    """Cached match data se innings info nikalo"""
    try:
        if not match_data:
            return None

        score_list = match_data.get("score", [])
        if not score_list:
            return None

        current = score_list[-1]
        innings_id = len(score_list)

        runs = int(current.get("r", 0) or 0)
        wickets = int(current.get("w", 0) or 0)
        overs = float(current.get("o", 0.0) or 0.0)

        # Target
        target = None
        if innings_id >= 2:
            first = score_list[0]
            target = int(first.get("r", 0) or 0) + 1

        # Run rate
        run_rate = round(runs / overs, 1) if overs > 0 else 0.0

        # Required run rate
        req_rate = 0.0
        if target and innings_id >= 2 and overs < 20:
            balls_left = max(1, int((20 - overs) * 6))
            runs_needed = target - runs
            overs_left = balls_left / 6
            if overs_left > 0:
                req_rate = round(runs_needed / overs_left, 1)

        innings_data = {
            "innings_id": innings_id,
            "runs": runs,
            "wickets": wickets,
            "overs": overs,
            "target": target,
            "run_rate": run_rate,
            "req_rate": req_rate,
        }

        update_cache("live_innings", innings_data)
        return innings_data

    except Exception as e:
        print(f"parse error: {e}")
        return None


# ─────────────────────────────────────────
# THRILL DETECTION
# IPL-specific calibration
# ─────────────────────────────────────────

match_trackers = {}


def detect_thrills(match_id, data):
    """
    IPL thrill moments detect karo.

    IPL averages:
    - 1st innings avg: 170-180
    - Normal RR: 8.5-9.0
    - Death overs RR: 10-14
    - Powerplay RR: 8-10

    Triggers:
    - 2+ wickets since last check = collapse
    - 6+ wickets, below par = deep trouble
    - Close chase last 5 overs
    - Close chase last 3 overs
    - Required rate 14+ (difficult)
    """
    alerts = []
    if not data:
        return alerts

    mid = str(match_id)

    # First check - initialize
    if mid not in match_trackers:
        match_trackers[mid] = {
            "innings_id": data["innings_id"],
            "prev_wickets": data["wickets"],
            "prev_runs": data["runs"],
            "prev_overs": data["overs"],
            "collapse_alerted": False,
            "thriller_alerted": False,
            "super_thriller_alerted": False,
            "steep_alerted": False,
        }
        return alerts

    tr = match_trackers[mid]

    # Innings change - reset
    if tr["innings_id"] != data["innings_id"]:
        match_trackers[mid] = {
            "innings_id": data["innings_id"],
            "prev_wickets": data["wickets"],
            "prev_runs": data["runs"],
            "prev_overs": data["overs"],
            "collapse_alerted": False,
            "thriller_alerted": False,
            "super_thriller_alerted": False,
            "steep_alerted": False,
        }
        return alerts

    runs = data["runs"]
    wickets = data["wickets"]
    overs = data["overs"]
    target = data["target"]
    run_rate = data["run_rate"]
    req_rate = data["req_rate"]

    wickets_diff = wickets - tr["prev_wickets"]

    # ─── WICKET ALERTS ───

    # 2+ wickets since last check
    if wickets_diff >= 2:
        alerts.append({
            "type": "collapse",
            "message": (
                f"😱 <b>WICKETS FALLING!</b>\n\n"
                f"{wickets_diff} wickets in quick succession!\n"
                f"Score: {runs}/{wickets} ({overs} ov)\n\n"
                f"Match is turning! 🔥"
            )
        })

    # 6+ wickets and below par score
    elif wickets >= 6 and not tr["collapse_alerted"]:
        expected = overs * 8.5
        if runs < expected * 0.75:
            alerts.append({
                "type": "collapse",
                "message": (
                    f"💥 <b>BATTING COLLAPSE!</b>\n\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n"
                    f"Run Rate: {run_rate}\n"
                    f"Well below par! 📉"
                )
            })
            tr["collapse_alerted"] = True

    if wickets > tr["prev_wickets"]:
        tr["prev_wickets"] = wickets

    # ─── CHASE ALERTS (2nd innings) ───

    if target and data["innings_id"] >= 2:
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))

        # Last 5 overs + close (<=60 needed)
        if (overs >= 15.0 and
                0 < runs_needed <= 60 and
                not tr["thriller_alerted"]):
            alerts.append({
                "type": "thriller",
                "message": (
                    f"🔴 <b>THRILLER ALERT!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n"
                    f"Required Rate: {req_rate}\n\n"
                    f"🏏 Game ON!"
                )
            })
            tr["thriller_alerted"] = True

        # Last 3 overs + very close (<=30 needed)
        if (overs >= 17.0 and
                0 < runs_needed <= 30 and
                not tr["super_thriller_alerted"]):
            alerts.append({
                "type": "super_thriller",
                "message": (
                    f"🔥🔥 <b>NAIL BITER!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n"
                    f"Required Rate: {req_rate}\n\n"
                    f"EVERY BALL COUNTS! 🏏"
                )
            })
            tr["super_thriller_alerted"] = True

        # Required rate 14+ (very tough chase)
        if (req_rate >= 14.0 and
                overs >= 10.0 and
                not tr["steep_alerted"]):
            alerts.append({
                "type": "steep",
                "message": (
                    f"📈 <b>TOUGH CHASE!</b>\n\n"
                    f"Required Rate: {req_rate}\n"
                    f"Need {runs_needed} off {balls_left} balls\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n\n"
                    f"Can they do it? 🤔"
                )
            })
            tr["steep_alerted"] = True

    # Update tracker
    tr["prev_runs"] = runs
    tr["prev_overs"] = overs

    return alerts


# ─────────────────────────────────────────
# DEBUG (Cache status - 0 API calls)
# ─────────────────────────────────────────

def debug_ipl_status():
    """Cache ka status dikhao - 0 API calls"""
    cache = get_cache()
    lines = []

    lines.append("=== CACHE STATUS ===")

    live = cache.get("live_match")
    if live:
        lines.append(
            f"Live: {live['team1']} vs {live['team2']}\n"
            f"State: {live['state']}\n"
            f"Status: {live['status']}\n"
            f"Score 1: {live.get('t1_score', '-')}\n"
            f"Score 2: {live.get('t2_score', '-')}"
        )
    else:
        lines.append("Live: No match in cache")

    innings = cache.get("live_innings")
    if innings:
        lines.append(
            f"\nInnings: {innings['innings_id']}\n"
            f"Score: {innings['runs']}/{innings['wickets']}\n"
            f"Overs: {innings['overs']}\n"
            f"RR: {innings['run_rate']}\n"
            f"Req RR: {innings['req_rate']}"
        )

    lines.append(f"\nLast API call: {cache.get('last_updated', 'Never')}")
    lines.append(f"Toss notified: {cache.get('toss_notified', False)}")
    lines.append(f"Result notified: {cache.get('result_notified', False)}")

    return "\n".join(lines)
