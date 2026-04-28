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
    """
    Ab hum seedha Match Info endpoint se data uthayenge 
    taaki series name ka jhamela na rahe.
    """
    try:
        # Step 1: Recent matches se pehla match uthao jo IPL series ka ho
        url = f"https://{RAPIDAPI_HOST}/matches/recent"
        response = requests.get(url, headers=get_headers(), timeout=10)
        
        if response.status_code != 200: return None
        
        data = response.json()
        type_matches = data.get("typeMatches", [])
        
        for match_type in type_matches:
            series_matches = match_type.get("seriesMatches", [])
            for series in series_matches:
                sw = series.get("seriesAdWrapper", {})
                s_name = sw.get("seriesName", "").upper()
                
                # Agar series name mein IPL hai, to uske saare matches check karo
                if "IPL" in s_name or "INDIAN PREMIER" in s_name:
                    matches = sw.get("matches", [])
                    for m in matches:
                        m_info = m.get("matchInfo", {})
                        m_score = m.get("matchScore", {})
                        state = m_info.get("state", "").lower()
                        
                        # Agar match Live ya In-Progress hai
                        if state in ["live", "in progress", "innings break"]:
                            return {
                                "match_id": str(m_info.get("matchId", "")),
                                "team1": m_info.get("team1", {}).get("teamName", "Team A"),
                                "team2": m_info.get("team2", {}).get("teamName", "Team B"),
                                "state": m_info.get("state", ""),
                                "status": m_info.get("status", ""),
                                "score_data": m_score
                            }
        
        # Agar loop se nahi mila, to manually match list mangwao
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_match_scorecard(match_id):
    """Is endpoint se live score confirm hota hai"""
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        response = requests.get(url, headers=get_headers(), timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception: return None

def parse_current_innings(scorecard_data):
    try:
        if not scorecard_data: return None
        sc = scorecard_data.get("scoreCard", [])
        if not sc: return None
        curr = sc[-1]
        bat = curr.get("batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": curr.get("inningsId", 1),
            "runs": bat.get("runs", 0),
            "wickets": bat.get("wickets", 0),
            "overs": float(bat.get("overs", 0.0)),
            "target": scorecard_data.get("matchHeader", {}).get("target", None)
        }
    except Exception: return None

match_trackers = {}

def detect_thrills(match_id, innings_data):
    alerts = []
    if not innings_data: return alerts
    
    if match_id not in match_trackers:
        match_trackers[match_id] = {"innings_id": innings_data["innings_id"], "wicket_count": innings_data["wickets"], "momentum_baseline": innings_data["runs"]}
        return alerts
    
    tr = match_trackers[match_id]
    if tr["innings_id"] != innings_data["innings_id"]:
        tr.update({"innings_id": innings_data["innings_id"], "wicket_count": innings_data["wickets"], "momentum_baseline": innings_data["runs"]})
        return alerts

    if innings_data["wickets"] > tr["wicket_count"]:
        alerts.append({"type": "wicket", "is_mega": False, "message": f"🚨 WICKET!\nScore: {innings_data['runs']}/{innings_data['wickets']}"})
        tr["wicket_count"] = innings_data["wickets"]

    if (innings_data["runs"] - tr["momentum_baseline"]) >= 12:
        alerts.append({"type": "momentum", "is_mega": False, "message": f"⚡ MOMENTUM!\nScore: {innings_data['runs']}/{innings_data['wickets']}"})
        tr["momentum_baseline"] = innings_data["runs"]

    return alerts
