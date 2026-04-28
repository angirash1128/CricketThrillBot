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
        # Step 1: Recent matches fetch karo
        url = f"https://{RAPIDAPI_HOST}/matches/recent"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            return None
        
        data = response.json()
        
        # Step 2: Poore JSON data mein IPL match dhoondo (Hard Scan)
        type_matches = data.get("typeMatches", [])
        
        for t_match in type_matches:
            series_matches = t_match.get("seriesMatches", [])
            for s_match in series_matches:
                # seriesAdWrapper ke andar dhoondo
                wrapper = s_match.get("seriesAdWrapper")
                if not wrapper: continue
                
                s_name = wrapper.get("seriesName", "").upper()
                
                # Agar series IPL hai
                if "IPL" in s_name or "INDIAN PREMIER" in s_name:
                    matches = wrapper.get("matches", [])
                    for m in matches:
                        m_info = m.get("matchInfo", {})
                        state = m_info.get("state", "").lower()
                        
                        # ABHI TEST KE LIYE: Hum 'complete' ko bhi 'live' ki tarah dikhayenge
                        # Kal jab match live hoga, ye tab bhi kaam karega
                        if state in ["live", "in progress", "innings break", "complete"]:
                            print(f"✅ Found IPL Match: {m_info.get('matchId')}")
                            return {
                                "match_id": str(m_info.get("matchId", "")),
                                "team1": m_info.get("team1", {}).get("teamName", "Team A"),
                                "team2": m_info.get("team2", {}).get("teamName", "Team B"),
                                "status": m_info.get("status", "Match Finished")
                            }
        return None
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None

def get_match_scorecard(match_id):
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
    # Dummy function to keep main.py happy
    return []
