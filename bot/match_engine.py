import os
import requests

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"


def get_live_ipl_match():
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        print(f"CricAPI status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: {response.text[:200]}")
            return None

        data = response.json()

        if data.get("status") != "success":
            print(f"API status: {data.get('status')}")
            return None

        matches = data.get("data", [])
        print(f"Total matches: {len(matches)}")

        for match in matches:
            # CricketData fields
            name = match.get("name", "") or ""
            series = match.get("series", "") or ""
            ms = match.get("ms", "") or ""
            match_type = match.get("matchType", "") or ""

            name_upper = name.upper()
            series_upper = series.upper()

            # IPL detection
            is_ipl = (
                "IPL" in name_upper or
                "IPL" in series_upper or
                "INDIAN PREMIER" in name_upper or
                "INDIAN PREMIER" in series_upper
            )

            if is_ipl:
                print(f"IPL Found: {name} | ms={ms}")

                # Live check
                is_live = ms.lower() in [
                    "live", "in progress",
                    "innings break", "toss"
                ]

                if is_live:
                    t1 = match.get("t1", "") or match.get("team1", "") or "Team A"
                    t2 = match.get("t2", "") or match.get("team2", "") or "Team B"
                    status = match.get("status", "Live") or "Live"
                    match_id = match.get("id", "") or ""

                    print(f"✅ LIVE IPL: {t1} vs {t2}")

                    return {
                        "match_id": str(match_id),
                        "team1": t1,
                        "team2": t2,
                        "status": status,
                        "state": ms
                    }

        print("No live IPL match")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None


def get_match_scorecard(match_id):
    try:
        url = f"{BASE_URL}/match"
        params = {
            "apikey": CRICAPI_KEY,
            "id": match_id
        }
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()

        if data.get("status") != "success":
            return None

        return data.get("data", None)

    except Exception as e:
        print(f"Scorecard error: {e}")
        return None


def parse_current_innings(match_data):
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

        target = None
        if innings_id == 2 and len(score_list) >= 1:
            first = score_list[0]
            target = int(first.get("r", 0) or 0) + 1

        return {
            "innings_id": innings_id,
            "runs": runs,
            "wickets": wickets,
            "overs": overs,
            "target": target
        }

    except Exception as e:
        print(f"Parse error: {e}")
        return None


def debug_ipl_status():
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return f"API Error: {response.status_code}"

        data = response.json()

        if data.get("status") != "success":
            return f"Status: {data.get('status')}"

        matches = data.get("data", [])
        lines = [f"Total matches: {len(matches)}\n"]

        ipl_found = False
        live_found = False

        for match in matches:
            name = match.get("name", "") or ""
            series = match.get("series", "") or ""
            ms = match.get("ms", "") or ""
            t1 = match.get("t1", "") or ""
            t2 = match.get("t2", "") or ""

            if ("IPL" in name.upper() or
                    "IPL" in series.upper() or
                    "INDIAN PREMIER" in name.upper()):
                ipl_found = True
                lines.append(
                    f"IPL: {t1} vs {t2}\n"
                    f"  ms={ms}\n"
                    f"  name={name}\n"
                    f"  series={series}"
                )

                if ms.lower() in ["live", "in progress", "innings break"]:
                    live_found = True

        if not ipl_found:
            lines.append("No IPL match in API\n")
            lines.append("Sample matches (first 5):")
            for m in matches[:5]:
                name = m.get("name", "no name")
                ms = m.get("ms", "no ms")
                series = m.get("series", "no series")
                lines.append(f"  name={name} | ms={ms} | series={series}")

        if ipl_found and not live_found:
            lines.append("\nIPL match found but NOT live yet")

        return "\n".join(lines)

    except Exception as e:
        return f"Exception: {e}"


match_trackers = {}


def detect_thrills(match_id, innings_data):
    alerts = []

    if not innings_data:
        return alerts

    if match_id not in match_trackers:
        match_trackers[match_id] = {
            "innings_id": innings_data["innings_id"],
            "wicket_count": innings_data["wickets"],
            "momentum_baseline": innings_data["runs"],
            "thriller_alerted": False
        }
        return alerts

    tr = match_trackers[match_id]

    if tr["innings_id"] != innings_data["innings_id"]:
        match_trackers[match_id] = {
            "innings_id": innings_data["innings_id"],
            "wicket_count": innings_data["wickets"],
            "momentum_baseline": innings_data["runs"],
            "thriller_alerted": False
        }
        return alerts

    runs = innings_data["runs"]
    wickets = innings_data["wickets"]
    overs = innings_data["overs"]
    target = innings_data["target"]

    # Wicket alert
    if wickets > tr["wicket_count"]:
        alerts.append({
            "type": "wicket",
            "is_mega": False,
            "message": (
                f"🚨 <b>WICKET ALERT!</b>\n\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tr["wicket_count"] = wickets

    # Momentum
    if (runs - tr["momentum_baseline"]) >= 12:
        alerts.append({
            "type": "momentum",
            "is_mega": False,
            "message": (
                f"⚡ <b>MOMENTUM SHIFT!</b>\n\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tr["momentum_baseline"] = runs

    # Thriller
    if (
        target
        and innings_data["innings_id"] == 2
        and overs >= 16.0
        and not tr["thriller_alerted"]
    ):
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))
        if 0 < runs_needed <= 36:
            alerts.append({
                "type": "thriller",
                "is_mega": False,
                "message": (
                    f"🔴 <b>THRILLER FINISH!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Score: {runs}/{wickets}"
                )
            })
            tr["thriller_alerted"] = True

    return alerts
