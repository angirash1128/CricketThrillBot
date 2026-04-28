import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")

def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

def get_live_ipl_match():
    try:
        url = f"https://{RAPIDAPI_HOST}/matches/v1/live"
        response = requests.get(url, headers=get_headers(), timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return None
        
        data = response.json()
        type_matches = data.get("typeMatches", [])
        
        for match_type in type_matches:
            series_matches = match_type.get("seriesMatches", [])
            for series in series_matches:
                series_wrapper = series.get("seriesAdWrapper", {})
                series_name = series_wrapper.get("seriesName", "Unknown")
                
                # Debug log: Render logs mein dikhega ki kaunsi series mil rahi hai
                print(f"🔍 Found series: {series_name}")
                
                # Sabse flexible check: Agar series name mein IPL ya Indian Premier hai
                if "IPL" in series_name.upper() or "INDIAN PREMIER" in series_name.upper():
                    matches = series_wrapper.get("matches", [])
                    for match in matches:
                        match_info = match.get("matchInfo", {})
                        match_score = match.get("matchScore", {})
                        
                        state = match_info.get("state", "")
                        # Hum sirf Live ya In-Progress matches lenge
                        if state.lower() in ["live", "innings break", "in progress"]:
                            return {
                                "match_id": str(match_info.get("matchId", "")),
                                "team1": match_info.get("team1", {}).get("teamName", "Team A"),
                                "team2": match_info.get("team2", {}).get("teamName", "Team B"),
                                "state": state,
                                "status": match_info.get("status", ""),
                                "score_data": match_score
                            }
        return None
    except Exception as e:
        print(f"❌ get_live_ipl_match error: {e}")
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
        if not scorecard_data: return None
        score_card = scorecard_data.get("scoreCard", [])
        if not score_card: return None
        current = score_card[-1]
        bat_score = current.get("batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": current.get("inningsId", 1),
            "runs": bat_score.get("runs", 0),
            "wickets": bat_score.get("wickets", 0),
            "overs": float(bat_score.get("overs", 0.0)),
            "target": scorecard_data.get("matchHeader", {}).get("target", None)
        }
    except Exception: return None

match_trackers = {}

def get_tracker(match_id):
    if match_id not in match_trackers:
        match_trackers[match_id] = {
            "innings_id": None, "wicket_count": 0, "momentum_baseline": 0,
            "thriller_alerted": False, "super_over_alerted": False
        }
    return match_trackers[match_id]

def detect_thrills(match_id, innings_data):
    alerts = []
    if not innings_data: return alerts
    tracker = get_tracker(match_id)
    
    runs, wickets, overs = innings_data["runs"], innings_data["wickets"], innings_data["overs"]
    
    if tracker["innings_id"] != innings_data["innings_id"]:
        tracker.update({"innings_id": innings_data["innings_id"], "wicket_count": wickets, "momentum_baseline": runs, "thriller_alerted": False})
        return alerts

    if wickets > tracker["wicket_count"]:
        alerts.append({"type": "wicket", "is_mega": False, "message": f"🚨 WICKET!\nScore: {runs}/{wickets}\nOvers: {overs}"})
        tracker["wicket_count"] = wickets

    if (runs - tracker["momentum_baseline"]) >= 12:
        alerts.append({"type": "momentum", "is_mega": False, "message": f"⚡ MOMENTUM SHIFT!\n{runs-tracker['momentum_baseline']} runs rapidly!\nScore: {runs}/{wickets}"})
        tracker["momentum_baseline"] = runs

    return alerts
