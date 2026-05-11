import os
import requests

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"


def get_live_ipl_match():
    """
    Live IPL match dhundo - 1 API call
    """
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            print(f"CricScore error: {response.status_code}")
            return None

        data = response.json()
        if data.get("status") != "success":
            return None

        matches = data.get("data", [])

        for match in matches:
            # Try all possible field names
            name = (
                match.get("name", "") or
                match.get("matchName", "") or
                match.get("title", "") or ""
            )
            series = (
                match.get("series", "") or
                match.get("seriesName", "") or ""
            )
            ms = (
                match.get("ms", "") or
                match.get("matchStatus", "") or
                match.get("status", "") or ""
            )

            name_upper = name.upper()
            series_upper = series.upper()

            is_ipl = (
                "IPL" in name_upper or
                "IPL" in series_upper or
                "INDIAN PREMIER" in name_upper or
                "INDIAN PREMIER" in series_upper
            )

            if not is_ipl:
                continue

            ms_lower = ms.lower()
            is_live = (
                "live" in ms_lower or
                "progress" in ms_lower or
                "innings" in ms_lower or
                "toss" in ms_lower or
                "break" in ms_lower
            )

            if is_live:
                # Team names - try multiple fields
                t1 = (
                    match.get("t1", "") or
                    match.get("team1", "") or
                    match.get("teamInfo", [{}])[0].get("name", "") if match.get("teamInfo") else ""
                ) or "Team A"

                t2 = (
                    match.get("t2", "") or
                    match.get("team2", "") or
                    match.get("teamInfo", [{}])[1].get("name", "") if match.get("teamInfo") and len(match.get("teamInfo", [])) > 1 else ""
                ) or "Team B"

                match_id = (
                    match.get("id", "") or
                    match.get("matchId", "") or ""
                )

                status = (
                    match.get("status", "") or
                    match.get("matchStatus", "") or "Live"
                )

                # Toss info
                toss = match.get("tpiw", "") or match.get("toss", "") or ""

                print(f"IPL LIVE: {t1} vs {t2} | {ms}")

                return {
                    "match_id": str(match_id),
                    "team1": t1,
                    "team2": t2,
                    "status": status,
                    "state": ms,
                    "toss": toss,
                    "name": name
                }

        return None

    except Exception as e:
        print(f"get_live_ipl_match error: {e}")
        return None


def get_match_scorecard(match_id):
    """
    Match ka detailed scorecard - 1 API call
    """
    try:
        url = f"{BASE_URL}/match"
        params = {"apikey": CRICAPI_KEY, "id": match_id}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()
        if data.get("status") != "success":
            return None

        return data.get("data", None)

    except Exception as e:
        print(f"scorecard error: {e}")
        return None


