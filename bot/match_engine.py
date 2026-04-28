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
        url = f"https://{RAPIDAPI_HOST}/matches/live"
        response = requests.get(url, headers=get_headers(), timeout=10)

        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            return None

        data = response.json()

        for match_type in data.get("typeMatches", []):
            for series in match_type.get("seriesMatches", []):
                wrapper = series.get("seriesAdWrapper", {})
                name = wrapper.get("seriesName", "").upper()

                if "IPL" in name or "INDIAN PREMIER" in name:
                    for match in wrapper.get("matches", []):
                        info = match.get("matchInfo", {})
                        state = info.get("state", "").lower()

                        if state in ["live", "in progress", "innings break", "complete"]:
                            return {
                                "match_id": str(info.get("matchId", "")),
                                "team1": info.get("team1", {}).get("teamName", "Team A"),
                                "team2": info.get("team2", {}).get("teamName", "Team B"),
                                "status": info.get("status", "Live")
                            }
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None

def get_match_scorecard(match_id):
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        response = requests.get(url, headers=get_headers(), timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None

def parse_current_innings(scorecard_data):
    try:
        if not scorecard_data:
            return None
        sc = scorecard_data.get("scoreCard", [])
        if not sc:
            return None
        curr = sc[-1]
        bat = curr.get("batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": curr.get("inningsId", 1),
            "runs": bat.get("runs", 0),
            "wickets": bat.get("wickets", 0),
            "overs": float(bat.get("overs", 0.0)),
            "target": scorecard_data.get("matchHeader", {}).get("target", None)
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
            "momentum_baseline": innings_data["runs"]
        }
        return alerts

    tr = match_trackers[match_id]

    if tr["innings_id"] != innings_data["innings_id"]:
        match_trackers[match_id] = {
            "innings_id": innings_data["innings_id"],
            "wicket_count": innings_data["wickets"],
            "momentum_baseline": innings_data["runs"]
        }
        return alerts

    # Wicket alert
    if innings_data["wickets"] > tr["wicket_count"]:
        alerts.append({
            "type": "wicket",
            "is_mega": False,
            "message": (
                f"🚨 WICKET ALERT!\n\n"
                f"Score: {innings_data['runs']}/{innings_data['wickets']}\n"
                f"Overs: {innings_data['overs']}"
            )
        })
        tr["wicket_count"] = innings_data["wickets"]

    # Momentum alert
    runs_diff = innings_data["runs"] - tr["momentum_baseline"]
    if runs_diff >= 12:
        alerts.append({
            "type": "momentum",
            "is_mega": False,
            "message": (
                f"⚡ MOMENTUM SHIFT!\n\n"
                f"{runs_diff} runs scored rapidly!\n"
                f"Score: {innings_data['runs']}/{innings_data['wickets']}"
            )
        })
        tr["momentum_baseline"] = innings_data["runs"]

    return alerts
