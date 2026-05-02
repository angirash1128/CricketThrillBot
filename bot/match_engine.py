import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")


def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }


def extract_first_ipl_match(data, include_complete=False):
    if not data:
        return None
    try:
        for match_type in data.get("typeMatches", []):
            for series in match_type.get("seriesMatches", []):
                wrapper = series.get("seriesAdWrapper")
                if not wrapper:
                    continue
                series_name = wrapper.get("seriesName", "")
                if "IPL" in series_name.upper() or "INDIAN PREMIER" in series_name.upper():
                    for match in wrapper.get("matches", []):
                        info = match.get("matchInfo", {})
                        state = info.get("state", "").lower()
                        if not include_complete and state == "complete":
                            continue
                        return {
                            "match_id": str(info.get("matchId", "")),
                            "team1": info.get("team1", {}).get("teamName", "Team A"),
                            "team2": info.get("team2", {}).get("teamName", "Team B"),
                            "status": info.get("status", "Live"),
                            "state": state,
                            "series_name": series_name
                        }
        return None
    except Exception:
        return None


def get_live_ipl_match():
    # Sahi URLs with /v1/
    endpoints = [
        f"https://{RAPIDAPI_HOST}/matches/v1/live",
        f"https://{RAPIDAPI_HOST}/matches/v1/upcoming",
        f"https://{RAPIDAPI_HOST}/matches/v1/recent",
    ]

    for url in endpoints:
        try:
            response = requests.get(url, headers=get_headers(), timeout=15)
            print(f"{url} → {response.status_code}")

            if response.status_code != 200:
                continue

            data = response.json()
            match = extract_first_ipl_match(data, include_complete=False)

            if match:
                print(f"✅ Found: {match['team1']} vs {match['team2']} | {match['state']}")
                return match

        except Exception as e:
            print(f"Error {url}: {e}")
            continue

    print("No IPL match found in any endpoint")
    return None


def debug_ipl_status():
    lines = []
    endpoints = [
        f"https://{RAPIDAPI_HOST}/matches/v1/live",
        f"https://{RAPIDAPI_HOST}/matches/v1/upcoming",
        f"https://{RAPIDAPI_HOST}/matches/v1/recent",
    ]

    for url in endpoints:
        short = url.split("/v1/")[-1]
        try:
            response = requests.get(url, headers=get_headers(), timeout=15)

            if response.status_code != 200:
                lines.append(f"{short} → {response.status_code} | {response.text[:150]}")
                continue

            data = response.json()
            match = extract_first_ipl_match(data, include_complete=True)

            if match:
                lines.append(
                    f"{short} → {match['team1']} vs {match['team2']} "
                    f"| state={match['state']} | {match['status']}"
                )
            else:
                lines.append(f"{short} → IPL not found in response")

        except Exception as e:
            lines.append(f"{short} → exception: {e}")

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
        bat_score = current.get(
            "batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": current.get("inningsId", 1),
            "runs": bat_score.get("runs", 0),
            "wickets": bat_score.get("wickets", 0),
            "overs": float(bat_score.get("overs", 0.0)),
            "target": scorecard_data.get(
                "matchHeader", {}).get("target", None)
        }
    except Exception:
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

    tr = match_trackers[match_id]

    if tr["innings_id"] != innings_data["innings_id"]:
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

    if wickets > tr["wicket_count"]:
        alerts.append({
            "type": "wicket",
            "is_mega": False,
            "message": (
                f"🚨 <b>WICKET ALERT!</b>\n\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tr["wicket_count"] = wickets

    if (runs - tr["momentum_baseline"]) >= 12:
        alerts.append({
            "type": "momentum",
            "is_mega": False,
            "message": (
                f"⚡ <b>MOMENTUM SHIFT!</b>\n\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tr["momentum_baseline"] = runs

    if (
        target
        and innings_data["innings_id"] == 2
        and overs >= 16.0
        and not tr["thriller_alerted"]
    ):
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))
        if 0 < runs_needed <= 36:
            alerts.append({
                "type": "thriller",
                "is_mega": False,
                "message": (
                    f"🔴 <b>THRILLER FINISH!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Score: {runs}/{wickets}"
                )
            })
            tr["thriller_alerted"] = True

    return alerts
