import os
import requests

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"


def get_live_ipl_match():
    """
    CricketData.org se live IPL match dhundo
    """
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        print(f"CricAPI status: {response.status_code}")

        if response.status_code != 200:
            print(f"CricAPI error: {response.text[:200]}")
            return None

        data = response.json()

        if data.get("status") != "success":
            print(f"CricAPI not success: {data.get('status')}")
            return None

        matches = data.get("data", [])

        for match in matches:
            name = match.get("name", "").upper()
            series = match.get("series", "").upper()
            ms = match.get("ms", "")  # match state

            # IPL check
            if "IPL" in name or "IPL" in series or "INDIAN PREMIER" in name:
                # Live match check
                if ms in ["live", "result"] or "live" in ms.lower():
                    team1 = match.get("t1", "Team A")
                    team2 = match.get("t2", "Team B")
                    status = match.get("status", "Live")
                    match_id = match.get("id", "")

                    print(f"✅ IPL Live: {team1} vs {team2} | {ms}")

                    return {
                        "match_id": str(match_id),
                        "team1": team1,
                        "team2": team2,
                        "status": status,
                        "state": ms
                    }

        print("No live IPL match found")
        return None

    except Exception as e:
        print(f"get_live_ipl_match error: {e}")
        return None


def get_match_scorecard(match_id):
    """
    Specific match ka scorecard lo
    """
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
        print(f"get_match_scorecard error: {e}")
        return None


def parse_current_innings(match_data):
    """
    Match data se current innings info nikalo
    """
    try:
        if not match_data:
            return None

        score_list = match_data.get("score", [])

        if not score_list:
            return None

        # Last innings = current
        current = score_list[-1]

        runs = current.get("r", 0)
        wickets = current.get("w", 0)
        overs = current.get("o", 0.0)
        innings_id = len(score_list)

        # Target for 2nd innings
        target = None
        if innings_id == 2 and len(score_list) >= 1:
            first_innings = score_list[0]
            target = first_innings.get("r", 0) + 1

        return {
            "innings_id": innings_id,
            "runs": int(runs),
            "wickets": int(wickets),
            "overs": float(overs),
            "target": target
        }

    except Exception as e:
        print(f"parse_current_innings error: {e}")
        return None


def debug_ipl_status():
    """
    Debug report for bot
    """
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return f"API Error: {response.status_code}\n{response.text[:200]}"

        data = response.json()

        if data.get("status") != "success":
            return f"API Status: {data.get('status')}\nInfo: {data.get('info', '')}"

        matches = data.get("data", [])
        lines = [f"Total matches in API: {len(matches)}\n"]

        ipl_found = False
        for match in matches:
            name = match.get("name", "")
            series = match.get("series", "")
            ms = match.get("ms", "")
            t1 = match.get("t1", "")
            t2 = match.get("t2", "")

            if "IPL" in name.upper() or "IPL" in series.upper():
                ipl_found = True
                lines.append(
                    f"✅ IPL: {t1} vs {t2}\n"
                    f"   state={ms}\n"
                    f"   series={series}"
                )

        if not ipl_found:
            lines.append("❌ No IPL match found in API response")
            lines.append("\nAll matches:")
            for m in matches[:5]:
                lines.append(f"  - {m.get('name', 'unknown')} | {m.get('ms', '')}")

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

    # Innings change
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

    # Momentum shift
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

    # Thriller finish
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
