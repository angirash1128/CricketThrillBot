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
            return None

        data = response.json()

        for t in data.get("typeMatches", []):
            for s in t.get("seriesMatches", []):
                w = s.get("seriesAdWrapper")
                if not w: continue
                
                name = w.get("seriesName", "").upper()
                # Agar series IPL hai, toh match uthao
                if "IPL" in name or "INDIAN PREMIER" in name:
                    for m in w.get("matches", []):
                        info = m.get("matchInfo", {})
                        state = info.get("state", "").lower()
                        
                        # Sirf 'complete' ko chhod kar baaki sab dikhao (Live, Toss, Preview, In Progress)
                        if state != "complete":
                            print(f"✅ Match detected: {info.get('matchId')}")
                            return {
                                "match_id": str(info.get("matchId", "")),
                                "team1": info.get("team1", {}).get("teamName", "Team A"),
                                "team2": info.get("team2", {}).get("teamName", "Team B"),
                                "status": info.get("status", "Match is starting...")
                            }
        return None
    except Exception:
        return None

# Baki scorecard functions as it is rahenge (Niche paste mat karna agar pehle se hain)
