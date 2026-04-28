import os
import requests

# Render Environment se key lega
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "cricbuzz-cricket.p.rapidapi.com"

def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

def get_live_ipl_match():
    # Hum do alag tareeko se match dhundenge
    endpoints = ["/matches/live", "/matches/recent"]
    
    for endpoint in endpoints:
        try:
            url = f"https://{RAPIDAPI_HOST}{endpoint}"
            response = requests.get(url, headers=get_headers(), timeout=15)

            if response.status_code != 200:
                print(f"DEBUG: Endpoint {endpoint} failed with {response.status_code}")
                continue

            data = response.json()
            type_matches = data.get("typeMatches", [])

            for match_type in type_matches:
                for series in match_type.get("seriesMatches", []):
                    wrapper = series.get("seriesAdWrapper", {})
                    series_name = wrapper.get("seriesName", "").upper()

                    # Flexible IPL detection
                    if "IPL" in series_name or "INDIAN PREMIER" in series_name:
                        for match in wrapper.get("matches", []):
                            info = match.get("matchInfo", {})
                            state = info.get("state", "").lower()

                            # State can be 'live', 'in progress', or 'innings break'
                            if state in ["live", "in progress", "innings break"]:
                                print(f"DEBUG: Found IPL Match: {info.get('team1', {}).get('teamName')} vs {info.get('team2', {}).get('teamName')}")
                                return {
                                    "match_id": str(info.get("matchId", "")),
                                    "team1": info.get("team1", {}).get("teamName", "Team A"),
                                    "team2": info.get("team2", {}).get("teamName", "Team B"),
                                    "status": info.get("status", "Live Match")
                                }
        except Exception as e:
            print(f"DEBUG: Error on {endpoint}: {e}")
            continue

    return None
