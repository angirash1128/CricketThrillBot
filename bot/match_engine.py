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
        url = f"https://{RAPIDAPI_HOST}/matches/recent"
        response = requests.get(url, headers=get_headers(), timeout=15)

        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            return None

        data = response.json()

        for t in data.get("typeMatches", []):
            for s in t.get("seriesMatches", []):
                w = s.get("seriesAdWrapper")
                if not w:
                    continue
                name = w.get("seriesName", "").upper()
                if "IPL" in name or "INDIAN PREMIER" in name:
                    for m in w.get("matches", []):
                        info = m.get("matchInfo", {})
                        state = info.get("state", "").lower()
                        if state in ["live", "in progress",
                                     "innings break", "complete"]:
                            print(f"Match found: {info.get('matchId')}")
                            return {
                                "match_id": str(info.get("matchId", "")),
                                "team1": info.get("team1", {}).get("teamName", "Team A"),
                                "team2": info.get("team2", {}).get("teamName", "Team B"),
                                "status": info.get("status", "")
                            }
        print("No IPL match in API response")
        return None

    except Exception as e:
        print(f"Match error: {e}")
        return None

def get_match_scorecard(match_id):
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        r = requests.get(url, headers=get_headers(), timeout=10)
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
        bat = curr.get("batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": curr.get("inningsId", 1),
            "runs": bat.get("runs", 0),
            "wickets": bat.get("wickets", 0),
            "overs": float(bat.get("overs", 0.0)),
            "target": data.get("matchHeader", {}).get("target", None)
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
    if innings_data["wickets"] > tr["wicket_count"]:
        alerts.append({
            "type": "wicket",
            "is_mega": False,
            "message": f"🚨 WICKET!\nScore: {innings_data['runs']}/{innings_data['wickets']}"
        })
        tr["wicket_count"] = innings_data["wickets"]
    if (innings_data["runs"] - tr["momentum_baseline"]) >= 12:
        alerts.append({
            "type": "momentum",
            "is_mega": False,
            "message": f"⚡ MOMENTUM SHIFT!\nScore: {innings_data['runs']}/{innings_data['wickets']}"
        })
        tr["momentum_baseline"] = innings_data["runs"]
    return alerts
