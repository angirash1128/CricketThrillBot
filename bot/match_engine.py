import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "cricbuzz-cricket.p.rapidapi.com"

def get_live_ipl_match():
    try:
        url = f"https://{RAPIDAPI_HOST}/matches/recent"
        headers = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return {"error": f"API Status {response.status_code}"}
        
        data = response.json()
        found_series = []
        
        # Scanner Loop
        for t in data.get("typeMatches", []):
            for s in t.get("seriesMatches", []):
                wrapper = s.get("seriesAdWrapper")
                if wrapper:
                    s_name = wrapper.get("seriesName", "")
                    found_series.append(s_name)
                    
                    # Agar "IPL" word milta hai (kisi bhi form mein)
                    if "IPL" in s_name.upper() or "INDIAN PREMIER" in s_name.upper():
                        for m in wrapper.get("matches", []):
                            info = m.get("matchInfo", {})
                            state = info.get("state", "").lower()
                            if state != "complete":
                                return {
                                    "match_id": str(info.get("matchId")),
                                    "team1": info.get("team1", {}).get("teamName"),
                                    "team2": info.get("team2", {}).get("teamName"),
                                    "status": info.get("status")
                                }
        
        # Agar match nahi mila, toh report bhejo
        return {"error": "IPL Match Not Found", "found_series": found_series[:5]}
    except Exception as e:
        return {"error": str(e)}

# Baki dummy functions
def get_match_scorecard(mid): return None
def parse_current_innings(d): return None
def detect_thrills(mid, d): return []
