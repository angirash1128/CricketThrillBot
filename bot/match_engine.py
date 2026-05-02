import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "cricbuzz-cricket.p.rapidapi.com"


def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }


def get_live_ipl_match():
    try:
        # SIRF /matches/live use karo
        url = f"https://{RAPIDAPI_HOST}/matches/live"
        response = requests.get(
            url, headers=get_headers(), timeout=15)

        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            return None

        data = response.json()

        for match_type in data.get("typeMatches", []):
            for series in match_type.get("seriesMatches", []):
                wrapper = series.get("seriesAdWrapper")
                if not wrapper:
                    continue

                series_name = wrapper.get("seriesName", "").upper()

                if "IPL" in series_name or "INDIAN PREMIER" in series_name:
                    for match in wrapper.get("matches", []):
                        info = match.get("matchInfo", {})
                        state = info.get("state", "").lower()

                        # Complete ko chhod kar sab accept karo
                        if state != "complete":
                            t1 = info.get("team1", {}).get(
                                "teamName", "Team A")
                            t2 = info.get("team2", {}).get(
                                "teamName", "Team B")
                            print(f"✅ IPL Match: {t1} vs {t2} | {state}")
                            return {
                                "match_id": str(info.get("matchId", "")),
                                "team1": t1,
                                "team2": t2,
                                "status": info.get("status", "Live"),
                                "state": state
                            }

        print("No IPL match in live endpoint")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None


def get_match_scorecard(match_id):
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        r = requests.get(url, headers=get_headers(), timeout=15)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def parse_current_innings(data):
    try:
        if not data:
            return None
        sc = data.get("scoreCard", [])
        if not sc:
            return None
        curr = sc[-1]
        bat = curr.get(
            "batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": curr.get("inningsId", 1),
            "runs": bat.get("runs", 0),
            "wickets": bat.get("wickets", 0),
            "overs": float(bat.get("overs", 0.0)),
            "target": data.get(
                "matchHeader", {}).get("target", None)
        }
    except Exception:
        return None


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
        if 0 < runs_needed <= 30:
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
