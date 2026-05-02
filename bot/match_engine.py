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
    # Dono endpoints try karenge
    endpoints = [
        "/matches/v1/live",
        "/matches/v1/recent"
    ]

    for endpoint in endpoints:
        try:
            url = f"https://{RAPIDAPI_HOST}{endpoint}"
            response = requests.get(
                url, headers=get_headers(), timeout=15)

            if response.status_code != 200:
                print(f"Endpoint {endpoint} failed: {response.status_code}")
                continue

            data = response.json()

            for t in data.get("typeMatches", []):
                for s in t.get("seriesMatches", []):
                    wrapper = s.get("seriesAdWrapper")
                    if not wrapper:
                        continue
                    name = wrapper.get("seriesName", "").upper()

                    if "IPL" in name or "INDIAN PREMIER" in name:
                        for m in wrapper.get("matches", []):
                            info = m.get("matchInfo", {})
                            state = info.get("state", "").lower()

                            if state != "complete":
                                print(f"✅ Match: {info.get('matchId')}")
                                return {
                                    "match_id": str(info.get("matchId")),
                                    "team1": info.get("team1", {}).get(
                                        "teamName", "Team A"),
                                    "team2": info.get("team2", {}).get(
                                        "teamName", "Team B"),
                                    "status": info.get("status", "Live")
                                }

        except Exception as e:
            print(f"Error {endpoint}: {e}")
            continue

    return None

def get_match_scorecard(match_id):
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        r = requests.get(url, headers=get_headers(), timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def parse_current_innings(data):
    try:
        if not data:
            return None
        sc = data.get("scoreCard", [])
        if not sc:
            return None
        curr = sc[-1]
        bat = curr.get(
            "batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": curr.get("inningsId", 1),
            "runs": bat.get("runs", 0),
            "wickets": bat.get("wickets", 0),
            "overs": float(bat.get("overs", 0.0)),
            "target": data.get(
                "matchHeader", {}).get("target", None)
        }
    except Exception:
        return None

def detect_thrills(match_id, data):
    return []
