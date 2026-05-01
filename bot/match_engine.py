import os
import requests
from datetime import datetime

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "cricbuzz-cricket.p.rapidapi.com"

def get_headers():
    return {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}

def get_live_ipl_match():
    # 200 limit hai, isliye hum sirf sham ko check karenge
    now = datetime.now()
    if now.hour < 19: # Sham 7 baje se pehle kuch nahi dhoondna
        return None

    try:
        url = f"https://{RAPIDAPI_HOST}/matches/recent"
        response = requests.get(url, headers=get_headers(), timeout=15)
        if response.status_code != 200: return None
        
        data = response.json()
        for t in data.get("typeMatches", []):
            for s in t.get("seriesMatches", []):
                wrapper = s.get("seriesAdWrapper")
                if not wrapper: continue
                if "IPL" in wrapper.get("seriesName", "").upper():
                    for m in wrapper.get("matches", []):
                        info = m.get("matchInfo", {})
                        if info.get("state", "").lower() != "complete":
                            return {
                                "match_id": str(info.get("matchId")),
                                "team1": info.get("team1", {}).get("teamName"),
                                "team2": info.get("team2", {}).get("teamName"),
                                "status": info.get("status")
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
