# ipl_schedule.py
# IPL Schedule + Cache System
# API se schedule ek baar fetch karo, save karo
# Users ke clicks pe 0 API calls

import os
import requests
from datetime import datetime, timedelta

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"

# ─────────────────────────────────────────
# CACHED DATA (Memory mein save rahega)
# ─────────────────────────────────────────

CACHE = {
    # Schedule data
    "schedule": [],
    "schedule_fetched": False,

    # Live match data (polling se update hoga)
    "live_match": None,
    "live_scorecard": None,
    "live_innings": None,
    "last_api_call": None,

    # Match state
    "match_started": False,
    "match_ended": False,
    "toss_notified": False,
    "result_notified": False,
    "current_match_id": None
}


def get_cache():
    """Cache return karo"""
    return CACHE


def update_cache(key, value):
    """Cache update karo"""
    CACHE[key] = value


# ─────────────────────────────────────────
# SCHEDULE FETCH (1 API call - ek baar)
# ─────────────────────────────────────────

def fetch_schedule():
    """
    IPL schedule fetch karo - SIRF 1 API call
    Ek baar fetch karke cache mein save
    Dubara call nahi hogi jab tak restart na ho
    """
    if CACHE["schedule_fetched"] and len(CACHE["schedule"]) > 0:
        print("Schedule already cached - 0 API calls")
        return CACHE["schedule"]

    try:
        url = f"{BASE_URL}/series_info"
        # IPL 2026 series ID - ye fix hai
        # Agar ye ID galat ho to API se dhundenge
        params = {"apikey": CRICAPI_KEY, "offset": 0}

        # Pehle series list se IPL dhundo
        series_url = f"{BASE_URL}/series"
        response = requests.get(series_url, params=params, timeout=15)

        if response.status_code != 200:
            print(f"Series API error: {response.status_code}")
            return []

        data = response.json()
        if data.get("status") != "success":
            print(f"Series API status: {data.get('status')}")
            print(f"Info: {data.get('info', {})}")
            return []

        # IPL series dhundo
        series_list = data.get("data", [])
        ipl_id = None

        for series in series_list:
            name = (series.get("name", "") or "").upper()
            if "IPL" in name or "INDIAN PREMIER" in name:
                ipl_id = series.get("id", "")
                print(f"IPL found: {series.get('name')} | ID: {ipl_id}")
                break

        if not ipl_id:
            print("IPL series not found")
            return []

        # IPL ka schedule fetch karo
        info_url = f"{BASE_URL}/series_info"
        info_params = {"apikey": CRICAPI_KEY, "id": ipl_id}
        info_response = requests.get(info_url, params=info_params, timeout=15)

        if info_response.status_code != 200:
            print(f"Series info error: {info_response.status_code}")
            return []

        info_data = info_response.json()
        if info_data.get("status") != "success":
            return []

        match_list = info_data.get("data", {}).get("matchList", [])

        CACHE["schedule"] = match_list
        CACHE["schedule_fetched"] = True

        print(f"Schedule cached: {len(match_list)} matches")
        return match_list

    except Exception as e:
        print(f"Schedule fetch error: {e}")
        return []


# ─────────────────────────────────────────
# SCHEDULE HELPERS (0 API calls)
# ─────────────────────────────────────────

def get_todays_matches():
    """Aaj ke matches - 0 API calls (cache se)"""
    schedule = CACHE["schedule"]
    if not schedule:
        return []

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    today_matches = []

    for match in schedule:
        match_date = (match.get("date", "") or
                      match.get("dateTimeGMT", "") or "")
        if today_str in match_date:
            today_matches.append(match)

    return today_matches


def get_upcoming_matches(days=3):
    """Agle kuch dino ke matches - 0 API calls"""
    schedule = CACHE["schedule"]
    if not schedule:
        return []

    now = datetime.now()
    upcoming = []

    for i in range(1, days + 1):
        future = now + timedelta(days=i)
        future_str = future.strftime("%Y-%m-%d")

        for match in schedule:
            match_date = (match.get("date", "") or
                          match.get("dateTimeGMT", "") or "")
            if future_str in match_date:
                upcoming.append(match)

    return upcoming