def parse_current_innings(match_data):
    """
    Match data se current innings ki info nikalo
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
        innings_id = len(score_list)
        inning_name = current.get("inning", "") or ""

        target = None
        if innings_id >= 2:
            first = score_list[0]
            target = int(first.get("r", 0) or 0) + 1

        # Run rate calculate karo
        run_rate = 0.0
        if overs > 0:
            run_rate = round(runs / overs, 2)

        # Required run rate (2nd innings)
        req_rate = 0.0
        if target and innings_id >= 2 and overs < 20:
            balls_left = max(1, int((20 - overs) * 6))
            runs_needed = target - runs
            overs_left = balls_left / 6
            if overs_left > 0:
                req_rate = round(runs_needed / overs_left, 2)

        return {
            "innings_id": innings_id,
            "inning_name": inning_name,
            "runs": runs,
            "wickets": wickets,
            "overs": overs,
            "target": target,
            "run_rate": run_rate,
            "req_rate": req_rate
        }

    except Exception as e:
        print(f"parse error: {e}")
        return None


def debug_ipl_status():
    """Debug report"""
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return f"API Error: {response.status_code}"

        data = response.json()
        if data.get("status") != "success":
            info = data.get("info", "no info")
            return f"Status: {data.get('status')}\nInfo: {info}"

        matches = data.get("data", [])
        lines = [f"Total matches: {len(matches)}\n"]

        ipl_count = 0
        for match in matches:
            name = match.get("name", "") or match.get("matchName", "") or ""
            series = match.get("series", "") or match.get("seriesName", "") or ""
            ms = match.get("ms", "") or match.get("matchStatus", "") or ""
            t1 = match.get("t1", "") or match.get("team1", "") or ""
            t2 = match.get("t2", "") or match.get("team2", "") or ""

            if "IPL" in name.upper() or "IPL" in series.upper() or "INDIAN PREMIER" in name.upper():
                ipl_count += 1
                lines.append(
                    f"✅ IPL: {t1} vs {t2}\n"
                    f"   ms={ms}\n"
                    f"   series={series}"
                )

        if ipl_count == 0:
            lines.append("❌ No IPL match found\n")
            lines.append("Sample (first 5):")
            for m in matches[:5]:
                n = m.get("name", "") or m.get("matchName", "") or "no name"
                s = m.get("series", "") or m.get("seriesName", "") or "no series"
                ms = m.get("ms", "") or m.get("matchStatus", "") or "no ms"
                lines.append(f"  name={n[:40]}")
                lines.append(f"  series={s[:30]}")
                lines.append(f"  ms={ms}\n")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# THRILL DETECTION ENGINE
# ─────────────────────────────────────────

match_trackers = {}


def detect_thrills(match_id, innings_data):
    """
    IPL-specific thrill detection

    IPL Normal Values:
    - Average score: 170-180
    - Normal run rate: 8.5-9.0
    - Death overs RR: 10-14
    - Powerplay RR: 8-10

    THRILL triggers:
    - 18+ runs in last check (explosive over)
    - 2+ wickets since last check (collapse starting)
    - 5+ total wickets (deep trouble)
    - Last 5 overs + close chase
    - Last 2 overs + very close
    - Required rate 14+ (very difficult chase)
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
            "collapse_alerted": False,
            "super_thriller_alerted": False,
            "explosive_alerted_at": 0
        }
        return alerts

    tr = match_trackers[mid]

    # Innings change - reset
    if tr["innings_id"] != innings_data["innings_id"]:
        match_trackers[mid] = {
            "innings_id": innings_data["innings_id"],
            "wicket_count": innings_data["wickets"],
            "last_runs": innings_data["runs"],
            "last_overs": innings_data["overs"],
            "thriller_alerted": False,
            "collapse_alerted": False,
            "super_thriller_alerted": False,
            "explosive_alerted_at": 0
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
    overs_diff = overs - tr["last_overs"]

    # ─── WICKET ALERTS ───

    # Multiple wickets fell quickly (2+ since last check)
    if wickets_diff >= 2:
        alerts.append({
            "type": "collapse",
            "is_mega": True,
            "message": (
                f"😱 <b>WICKETS TUMBLING!</b>\n\n"
                f"{wickets_diff} wickets fell!\n"
                f"Score: {runs}/{wickets} ({overs} ov)\n"
                f"Run Rate: {run_rate}\n\n"
                f"Match turning! 🔥"
            )
        })
        tr["wicket_count"] = wickets

    # Single important wicket (5+ wickets = deep trouble)
    elif wickets_diff == 1 and wickets >= 5:
        alerts.append({
            "type": "wicket",
            "is_mega": False,
            "message": (
                f"🚨 <b>WICKET!</b>\n\n"
                f"Score: {runs}/{wickets} ({overs} ov)\n"
                f"Team in trouble! 😰"
            )
        })
        tr["wicket_count"] = wickets

    # Batting collapse (5+ wickets with low score)
    elif wickets >= 5 and not tr["collapse_alerted"]:
        expected_score = overs * 8.5  # IPL average
        if runs < expected_score * 0.7:  # 30% below average
            alerts.append({
                "type": "collapse",
                "is_mega": True,
                "message": (
                    f"💥 <b>BATTING COLLAPSE!</b>\n\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n"
                    f"Run Rate: {run_rate}\n"
                    f"Well below par score! 📉"
                )
            })
            tr["collapse_alerted"] = True

    # Update wicket count
    if wickets > tr["wicket_count"]:
        tr["wicket_count"] = wickets

    # ─── EXPLOSIVE BATTING ───

    # 18+ runs since last check (IPL mein 18+ in ~2-3 overs is explosive)
    if runs_diff >= 18 and overs > tr.get("explosive_alerted_at", 0) + 2:
        alerts.append({
            "type": "explosive",
            "is_mega": False,
            "message": (
                f"💥 <b>EXPLOSIVE BATTING!</b>\n\n"
                f"{runs_diff} runs scored!\n"
                f"Score: {runs}/{wickets} ({overs} ov)\n"
                f"Run Rate: {run_rate} 🚀"
            )
        })
        tr["explosive_alerted_at"] = overs

    # ─── THRILLER CHASE (2nd innings only) ───

    if target and innings_data["innings_id"] >= 2:
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))

        # Last 5 overs + close match
        if (
            overs >= 15.0
            and 0 < runs_needed <= 60
            and not tr["thriller_alerted"]
        ):
            alerts.append({
                "type": "thriller",
                "is_mega": True,
                "message": (
                    f"🔴 <b>THRILLER ALERT!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n"
                    f"Required Rate: {req_rate}\n\n"
                    f"🏏 Game on!"
                )
            })
            tr["thriller_alerted"] = True

        # Last 3 overs + very close
        if (
            overs >= 17.0
            and 0 < runs_needed <= 30
            and not tr["super_thriller_alerted"]
        ):
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

        # Required rate very high (14+) = difficult chase
        if req_rate >= 14.0 and overs >= 10.0 and not tr.get("high_rr_alerted"):
            alerts.append({
                "type": "high_required",
                "is_mega": False,
                "message": (
                    f"📈 <b>STEEP CHASE!</b>\n\n"
                    f"Required Rate: {req_rate}\n"
                    f"Need {runs_needed} off {balls_left} balls\n"
                    f"Score: {runs}/{wickets} ({overs} ov)\n\n"
                    f"Can they pull it off? 🤔"
                )
            })
            tr["high_rr_alerted"] = True

    # Update tracking
    tr["last_runs"] = runs
    tr["last_overs"] = overs

    return alerts
