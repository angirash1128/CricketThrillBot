import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")


def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }


def fetch_endpoint(endpoint):
    """
    Endpoint se data lao.
    Returns:
    {
        "ok": True/False,
        "status_code": int,
        "data": json or None,
        "error": str or None
    }
    """
    try:
        url = f"https://{RAPIDAPI_HOST}{endpoint}"
        response = requests.get(url, headers=get_headers(), timeout=15)

        result = {
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "data": None,
            "error": None
        }

        if response.status_code == 200:
            result["data"] = response.json()
        else:
            result["error"] = response.text[:300]

        return result

    except Exception as e:
        return {
            "ok": False,
            "status_code": 0,
            "data": None,
            "error": str(e)
        }


def extract_first_ipl_match(data, include_complete=False):
    """
    API response me pehla IPL match dhundo.
    include_complete=False => complete match ignore karega
    """
    if not data:
        return None

    try:
        for match_type in data.get("typeMatches", []):
            for series in match_type.get("seriesMatches", []):
                wrapper = series.get("seriesAdWrapper")
                if not wrapper:
                    continue

                series_name = wrapper.get("seriesName", "")
                series_name_upper = series_name.upper()

                if "IPL" in series_name_upper or "INDIAN PREMIER" in series_name_upper:
                    matches = wrapper.get("matches", [])

                    for match in matches:
                        info = match.get("matchInfo", {})
                        state = info.get("state", "").lower()
                        status = info.get("status", "")

                        if not include_complete and state == "complete":
                            continue

                        return {
                            "match_id": str(info.get("matchId", "")),
                            "team1": info.get("team1", {}).get("teamName", "Team A"),
                            "team2": info.get("team2", {}).get("teamName", "Team B"),
                            "status": status or "No status",
                            "state": state or "unknown",
                            "series_name": series_name
                        }

        return None

    except Exception:
        return None


def get_live_ipl_match():
    """
    Priority:
    1. /matches/live
    2. /matches/upcoming
    """
    # Live endpoint
    live_result = fetch_endpoint("/matches/live")
    if live_result["ok"]:
        live_match = extract_first_ipl_match(
            live_result["data"],
            include_complete=False
        )
        if live_match:
            return live_match

    # Upcoming endpoint
    upcoming_result = fetch_endpoint("/matches/upcoming")
    if upcoming_result["ok"]:
        upcoming_match = extract_first_ipl_match(
            upcoming_result["data"],
            include_complete=False
        )
        if upcoming_match:
            return upcoming_match

    return None


def debug_ipl_status():
    """
    Debug report banao taaki bot se hi pata chale
    API kya de rahi hai.
    """
    lines = []

    for endpoint in ["/matches/live", "/matches/upcoming", "/matches/recent"]:
        result = fetch_endpoint(endpoint)

        if not result["ok"]:
            lines.append(
                f"{endpoint} → {result['status_code']} | {result['error'] or 'error'}"
            )
            continue

        match = extract_first_ipl_match(
            result["data"],
            include_complete=True
        )

        if match:
            lines.append(
                f"{endpoint} → "
                f"{match['team1']} vs {match['team2']} | "
                f"state={match['state']} | status={match['status']}"
            )
        else:
            lines.append(f"{endpoint} → IPL not found")

    return "\n".join(lines)


def get_match_scorecard(match_id):
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        response = requests.get(url, headers=get_headers(), timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def parse_current_innings(scorecard_data):
    try:
        if not scorecard_data:
            return None

        score_card = scorecard_data.get("scoreCard", [])
        if not score_card:
            return None

        current = score_card[-1]
        bat_team_details = current.get("batTeamDetails", {})
        bat_score = bat_team_details.get("batTeamScoreDetails", {})

        return {
            "innings_id": current.get("inningsId", 1),
            "runs": bat_score.get("runs", 0),
            "wickets": bat_score.get("wickets", 0),
            "overs": float(bat_score.get("overs", 0.0)),
            "target": scorecard_data.get("matchHeader", {}).get("target", None)
        }

    except Exception:
        return None


def detect_thrills(match_id, innings_data):
    # Abhi simple rakha hai
    return []
