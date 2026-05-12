# match_engine.py
# Live Match Data + Thrill Detection
# API calls sirf background polling se
# User clicks pe 0 API calls

import os
import requests
from datetime import datetime
from ipl_schedule import get_cache, update_cache

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"


# ─────────────────────────────────────────
# LIVE MATCH FETCH (Background polling se)
# ─────────────────────────────────────────

def fetch_live_match():
    """
    API se live IPL match fetch karo - 1 call
    Data cache mein save karo
    Ye SIRF background polling se call hogi
    User click se KABHI nahi
    """
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        now = datetime.now().strftime("%H:%M")
        update_cache("last_api_call", now)

        if response.status_code != 200:
            print(f"API error: {response.status_code}")
            return None

        data = response.json()

        if data.get("status") != "success":
            info = data.get("info", {})
            hits = info.get("hitsToday", 0)
            limit = info.get("hitsLimit", 100)
            print(f"API status: {data.get('status')} | Hits: {hits}/{limit}")
            return None

        # API hits info log karo
        info = data.get("info", {})
        hits = info.get("hitsToday", 0)
        limit = info.get("hitsLimit", 100)
        print(f"API Hits: {hits}/{limit}")

        matches = data.get("data", [])

        for match in matches:
            # Fields - multiple naam try karo
            series = (
                match.get("series", "") or
                match.get("seriesName", "") or ""
            )

            # IPL check
            series_upper = series.upper()
            if "IPL" not in series_upper and "INDIAN PREMIER" not in series_upper:
                continue

            # Match status
            ms = (
                match.get("ms", "") or
                match.get("matchStatus", "") or ""
            ).lower()

            # Sirf live/active matches
            is_active = (
                "live" in ms or
                "progress" in ms or
                "innings" in ms or
                "break" in ms or
                "toss" in ms
            )

            if not is_active:
                continue

            # Match data extract karo
            match_id = str(
                match.get("id", "") or
                match.get("matchId", "") or ""
            )

            # Team names - har possible field try karo
            t1 = ""
            t2 = ""

            # Method 1: t1, t2 fields
            t1 = match.get("t1", "") or ""
            t2 = match.get("t2", "") or ""

            # Method 2: teamInfo array
            if not t1 and match.get("teamInfo"):
                team_info = match.get("teamInfo", [])
                if len(team_info) >= 1:
                    t1 = team_info[0].get("name", "") or team_info[0].get("shortname", "") or ""
                if len(team_info) >= 2:
                    t2 = team_info[1].get("name", "") or team_info[1].get("shortname", "") or ""

            # Method 3: name field se parse
            if not t1:
                name = match.get("name", "") or match.get("matchName", "") or ""
                if " vs " in name:
                    parts = name.split(" vs ")
                    t1 = parts[0].strip()
                    t2 = parts[1].strip() if len(parts) > 1 else ""

            # Fallback
            if not t1:
                t1 = "Team 1"
            if not t2:
                t2 = "Team 2"

            # Status
            status = (
                match.get("status", "") or
                match.get("matchStatus", "") or "Live"
            )

            # Toss
            toss = match.get("tpiw", "") or match.get("toss", "") or ""

            # Score
            t1s = match.get("t1s", "") or ""
            t2s = match.get("t2s", "") or ""

            live_data = {
                "match_id": match_id,
                "team1": t1,
                "team2": t2,
                "status": status,
                "state": ms,
                "toss": toss,
                "series": series,
                "t1_score": t1s,
                "t2_score": t2s
            }

            # Cache mein save karo
            update_cache("live_match", live_data)

            print(f"✅ IPL Live: {t1} vs {t2} | {ms}")
            return live_data

        # Koi live IPL match nahi mila
        update_cache("live_match", None)
        print("No live IPL match")
        return None

    except Exception as e:
        print(f"fetch_live_match error: {e}")
        return None


def get_live_ipl_match():
    """
    Cached live match data return karo
    0 API calls - sirf cache se
    """
    return get_cache()["live_match"]


# ─────────────────────────────────────────
# SCORECARD FETCH (Background polling se)
# ─────────────────────────────────────────

def fetch_scorecard(match_id):
    """
    Match ka scorecard fetch karo - 1 API call
    Cache mein save karo
    SIRF background polling se
    """
    try:
        url = f"{BASE_URL}/match_info"
        params = {"apikey": CRICAPI_KEY, "id": match_id}
        response = requests.get(url, params=params, timeout=15)

        now = datetime.now().strftime("%H:%M")
        update_cache("last_api_call", now)

        if response.status_code != 200:
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


