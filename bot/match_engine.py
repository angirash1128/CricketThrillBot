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
        if response.status_code != 200: return None
        data = response.json()

        # DEEP SCAN: JSON ke har hisse mein IPL match dhoondo
        for type_match in data.get("typeMatches", []):
            for series_match in type_match.get("seriesMatches", []):
                wrapper = series_match.get("seriesAdWrapper")
                if not wrapper: continue
                
                # Check Series Name
                s_name = wrapper.get("seriesName", "").upper()
                if "IPL" in s_name or "INDIAN PREMIER" in s_name:
                    matches = wrapper.get("matches", [])
                    # Sabse pehla match uthao jo complete na ho, ya last match uthao
                    for m in matches:
                        m_info = m.get("matchInfo", {})
                        state = m_info.get("state", "").lower()
                        
                        # Agar match complete nahi hai, toh ye hi live hai!
                        if state != "complete":
                            return {
                                "match_id": str(m_info.get("matchId")),
                                "team1": m_info.get("team1", {}).get("teamName", "Team 1"),
                                "team2": m_info.get("team2", {}).get("teamName", "Team 2"),
                                "status": m_info.get("status", "Match Live")
                            }
        return None
    except Exception: return None

def get_match_scorecard(match_id):
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        r = requests.get(url, headers=get_headers(), timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception: return None

def parse_current_innings(data):
    try:
        if not data: return None
        sc = data.get("scoreCard", [])
        if not sc: return None
        curr = sc[-1]
        bat = curr.get("batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": curr.get("inningsId", 1),
            "runs": bat.get("runs", 0),
            "wickets": bat.get("wickets", 0),
            "overs": float(bat.get("overs", 0.0)),
            "target": data.get("matchHeader", {}).get("target", None)
        }
    except Exception: return None

def detect_thrills(match_id, innings_data):
    # alerts logic...
    return []
