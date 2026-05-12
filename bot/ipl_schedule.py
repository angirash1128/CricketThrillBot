# ipl_schedule.py
# IPL Schedule Cache System
# Schedule ko API se ek baar fetch karke cache me save karta hai
# User clicks pe 0 API calls

import os
import requests
from datetime import datetime, timedelta

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"

CACHE = {
    "schedule": [],
    "schedule_fetched": False,
    "schedule_last_updated": None,
    "live_match": None,
    "live_scorecard": None,
    "live_innings": None,
    "last_api_call": None,
    "match_started": False,
    "match_ended": False,
    "toss_notified": False,
    "result_notified": False,
    "current_match_id": None
}


def get_cache():
    return CACHE


def update_cache(key, value):
    CACHE[key] = value


def parse_match_name(name):
    """
    'Mumbai Indians vs Chennai Super Kings' ko 2 team names me todta hai
    """
    if not name:
        return "TBD", "TBD"

    if " vs " in name:
        parts = name.split(" vs ")
        team1 = parts[0].strip() if len(parts) > 0 else "TBD"
        team2 = parts[1].strip() if len(parts) > 1 else "TBD"
        return team1, team2

    return name.strip(), "TBD"


def format_time_ist(match_date):
    """
    UTC date string ko IST time me convert karo
    Format: 00:00 AM/PM
    """
    if not match_date:
        return "07:30 PM"

    try:
        if "T" in match_date:
            time_part = match_date.split("T")[1][:5]
            hour = int(time_part.split(":")[0])
            minute = int(time_part.split(":")[1])

            # UTC to IST (+5:30)
            total = hour * 60 + minute + 330
            ist_hour = (total // 60) % 24
            ist_min = total % 60

            if ist_hour >= 12:
                ampm = "PM"
                display_hour = ist_hour - 12 if ist_hour > 12 else 12
            else:
                ampm = "AM"
                display_hour = ist_hour if ist_hour > 0 else 12

            return f"{display_hour:02d}:{ist_min:02d} {ampm}"

    except Exception:
        pass

    return "07:30 PM"


def format_date_ddmmyyyy(match_date):
    """
    YYYY-MM-DD ko DD/MM/YYYY me convert karo
    """
    if not match_date:
        return "TBD"

    try:
        date_only = match_date[:10]
        dt = datetime.strptime(date_only, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return match_date[:10] if match_date else "TBD"


def fetch_schedule():
    """
    IPL schedule fetch karo.
    Yeh function IPL series ko multiple offsets pe dhundta hai
    kyunki first page me IPL zaroori nahi mile.
    """
    if CACHE["schedule_fetched"] and len(CACHE["schedule"]) > 0:
        print("📅 Schedule already cached")
        return CACHE["schedule"]

    if not CRICAPI_KEY:
        print("❌ CRICAPI_KEY missing")
        return []

    try:
        ipl_series_id = None
        ipl_series_name = None

        # Step 1: series list me IPL dhundo (multiple offsets)
        for offset in [0, 25, 50, 75, 100, 125]:
            try:
                url = f"{BASE_URL}/series"
                params = {
                    "apikey": CRICAPI_KEY,
                    "offset": offset
                }
                response = requests.get(url, params=params, timeout=15)

                if response.status_code != 200:
                    print(f"Series API error at offset {offset}: {response.status_code}")
                    continue

                data = response.json()
                if data.get("status") != "success":
                    continue

                series_list = data.get("data", [])

                for series in series_list:
                    name = (series.get("name", "") or "").upper()
                    if "IPL" in name or "INDIAN PREMIER" in name:
                        ipl_series_id = series.get("id", "")
                        ipl_series_name = series.get("name", "")
                        print(f"✅ IPL Series found: {ipl_series_name} | ID: {ipl_series_id}")
                        break

                if ipl_series_id:
                    break

            except Exception as e:
                print(f"Series offset {offset} error: {e}")

        if not ipl_series_id:
            print("❌ IPL series not found in any offset")
            return []

        # Step 2: series_info se schedule lao
        info_url = f"{BASE_URL}/series_info"
        info_params = {
            "apikey": CRICAPI_KEY,
            "id": ipl_series_id
        }

        info_response = requests.get(info_url, params=info_params, timeout=20)

        if info_response.status_code != 200:
            print(f"❌ series_info error: {info_response.status_code}")
            return []

        info_data = info_response.json()

        if info_data.get("status") != "success":
            print(f"❌ series_info status: {info_data.get('status')}")
            return []

        raw_matches = info_data.get("data", {}).get("matchList", [])
        parsed_matches = []

        for match in raw_matches:
            name = (match.get("name", "") or
                    match.get("matchName", "") or
                    match.get("title", "") or "")

            team1, team2 = parse_match_name(name)

            match_date = (
                match.get("date", "") or
                match.get("dateTimeGMT", "") or
                ""
            )

            venue = (
                match.get("venue", "") or
                match.get("ground", "") or
                "TBD"
            )

            match_type = (
                match.get("matchType", "") or
                "T20"
            )

            parsed_matches.append({
                "name": name or f"{team1} vs {team2}",
                "team1": team1,
                "team2": team2,
                "date": match_date,
                "venue": venue,
                "match_type": match_type
            })

        CACHE["schedule"] = parsed_matches
        CACHE["schedule_fetched"] = True
        CACHE["schedule_last_updated"] = datetime.now().strftime("%d/%m/%Y %I:%M %p")

        print(f"✅ Schedule cached: {len(parsed_matches)} matches")
        return parsed_matches

    except Exception as e:
        print(f"❌ fetch_schedule error: {e}")
        return []


def get_schedule():
    return CACHE["schedule"]


def get_todays_matches():
    today = datetime.now().strftime("%Y-%m-%d")
    matches = []

    for match in CACHE["schedule"]:
        match_date = match.get("date", "") or ""
        if today in match_date:
            matches.append(match)

    return matches


def get_upcoming_matches(days=3):
    upcoming = []
    now = datetime.now()

    for i in range(1, days + 1):
        target = (now + timedelta(days=i)).strftime("%Y-%m-%d")

        for match in CACHE["schedule"]:
            match_date = match.get("date", "") or ""
            if target in match_date:
                upcoming.append(match)

    return upcoming


def is_match_time_now():
    """
    Match start se 30 min pehle se 4.5 hours baad tak True
    """
    now = datetime.now()
    current_mins = now.hour * 60 + now.minute
    today_matches = get_todays_matches()

    for match in today_matches:
        match_date = match.get("date", "") or ""
        if not match_date:
            continue

        try:
            # UTC time extract
            time_part = match_date.split("T")[1][:5]
            hour = int(time_part.split(":")[0])
            minute = int(time_part.split(":")[1])

            # Convert UTC to IST
            total = hour * 60 + minute + 330
            ist_hour = (total // 60) % 24
            ist_min = total % 60
            match_start_mins = ist_hour * 60 + ist_min

            window_start = match_start_mins - 30
            window_end = match_start_mins + 270  # 4.5 hours

            if window_start <= current_mins <= window_end:
                return True

        except Exception:
            continue

    return False


def format_schedule_message():
    """
    Professional Today's Schedule message
    Date format: DD/MM/YYYY
    Time format: 00:00 AM/PM
    """
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    day_name = now.strftime("%A")

    lines = []
    lines.append(f"📅 <b>{date_str} ({day_name})</b>")
    lines.append("🏆 <b>Indian Premier League 2026</b>\n")

    today_matches = get_todays_matches()

    if today_matches:
        lines.append("<b>Today's Matches:</b>\n")
        for idx, match in enumerate(today_matches, start=1):
            lines.append(f"🏏 <b>Match {idx}</b>")
            lines.append(
                f"   <b>{match.get('team1', 'TBD')}</b> vs <b>{match.get('team2', 'TBD')}</b>"
            )
            lines.append(f"   ⏰ {format_time_ist(match.get('date', ''))} IST")
            lines.append(f"   📍 {match.get('venue', 'TBD')}")
            lines.append("")
    else:
        lines.append("😴 No IPL match today\n")

    upcoming = get_upcoming_matches(days=3)
    if upcoming:
        lines.append("🗓 <b>Upcoming Matches:</b>\n")
        for match in upcoming[:4]:
            date_display = format_date_ddmmyyyy(match.get("date", ""))
            lines.append(f"• {date_display}")
            lines.append(
                f"  <b>{match.get('team1', 'TBD')}</b> vs <b>{match.get('team2', 'TBD')}</b>"
            )
            lines.append(f"  ⏰ {format_time_ist(match.get('date', ''))} IST\n")

    if CACHE["schedule_last_updated"]:
        lines.append(f"📡 Last updated: {CACHE['schedule_last_updated']}")

    return "\n".join(lines)