def get_match_scorecard(match_id):
    """Cached scorecard return karo - 0 API calls"""
    return get_cache()["live_scorecard"]


# ─────────────────────────────────────────
# INNINGS PARSING
# ─────────────────────────────────────────

def parse_current_innings(match_data):
    """
    Match data se current innings ki info nikalo
    0 API calls - cached data se
    """
    try:
        if not match_data:
            return None

        score_list = match_data.get("score", [])
        if not score_list:
            return None

        current = score_list[-1]

        runs = int(current.get("r", 0) or 0)
        wickets = int(current.get("w", 0) or 0)
        overs = float(current.get("o", 0.0) or 0.0)
        inning_name = current.get("inning", "") or ""
        innings_id = len(score_list)

        # Target (2nd innings)
        target = None
        if innings_id >= 2:
            first = score_list[0]
            target = int(first.get("r", 0) or 0) + 1

        # Run rate
        run_rate = round(runs / overs, 2) if overs > 0 else 0.0

        # Required run rate
        req_rate = 0.0
        if target and innings_id >= 2 and overs < 20:
            balls_left = max(1, int((20 - overs) * 6))
            runs_needed = target - runs
            overs_left = balls_left / 6
            if overs_left > 0:
                req_rate = round(runs_needed / overs_left, 2)

        innings_data = {
            "innings_id": innings_id,
            "inning_name": inning_name,
            "runs": runs,
            "wickets": wickets,
            "overs": overs,
            "target": target,
            "run_rate": run_rate,
            "req_rate": req_rate
        }

        update_cache("live_innings", innings_data)
        return innings_data

    except Exception as e:
        print(f"parse error: {e}")
        return None


# ─────────────────────────────────────────
# DEBUG (1 API call - emergency only)
# ─────────────────────────────────────────

def debug_ipl_status():
    """
    Debug report - ye API call use karta hai
    Sirf emergency mein use karo
    """
    cache = get_cache()

    lines = []
    lines.append("=== CACHE STATUS ===\n")

    # Schedule
    schedule_count = len(cache["schedule"])
    lines.append(f"Schedule cached: {schedule_count} matches")
    lines.append(f"Schedule fetched: {cache['schedule_fetched']}")

    # Live match
    live = cache["live_match"]
    if live:
        lines.append(
            f"\nLive: {live['team1']} vs {live['team2']}"
            f"\nState: {live['state']}"
            f"\nStatus: {live['status']}"
            f"\n{live['team1']}: {live.get('t1_score', '-')}"
            f"\n{live['team2']}: {live.get('t2_score', '-')}"
        )
    else:
        lines.append("\nLive: No match in cache")

    # Innings
    innings = cache["live_innings"]
    if innings:
        lines.append(
            f"\nInnings: {innings['innings_id']}"
            f"\nScore: {innings['runs']}/{innings['wickets']}"
            f"\nOvers: {innings['overs']}"
            f"\nRR: {innings['run_rate']}"
            f"\nReq RR: {innings['req_rate']}"
        )

    # API info
    lines.append(f"\nLast API call: {cache['last_api_call'] or 'Never'}")
    lines.append(f"Match started: {cache['match_started']}")
    lines.append(f"Match ended: {cache['match_ended']}")
    lines.append(f"Toss notified: {cache['toss_notified']}")

    return "\n".join(lines)


# ─────────────────────────────────────────
# THRILL DETECTION ENGINE
# IPL Specific - Professional Calibration
# ─────────────────────────────────────────

match_trackers = {}


