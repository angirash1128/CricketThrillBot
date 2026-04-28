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
        response = requests.get(url, headers=get_headers(), timeout=10)

        if response.status_code != 200:
            print("API ERROR:", response.text)
            return None

        data = response.json()
        type_matches = data.get("typeMatches", [])

        for match_type in type_matches:
            for series in match_type.get("seriesMatches", []):
                wrapper = series.get("seriesAdWrapper", {})
                series_name = wrapper.get("seriesName", "").upper()

                if "IPL" in series_name:
                    for match in wrapper.get("matches", []):
                        info = match.get("matchInfo", {})
                        state = info.get("state", "").lower()

                        if state in ["live", "in progress", "innings break"]:
                            return {
                                "match_id": str(info.get("matchId", "")),
                                "team1": info.get("team1", {}).get("teamName", ""),
                                "team2": info.get("team2", {}).get("teamName", ""),
                                "status": info.get("status", "")
                            }

        return None

    except Exception as e:
        print("MATCH ERROR:", e)
        return None
