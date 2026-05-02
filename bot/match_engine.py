import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "cricbuzz-cricket.p.rapidapi.com"


def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }


def extract_ipl_match(data, allow_complete=False):
    """
    API response me IPL match dhundo.
    allow_complete=False means sirf live/upcoming type match return karo.
    """
    try:
        for match_type in data.get("typeMatches", []):
            for series in match_type.get("seriesMatches", []):
                wrapper = series.get("seriesAdWrapper")
                if not wrapper:
                    continue

                series_name = wrapper.get("seriesName", "").upper()

                if "IPL" in series_name or "INDIAN PREMIER" in series_name:
                    matches = wrapper.get("matches", [])

                    for match in matches:
                        info = match.get("matchInfo", {})
                        state = info.get("state", "").lower()
                        status = info.get("status", "")

                        if allow_complete:
                            return {
                                "match_id": str(info.get("matchId", "")),
                                "team1": info.get("team1", {}).get("teamName", "Team A"),
                                "team2": info.get("team2", {}).get("teamName", "Team B"),
                                "status": status,
                                "state": state
                            }

                        # Live / toss / preview / innings break / in progress
                        if state != "complete":
                            return {
                                "match_id": str(info.get("matchId", "")),
                                "team1": info.get("team1", {}).get("teamName", "Team A"),
                                "team2": info.get("team2", {}).get("teamName", "Team B"),
                                "status": status,
                                "state": state
                            }

        return None
    except Exception as e:
        print(f"extract_ipl_match error: {e}")
        return None


def fetch_endpoint(endpoint):
    try:
        url = f"https://{RAPIDAPI_HOST}{endpoint}"
        response = requests.get(url, headers=get_headers(), timeout=15)

        if response.status_code != 200:
            print(f"{endpoint} failed: {response.status_code}")
            return None

        return response.json()
    except Exception as e:
        print(f"{endpoint} error: {e}")
        return None


def get_live_ipl_match():
    """
    Priority:
    1. /matches/live
    2. /matches/upcoming
    3. None
    """
    # 1. Live endpoint
    live_data = fetch_endpoint("/matches/live")
    if live_data:
        live_match = extract_ipl_match(live_data, allow_complete=False)
        if live_match:
            print(f"✅ LIVE IPL found: {live_match['team1']} vs {live_match['team2']}")
            return live_match

    # 2. Upcoming endpoint
    upcoming_data = fetch_endpoint("/matches/upcoming")
    if upcoming_data:
        upcoming_match = extract_ipl_match(upcoming_data, allow_complete=False)
        if upcoming_match:
            print(f"✅ UPCOMING IPL found: {upcoming_match['team1']} vs {upcoming_match['team2']}")
            return upcoming_match

    print("No live/upcoming IPL match found")
    return None


def get_match_scorecard(match_id):
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        response = requests.get(url, headers=get_headers(), timeout=15)

        if response.status_code != 200:
            print(f"scorecard failed: {response.status_code}")
            return None

        return response.json()
    except Exception as e:
        print(f"scorecard error: {e}")
        return None


def parse_current_innings(scorecard_data):
    try:
        if not scorecard_data:
            return None

        score_card = scorecard_data.get("scoreCard", [])
        if not score_card:
            return None

        current = score_card[-1]
        innings_id = current.get("inningsId", 1)

        bat_team_details = current.get("batTeamDetails", {})
        bat_score = bat_team_details.get("batTeamScoreDetails", {})

        runs = bat_score.get("runs", 0)
        wickets = bat_score.get("wickets", 0)
        overs = bat_score.get("overs", 0.0)

        target = None
        if innings_id == 2:
            match_header = scorecard_data.get("matchHeader", {})
            target = match_header.get("target", None)

        return {
            "innings_id": innings_id,
            "runs": runs,
            "wickets": wickets,
            "overs": float(overs),
            "target": target
        }

    except Exception as e:
        print(f"parse_current_innings error: {e}")
        return None


match_trackers = {}


def detect_thrills(match_id, innings_data):
    alerts = []

    if not innings_data:
        return alerts

    if match_id not in match_trackers:
        match_trackers[match_id] = {
            "innings_id": innings_data["innings_id"],
            "wicket_count": innings_data["wickets"],
            "momentum_baseline": innings_data["runs"],
            "thriller_alerted": False
        }
        return alerts

    tracker = match_trackers[match_id]

    # innings change reset
    if tracker["innings_id"] != innings_data["innings_id"]:
        match_trackers[match_id] = {
            "innings_id": innings_data["innings_id"],
            "wicket_count": innings_data["wickets"],
            "momentum_baseline": innings_data["runs"],
            "thriller_alerted": False
        }
        return alerts

    runs = innings_data["runs"]
    wickets = innings_data["wickets"]
    overs = innings_data["overs"]
    target = innings_data["target"]

    # wicket alert
    if wickets > tracker["wicket_count"]:
        alerts.append({
            "type": "wicket",
            "is_mega": False,
            "message": (
                f"🚨 <b>WICKET ALERT!</b>\n\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tracker["wicket_count"] = wickets

    # momentum shift
    if (runs - tracker["momentum_baseline"]) >= 12:
        alerts.append({
            "type": "momentum",
            "is_mega": False,
            "message": (
                f"⚡ <b>MOMENTUM SHIFT!</b>\n\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tracker["momentum_baseline"] = runs

    # thriller finish
    if (
        target
        and innings_data["innings_id"] == 2
        and overs >= 16.0
        and not tracker["thriller_alerted"]
    ):
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))

        if 0 < runs_needed <= 30:
            alerts.append({
                "type": "thriller",
                "is_mega": False,
                "message": (
                    f"🔴 <b>THRILLER FINISH!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Score: {runs}/{wickets}"
                )
            })
            tracker["thriller_alerted"] = True

    return alerts