def is_match_time_now():
    """Kya abhi match ka time hai? - 0 API calls"""
    now = datetime.now()
    current_mins = now.hour * 60 + now.minute

    today_matches = get_todays_matches()

    if not today_matches:
        return False

    for match in today_matches:
        match_date = (match.get("date", "") or
                      match.get("dateTimeGMT", "") or "")

        # Time parse karo
        match_start_mins = 19 * 60 + 30  # Default 7:30 PM IST

        if "T" in match_date:
            try:
                time_part = match_date.split("T")[1][:5]
                hour = int(time_part.split(":")[0])
                minute = int(time_part.split(":")[1])

                # UTC to IST (+5:30)
                ist_total = (hour * 60 + minute) + 330
                match_start_mins = ist_total % (24 * 60)
            except Exception:
                pass

        # Match window: 30 min before to 4.5 hours after
        window_start = match_start_mins - 30
        window_end = match_start_mins + 270

        if window_start <= current_mins <= window_end:
            return True

    return False


def parse_match_time(match_date_str):
    """Match date string se IST time nikalo"""
    if not match_date_str:
        return "07:30 PM"

    try:
        if "T" in match_date_str:
            time_part = match_date_str.split("T")[1][:5]
            hour = int(time_part.split(":")[0])
            minute = int(time_part.split(":")[1])

            # UTC to IST
            ist_total = (hour * 60 + minute) + 330
            ist_hour = (ist_total // 60) % 24
            ist_min = ist_total % 60

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


def format_schedule_message():
    """
    Schedule ka formatted message
    Date: DD/MM/YYYY
    Time: HH:MM AM/PM
    0 API calls - cache se
    """
    now = datetime.now()
    today_str = now.strftime("%d/%m/%Y")
    day_name = now.strftime("%A")

    today_matches = get_todays_matches()
    upcoming = get_upcoming_matches(days=3)

    lines = []

    # Header
    lines.append(f"📅 <b>{today_str} ({day_name})</b>")
    lines.append(f"🏆 <b>Indian Premier League 2026</b>\n")

    # Today
    if today_matches:
        for i, match in enumerate(today_matches, 1):
            # Match name
            name = (match.get("name", "") or
                    match.get("matchName", "") or "")

            # Teams parse
            teams = name.split(" vs ") if " vs " in name else [name, ""]
            t1 = teams[0].strip() if len(teams) > 0 else "TBD"
            t2 = teams[1].strip() if len(teams) > 1 else "TBD"

            # Venue
            venue = (match.get("venue", "") or
                     match.get("ground", "") or "TBD")

            # Time
            match_date = (match.get("date", "") or
                          match.get("dateTimeGMT", "") or "")
            time_str = parse_match_time(match_date)

            # Match desc
            match_desc = match.get("matchType", "T20") or "T20"

            lines.append(f"🏏 <b>Match {i}</b> ({match_desc})")
            lines.append(f"   <b>{t1}</b> vs <b>{t2}</b>")
            lines.append(f"   ⏰ {time_str} IST")
            lines.append(f"   📍 {venue}")
            lines.append("")
    else:
        lines.append("😴 No IPL match today\n")

    # Upcoming
    if upcoming:
        lines.append("🗓 <b>Upcoming Matches:</b>\n")
        for match in upcoming[:4]:
            name = (match.get("name", "") or
                    match.get("matchName", "") or "TBD vs TBD")
            match_date = (match.get("date", "") or
                          match.get("dateTimeGMT", "") or "")

            if match_date:
                try:
                    dt = datetime.strptime(
                        match_date[:10], "%Y-%m-%d")
                    date_display = dt.strftime("%d/%m/%Y (%A)")
                except Exception:
                    date_display = match_date[:10]
            else:
                date_display = "TBD"

            time_str = parse_match_time(match_date)
            lines.append(f"• {date_display}")
            lines.append(f"  {name}")
            lines.append(f"  ⏰ {time_str} IST\n")

    # Cache info
    if CACHE["last_api_call"]:
        lines.append(
            f"\n📡 Last updated: {CACHE['last_api_call']}")

    return "\n".join(lines)
