import os
import requests

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"


def get_live_ipl_match():
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()

        if data.get("status") != "success":
            return None

        matches = data.get("data", [])

        for match in matches:
            name = (match.get("name", "") or "").upper()
            series = (match.get("series", "") or "").upper()
            ms = (match.get("ms", "") or "").lower()

            is_ipl = (
                "IPL" in name or
                "IPL" in series or
                "INDIAN PREMIER" in name or
                "INDIAN PREMIER" in series
            )

            if is_ipl and ms in ["live", "in progress", "innings break", "toss"]:
                t1 = match.get("t1", "") or "Team A"
                t2 = match.get("t2", "") or "Team B"

                return {
                    "match_id": str(match.get("id", "")),
                    "team1": t1,
                    "team2": t2,
                    "status": match.get("status", "Live") or "Live",
                    "state": ms
                }

        return None

    except Exception as e:
        print(f"Error: {e}")
        return None


def get_match_scorecard(match_id):
    try:
        url = f"{BASE_URL}/match"
        params = {"apikey": CRICAPI_KEY, "id": match_id}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()
        if data.get("status") != "success":
            return None

        return data.get("data", None)

    except Exception:
        return None


def parse_current_innings(match_data):
    try:
        if not match_data:
            return None

        score_list = match_data.get("score", [])
        if not score_list:
            return None

        current = score_list[-1]

        runs = int(current.get("r", 0) or 0)
        wickets = int(current.get("w", 0) or 0)
        overs = float(current.get("o", 0.0) or 0.0)
        innings_id = len(score_list)

        target = None
        if innings_id >= 2:
            first = score_list[0]
            target = int(first.get("r", 0) or 0) + 1

        return {
            "innings_id": innings_id,
            "runs": runs,
            "wickets": wickets,
            "overs": overs,
            "target": target
        }

    except Exception:
        return None


def debug_ipl_status():
    try:
        url = f"{BASE_URL}/cricScore"
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return f"API Error: {response.status_code}"

        data = response.json()
        if data.get("status") != "success":
            return f"Status: {data.get('status')}"

        matches = data.get("data", [])
        lines = [f"Total: {len(matches)}\n"]

        ipl_count = 0
        for match in matches:
            name = (match.get("name", "") or "")
            series = (match.get("series", "") or "")
            ms = (match.get("ms", "") or "")
            t1 = (match.get("t1", "") or "")
            t2 = (match.get("t2", "") or "")

            if "IPL" in name.upper() or "IPL" in series.upper():
                ipl_count += 1
                lines.append(f"IPL: {t1} vs {t2} | ms={ms}")

        if ipl_count == 0:
            lines.append("No IPL found")
            lines.append("\nSample:")
            for m in matches[:5]:
                lines.append(
                    f"  {m.get('name','-')[:40]} | "
                    f"ms={m.get('ms','-')} | "
                    f"series={m.get('series','-')[:30]}"
                )

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


# Thrill Detection
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

    # Wicket
    if wickets > tr["wicket_count"]:
        new_w = wickets - tr["wicket_count"]
        alerts.append({
            "type": "wicket",
            "is_mega": new_w >= 2,
            "message": (
                f"🚨 <b>WICKET{'S' if new_w > 1 else ''} ALERT!</b>\n\n"
                f"{'😱 DOUBLE STRIKE!' if new_w >= 2 else ''}\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tr["wicket_count"] = wickets

    # Momentum
    runs_diff = runs - tr["momentum_baseline"]
    if runs_diff >= 15:
        alerts.append({
            "type": "momentum",
            "is_mega": False,
            "message": (
                f"⚡ <b>MOMENTUM SHIFT!</b>\n\n"
                f"{runs_diff} runs added rapidly!\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        tr["momentum_baseline"] = runs

    # Thriller
    if (
        target
        and innings_data["innings_id"] == 2
        and overs >= 16.0
        and not tr["thriller_alerted"]
    ):
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))

        if 0 < runs_needed <= 40:
            rrr = (runs_needed * 6) / balls_left
            alerts.append({
                "type": "thriller",
                "is_mega": True,
                "message": (
                    f"🔴 <b>THRILLER FINISH!</b>\n\n"
                    f"Need {runs_needed} off {balls_left} balls!\n"
                    f"Required Rate: {rrr:.1f}\n"
                    f"Score: {runs}/{wickets}\n\n"
                    f"🏏 Match going to the wire!"
                )
            })
            tr["thriller_alerted"] = True

    return alerts
