import os
import requests
from datetime import datetime

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
            print(f"API Error: {response.status_code}")
            return None

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
                            print(f"✅ IPL Match: {info.get('matchId')}")
                            return {
                                "match_id": str(info.get("matchId", "")),
                                "team1": info.get("team1", {}).get("teamName", "Team A"),
                                "team2": info.get("team2", {}).get("teamName", "Team B"),
                                "status": info.get("status", "Live")
                            }
        print("No live IPL match found")
        return None

    except Exception as e:
        print(f"Match error: {e}")
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
        bat = curr.get("batTeamDetails", {}).get("batTeamScoreDetails", {})
        return {
            "innings_id": curr.get("inningsId", 1),
            "runs": bat.get("runs", 0),
            "wickets": bat.get("wickets", 0),
            "overs": float(bat.get("overs", 0.0)),
            "target": data.get("matchHeader", {}).get("target", None)
        }
    except Exception:
        return None

# Thrill tracker
match_trackers = {}

def detect_thrills(match_id, innings_data):
    alerts = []
    if not innings_data:
        return alerts

    runs = innings_data["runs"]
    wickets = innings_data["wickets"]
    overs = innings_data["overs"]
    innings_id = innings_data["innings_id"]
    target = innings_data["target"]

    if match_id not in match_trackers:
        match_trackers[match_id] = {
            "innings_id": innings_id,
            "wicket_count": wickets,
            "momentum_baseline": runs,
            "thriller_alerted": False,
            "collapse_alerted": False
        }
        return alerts

    tr = match_trackers[match_id]

    # Innings change
    if tr["innings_id"] != innings_id:
        match_trackers[match_id] = {
            "innings_id": innings_id,
            "wicket_count": wickets,
            "momentum_baseline": runs,
            "thriller_alerted": False,
            "collapse_alerted": False
        }
        return alerts

    # WICKET ALERT
    if wickets > tr["wicket_count"]:
        new_w = wickets - tr["wicket_count"]
        for i in range(new_w):
            alerts.append({
                "type": "wicket",
                "is_mega": False,
                "message": (
                    f"🚨 <b>WICKET ALERT!</b>\n\n"
                    f"Wicket #{tr['wicket_count'] + i + 1} down!\n"
                    f"Score: {runs}/{wickets}\n"
                    f"Overs: {overs}"
                )
            })
        tr["wicket_count"] = wickets

    # COLLAPSE ALERT (3+ wickets in quick succession)
    if wickets >= 3 and not tr.get("collapse_alerted"):
        if (runs - tr["momentum_baseline"]) < 20:
            alerts.append({
                "type": "collapse",
                "is_mega": False,
                "message": (
                    f"😱 <b>BATTING COLLAPSE!</b>\n\n"
                    f"Multiple wickets falling fast!\n"
                    f"Score: {runs}/{wickets}\n"
                    f"Overs: {overs}\n\n"
                    f"This match is turning! 🔥"
                )
            })
            tr["collapse_alerted"] = True

    # MOMENTUM SHIFT
    runs_diff = runs - tr["momentum_baseline"]
    if runs_diff >= 12:
        alerts.append({
            "type": "momentum",
            "is_mega": False,
            "message": (
                f"⚡ <b>MOMENTUM SHIFT!</b>\n\n"
                f"{runs_diff} runs scored rapidly!\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tr["momentum_baseline"] = runs

    # THRILLER FINISH (2nd innings, last 4 overs, close chase)
    if (
        innings_id == 2
        and target
        and overs >= 16.0
        and not tr.get("thriller_alerted")
    ):
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))
        rrr = (runs_needed * 6) / balls_left

        if 0 < runs_needed <= 30 or rrr > 12:
            alerts.append({
                "type": "thriller",
                "is_mega": False,
                "message": (
                    f"🔴 <b>THRILLER FINISH!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Required Rate: {rrr:.1f}\n"
                    f"Score: {runs}/{wickets}\n\n"
                    f"🏏 This one is going to the wire!"
                )
            })
            tr["thriller_alerted"] = True

    return alerts