def detect_thrills(match_id, innings_data):
    """
    IPL-specific thrill detection

    IPL Normal Values:
    - Average 1st innings: 170-180
    - Normal run rate: 8.5-9.0
    - Death overs RR: 10-14
    - Powerplay RR: 8-10

    THRILL triggers:
    1. 2+ wickets since last check = collapse sign
    2. 5+ total wickets with low score = deep trouble
    3. 18+ runs since last check = explosive batting
    4. Last 5 overs + close chase = thriller
    5. Last 3 overs + very close = nail biter
    6. Required rate 14+ = steep chase
    """
    alerts = []

    if not innings_data:
        return alerts

    mid = str(match_id)

    # First time tracking
    if mid not in match_trackers:
        match_trackers[mid] = {
            "innings_id": innings_data["innings_id"],
            "wicket_count": innings_data["wickets"],
            "last_runs": innings_data["runs"],
            "last_overs": innings_data["overs"],
            "thriller_alerted": False,
            "super_thriller_alerted": False,
            "collapse_alerted": False,
            "explosive_alerted_at": 0,
            "steep_chase_alerted": False
        }
        return alerts

    tr = match_trackers[mid]

    # Innings change - reset tracker
    if tr["innings_id"] != innings_data["innings_id"]:
        match_trackers[mid] = {
            "innings_id": innings_data["innings_id"],
            "wicket_count": innings_data["wickets"],
            "last_runs": innings_data["runs"],
            "last_overs": innings_data["overs"],
            "thriller_alerted": False,
            "super_thriller_alerted": False,
            "collapse_alerted": False,
            "explosive_alerted_at": 0,
            "steep_chase_alerted": False
        }
        return alerts

    runs = innings_data["runs"]
    wickets = innings_data["wickets"]
    overs = innings_data["overs"]
    target = innings_data["target"]
    run_rate = innings_data["run_rate"]
    req_rate = innings_data["req_rate"]

    runs_diff = runs - tr["last_runs"]
    wickets_diff = wickets - tr["wicket_count"]

    # ─── WICKET ALERTS ───

    # Multiple wickets (2+ since last check)
    if wickets_diff >= 2:
        alerts.append({
            "type": "collapse",
            "is_mega": True,
            "message": (
                f"😱 <b>WICKETS TUMBLING!</b>\n\n"
                f"{wickets_diff} wickets fell since last update!\n"
                f"Score: {runs}/{wickets} ({overs} ov)\n"
                f"Run Rate: {run_rate}\n\n"
                f"Match is turning! 🔥"
            )
        })

    # Deep trouble (5+ wickets, below par)
    elif wickets >= 5 and not tr["collapse_alerted"]:
        expected = overs * 8.5
        if runs < expected * 0.7:
            alerts.append({
                "type": "collapse",
                "is_mega": True,
                "message": (
                    f"💥 <b>BATTING COLLAPSE!</b>\n\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n"
                    f"Run Rate: {run_rate}\n"
                    f"Well below par! 📉"
                )
            })
            tr["collapse_alerted"] = True

    # Single wicket but team in trouble (6+ down)
    elif wickets_diff == 1 and wickets >= 6:
        alerts.append({
            "type": "wicket",
            "is_mega": False,
            "message": (
                f"🚨 <b>WICKET!</b>\n\n"
                f"Score: {runs}/{wickets} ({overs} ov)\n"
                f"Team in deep trouble! 😰"
            )
        })

    # Update wicket count
    if wickets > tr["wicket_count"]:
        tr["wicket_count"] = wickets

    # ─── EXPLOSIVE BATTING ───

    if (runs_diff >= 18 and
            overs > tr.get("explosive_alerted_at", 0) + 2):
        alerts.append({
            "type": "explosive",
            "is_mega": False,
            "message": (
                f"💥 <b>EXPLOSIVE BATTING!</b>\n\n"
                f"{runs_diff} runs scored since last update!\n"
                f"Score: {runs}/{wickets} ({overs} ov)\n"
                f"Run Rate: {run_rate} 🚀"
            )
        })
        tr["explosive_alerted_at"] = overs

    # ─── THRILLER CHASE (2nd innings) ───

    if target and innings_data["innings_id"] >= 2:
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))

        # Last 5 overs + close (need <= 60)
        if (overs >= 15.0 and
                0 < runs_needed <= 60 and
                not tr["thriller_alerted"]):
            alerts.append({
                "type": "thriller",
                "is_mega": True,
                "message": (
                    f"🔴 <b>THRILLER ALERT!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n"
                    f"Required Rate: {req_rate}\n\n"
                    f"🏏 Game ON!"
                )
            })
            tr["thriller_alerted"] = True

        # Last 3 overs + very close (need <= 30)
        if (overs >= 17.0 and
                0 < runs_needed <= 30 and
                not tr["super_thriller_alerted"]):
            alerts.append({
                "type": "super_thriller",
                "is_mega": True,
                "message": (
                    f"🔥🔥🔥 <b>NAIL BITER!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n"
                    f"Required Rate: {req_rate}\n\n"
                    f"EVERY BALL COUNTS! 🏏"
                )
            })
            tr["super_thriller_alerted"] = True

        # Steep chase (RRR 14+)
        if (req_rate >= 14.0 and
                overs >= 10.0 and
                not tr.get("steep_chase_alerted")):
            alerts.append({
                "type": "steep_chase",
                "is_mega": False,
                "message": (
                    f"📈 <b>STEEP CHASE!</b>\n\n"
                    f"Required Rate: {req_rate}\n"
                    f"Need {runs_needed} off {balls_left} balls\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n\n"
                    f"Can they pull it off? 🤔"
                )
            })
            tr["steep_chase_alerted"] = True

    # Update tracking
    tr["last_runs"] = runs
    tr["last_overs"] = overs

    return alerts
