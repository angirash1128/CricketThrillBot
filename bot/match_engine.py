import os
import requests

# Render se key lega
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "cricbuzz-cricket.p.rapidapi.com"

def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

def get_live_ipl_match():
    """
    Direct Match ID (151976) se data fetch karega. 
    Koi search filter nahi!
    """
    match_id = "151976" # RR vs DC
    try:
        # Seedha scorecard endpoint check karo
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            return {
                "match_id": match_id,
                "team1": "Rajasthan Royals",
                "team2": "Delhi Capitals",
                "status": "Match is LIVE 🏏"
            }
        else:
            print(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

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
    return [] # dummy for now
