import os
import json
import requests
from datetime import datetime, timedelta

CRICAPI_KEY = os.environ.get("CRICAPI_KEY")
BASE_URL = "https://api.cricapi.com/v1"

# Memory mein schedule save hoga
CACHED_SCHEDULE = {
    "matches": [],
    "last_fetched": None
}


def fetch_ipl_schedule_from_api():
    """
    API se IPL schedule fetch karo - sirf 1 call
    Aur memory mein save karo
    """
    try:
        url = f"{BASE_URL}/series"
        params = {"apikey": CRICAPI_KEY, "offset": 0}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            print(f"Schedule API error: {response.status_code}")
            return False

        data = response.json()
        if data.get("status") != "success":
            return False

        # IPL series dhundo
        series_list = data.get("data", [])
        ipl_id = None

        for series in series_list:
            name = (series.get("name", "") or "").upper()
            if "IPL" in name or "INDIAN PREMIER" in name:
                ipl_id = series.get("id", "")
                print(f"IPL Series found: {series.get('name')} | ID: {ipl_id}")
                break

        if not ipl_id:
            print("IPL series not found in API")
            return False

        # IPL matches fetch karo
        url2 = f"{BASE_URL}/series_info"
        params2 = {"apikey": CRICAPI_KEY, "id": ipl_id}
        response2 = requests.get(url2, params2, timeout=15)

        if response2.status_code != 200:
            return False

        data2 = response2.json()
        if data2.get("status") != "success":
            return False

        match_list = data2.get("data", {}).get("matchList", [])

        CACHED_SCHEDULE["matches"] = match_list
        CACHED_SCHEDULE["last_fetched"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        print(f"Schedule cached: {len(match_list)} matches")
        return True

    except Exception as e:
        print(f"Schedule fetch error: {e}")
        return False


def get_schedule():
    """
    Schedule return karo
    Agar cache empty hai to fetch karo (1 API call)
    Agar cache hai to wahi use karo (0 API calls)
    """
    if not CACHED_SCHEDULE["matches"]:
        fetch_ipl_schedule_from_api()
    return CACHED_SCHEDULE["matches"]


def get_todays_matches():
    """Aaj ke IPL matches return karo"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    matches = get_schedule()
    today_matches = []

    for match in matches:
        match_date = match.get("date", "") or ""
        match_date_only = match_date[:10] if match_date else ""

        if match_date_only == today_str:
            today_matches.append(match)

    return today_matches


def get_upcoming_matches(days=3):
    """Agle kuch dino ke matches"""
    now = datetime.now()
    upcoming = []

    for i in range(1, days + 1):
        future = now + timedelta(days=i)
        future_str = future.strftime("%Y-%m-%d")

        matches = get_schedule()
        for match in matches:
            match_date = match.get("date", "") or ""
            match_date_only = match_date[:10] if match_date else ""

            if match_date_only == future_str:
                upcoming.append(match)

    return upcoming


def is_match_time_now():
    """Kya abhi match ka time hai?"""
    now = datetime.now()
    current_mins = now.hour * 60 + now.minute

    today_matches = get_todays_matches()

    for match in today_matches:
        # IPL matches usually 3:30 PM or 7:30 PM
        match_date = match.get("date", "") or ""

        # Default times based on IPL pattern
        if "T" in match_date:
            try:
                time_part = match_date.split("T")[1][:5]
                hour = int(time_part.split(":")[0])
                minute = int(time_part.split(":")[1])

                # Convert UTC to IST (+5:30)
                ist_mins = (hour * 60 + minute) + 330
                ist_hour = ist_mins // 60
                ist_min = ist_mins % 60

                match_start_mins = ist_hour * 60 + ist_min
            except Exception:
                match_start_mins = 19 * 60 + 30  # Default 7:30 PM
        else:
            match_start_mins = 19 * 60 + 30  # Default 7:30 PM

        # Window: 15 min before to 4 hours after
        window_start = match_start_mins - 15
        window_end = match_start_mins + 240

        if window_start <= current_mins <= window_end:
            return True

    return False


def format_schedule_message():
    """
    Schedule ka formatted message banao
    Date: DD/MM/YYYY
    Time: HH:MM AM/PM
    """
    now = datetime.now()
    today_str = now.strftime("%d/%m/%Y")
    day_name = now.strftime("%A")

    today_matches = get_todays_matches()
    upcoming = get_upcoming_matches(days=3)

    lines = []

    # Today's matches
    lines.append(f"📅 <b>{today_str} ({day_name})</b>")
    lines.append(f"🏆 Indian Premier League 2026\n")

    if today_matches:
        for i, match in enumerate(today_matches, 1):
            name = match.get("name", "") or "TBD vs TBD"
            venue = match.get("venue", "") or "TBD"
            match_date = match.get("date", "") or ""
            match_type = match.get("matchType", "") or "T20"

            # Time extract
            time_str = "07:30 PM"
            if "T" in match_date:
                try:
                    time_part = match_date.split("T")[1][:5]
                    hour = int(time_part.split(":")[0])
                    minute = int(time_part.split(":")[1])
                    ist_mins = (hour * 60 + minute) + 330
                    ist_hour = ist_mins // 60
                    ist_min = ist_mins % 60

                    if ist_hour >= 12:
                        ampm = "PM"
                        display_hour = ist_hour - 12 if ist_hour > 12 else 12
                    else:
                        ampm = "AM"
                        display_hour = ist_hour if ist_hour > 0 else 12

                    time_str = f"{display_hour:02d}:{ist_min:02d} {ampm}"
                except Exception:
                    time_str = "07:30 PM"

            lines.append(f"🏏 <b>Match {i}</b>")
            lines.append(f"   {name}")
            lines.append(f"   ⏰ {time_str} IST")
            lines.append(f"   📍 {venue}")
            lines.append("")
    else:
        lines.append("No IPL match today 😴\n")

    # Upcoming matches
    if upcoming:
        lines.append("🗓 <b>Upcoming Matches:</b>\n")
        for match in upcoming[:4]:
            name = match.get("name", "") or "TBD vs TBD"
            match_date = match.get("date", "") or ""

            if match_date:
                try:
                    dt = datetime.strptime(match_date[:10], "%Y-%m-%d")
                    date_display = dt.strftime("%d/%m/%Y (%A)")
                except Exception:
                    date_display = match_date[:10]
            else:
                date_display = "TBD"

            lines.append(f"• {date_display}")
            lines.append(f"  {name}\n")

    return "\n".join(lines)
