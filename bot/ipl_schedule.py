# ipl_schedule.py
# IPL 2026 Schedule - Hardcoded
# 0 API calls for schedule
# User clicks pe instant response

from datetime import datetime, timedelta

# ─────────────────────────────────────────
# IPL 2026 COMPLETE SCHEDULE
# Format: (YYYY, MM, DD, HH, MM_min, "Team1", "Team2", "Venue")
# Time: IST
# ─────────────────────────────────────────

IPL_MATCHES = [
    # --- Already Played (April) ---
    (2026, 4, 22, 19, 30, "Kolkata Knight Riders", "Royal Challengers Bengaluru", "Eden Gardens, Kolkata"),
    (2026, 4, 23, 19, 30, "Sunrisers Hyderabad", "Rajasthan Royals", "Rajiv Gandhi Stadium, Hyderabad"),
    (2026, 4, 24, 19, 30, "Chennai Super Kings", "Mumbai Indians", "MA Chidambaram Stadium, Chennai"),
    (2026, 4, 25, 19, 30, "Delhi Capitals", "Lucknow Super Giants", "Arun Jaitley Stadium, Delhi"),
    (2026, 4, 26, 15, 30, "Punjab Kings", "Gujarat Titans", "Mullanpur Stadium, Punjab"),
    (2026, 4, 26, 19, 30, "Rajasthan Royals", "Kolkata Knight Riders", "Sawai Mansingh Stadium, Jaipur"),
    (2026, 4, 27, 15, 30, "Mumbai Indians", "Sunrisers Hyderabad", "Wankhede Stadium, Mumbai"),
    (2026, 4, 27, 19, 30, "Royal Challengers Bengaluru", "Delhi Capitals", "M Chinnaswamy Stadium, Bengaluru"),
    (2026, 4, 28, 19, 30, "Lucknow Super Giants", "Chennai Super Kings", "Ekana Stadium, Lucknow"),
    (2026, 4, 29, 19, 30, "Gujarat Titans", "Punjab Kings", "Narendra Modi Stadium, Ahmedabad"),
    (2026, 4, 30, 19, 30, "Kolkata Knight Riders", "Delhi Capitals", "Eden Gardens, Kolkata"),

    # --- May ---
    (2026, 5, 1, 19, 30, "Mumbai Indians", "Rajasthan Royals", "Wankhede Stadium, Mumbai"),
    (2026, 5, 2, 19, 30, "Rajasthan Royals", "Delhi Capitals", "Sawai Mansingh Stadium, Jaipur"),
    (2026, 5, 3, 15, 30, "Lucknow Super Giants", "Punjab Kings", "Ekana Stadium, Lucknow"),
    (2026, 5, 3, 19, 30, "Kolkata Knight Riders", "Mumbai Indians", "Eden Gardens, Kolkata"),
    (2026, 5, 4, 19, 30, "Sunrisers Hyderabad", "Chennai Super Kings", "Rajiv Gandhi Stadium, Hyderabad"),
    (2026, 5, 5, 19, 30, "Royal Challengers Bengaluru", "Gujarat Titans", "M Chinnaswamy Stadium, Bengaluru"),
    (2026, 5, 6, 19, 30, "Delhi Capitals", "Lucknow Super Giants", "Arun Jaitley Stadium, Delhi"),
    (2026, 5, 7, 19, 30, "Mumbai Indians", "Rajasthan Royals", "Wankhede Stadium, Mumbai"),
    (2026, 5, 8, 19, 30, "Punjab Kings", "Kolkata Knight Riders", "Mullanpur Stadium, Punjab"),
    (2026, 5, 9, 19, 30, "Chennai Super Kings", "Sunrisers Hyderabad", "MA Chidambaram Stadium, Chennai"),
    (2026, 5, 10, 15, 30, "Gujarat Titans", "Royal Challengers Bengaluru", "Narendra Modi Stadium, Ahmedabad"),
    (2026, 5, 10, 19, 30, "Lucknow Super Giants", "Delhi Capitals", "Ekana Stadium, Lucknow"),
    (2026, 5, 11, 15, 30, "Rajasthan Royals", "Punjab Kings", "Sawai Mansingh Stadium, Jaipur"),
    (2026, 5, 11, 19, 30, "Mumbai Indians", "Chennai Super Kings", "Wankhede Stadium, Mumbai"),
    (2026, 5, 12, 19, 30, "Kolkata Knight Riders", "Gujarat Titans", "Eden Gardens, Kolkata"),
    (2026, 5, 13, 19, 30, "Sunrisers Hyderabad", "Royal Challengers Bengaluru", "Rajiv Gandhi Stadium, Hyderabad"),
    (2026, 5, 14, 19, 30, "Delhi Capitals", "Mumbai Indians", "Arun Jaitley Stadium, Delhi"),
    (2026, 5, 15, 19, 30, "Lucknow Super Giants", "Rajasthan Royals", "Ekana Stadium, Lucknow"),
    (2026, 5, 16, 15, 30, "Punjab Kings", "Sunrisers Hyderabad", "Mullanpur Stadium, Punjab"),
    (2026, 5, 16, 19, 30, "Chennai Super Kings", "Kolkata Knight Riders", "MA Chidambaram Stadium, Chennai"),
    (2026, 5, 17, 15, 30, "Gujarat Titans", "Delhi Capitals", "Narendra Modi Stadium, Ahmedabad"),
    (2026, 5, 17, 19, 30, "Royal Challengers Bengaluru", "Mumbai Indians", "M Chinnaswamy Stadium, Bengaluru"),
    (2026, 5, 18, 19, 30, "Rajasthan Royals", "Lucknow Super Giants", "Sawai Mansingh Stadium, Jaipur"),
    (2026, 5, 19, 19, 30, "Kolkata Knight Riders", "Punjab Kings", "Eden Gardens, Kolkata"),
    (2026, 5, 20, 19, 30, "Sunrisers Hyderabad", "Gujarat Titans", "Rajiv Gandhi Stadium, Hyderabad"),

    # --- Playoffs (Approximate dates) ---
    (2026, 5, 22, 19, 30, "Qualifier 1", "TBD", "TBD"),
    (2026, 5, 23, 19, 30, "Eliminator", "TBD", "TBD"),
    (2026, 5, 25, 19, 30, "Qualifier 2", "TBD", "TBD"),
    (2026, 5, 27, 19, 30, "FINAL", "TBD", "TBD"),
]


# ─────────────────────────────────────────
# CACHE (Memory mein live data save hoga)
# ─────────────────────────────────────────

CACHE = {
    "live_match": None,
    "live_scorecard": None,
    "live_innings": None,
    "last_updated": None,
    "toss_notified": False,
    "result_notified": False,
    "current_match_id": None,
}


def get_cache():
    return CACHE


def update_cache(key, value):
    CACHE[key] = value


# ─────────────────────────────────────────
# SCHEDULE HELPERS (0 API calls)
# ─────────────────────────────────────────

def get_todays_matches():
    """Aaj ke matches - schedule se (0 API calls)"""
    now = datetime.now()
    today = []

    for match in IPL_MATCHES:
        y, mo, d, h, mi, t1, t2, venue = match
        if y == now.year and mo == now.month and d == now.day:
            today.append({
                "year": y, "month": mo, "day": d,
                "hour": h, "minute": mi,
                "team1": t1, "team2": t2,
                "venue": venue
            })

    return today


def get_upcoming_matches(days=3):
    """Agle kuch dino ke matches"""
    now = datetime.now()
    upcoming = []

    for i in range(1, days + 1):
        future = now + timedelta(days=i)
        for match in IPL_MATCHES:
            y, mo, d, h, mi, t1, t2, venue = match
            if (y == future.year and
                    mo == future.month and
                    d == future.day):
                upcoming.append({
                    "year": y, "month": mo, "day": d,
                    "hour": h, "minute": mi,
                    "team1": t1, "team2": t2,
                    "venue": venue
                })

    return upcoming


def is_match_time_now():
    """
    Match start se 20 min pehle se
    Match end tak (4 hours after)
    True return karo
    """
    now = datetime.now()
    current_mins = now.hour * 60 + now.minute
    today = get_todays_matches()

    for match in today:
        start = match["hour"] * 60 + match["minute"]
        # Window: 20 min before to 4.5 hours after
        if (start - 20) <= current_mins <= (start + 270):
            return True

    return False


def format_time(hour, minute):
    """HH:MM AM/PM format"""
    if hour >= 12:
        ampm = "PM"
        h = hour - 12 if hour > 12 else 12
    else:
        ampm = "AM"
        h = hour if hour > 0 else 12
    return f"{h:02d}:{minute:02d} {ampm}"


def format_schedule_message():
    """
    Schedule message banao
    Date: DD/MM/YYYY
    Time: HH:MM AM/PM
    0 API calls
    """
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    day_name = now.strftime("%A")

    lines = []
    lines.append(f"📅 <b>{date_str} ({day_name})</b>")
    lines.append("🏆 <b>Indian Premier League 2026</b>\n")

    today = get_todays_matches()

    if today:
        lines.append("<b>Today's Matches:</b>\n")
        for i, m in enumerate(today, 1):
            time_str = format_time(m["hour"], m["minute"])
            lines.append(f"🏏 <b>Match {i}</b>")
            lines.append(
                f"   <b>{m['team1']}</b> vs <b>{m['team2']}</b>")
            lines.append(f"   ⏰ {time_str} IST")
            lines.append(f"   📍 {m['venue']}")
            lines.append("")
    else:
        lines.append("😴 <b>No IPL match today</b>\n")

    upcoming = get_upcoming_matches(days=3)
    if upcoming:
        lines.append("🗓 <b>Upcoming Matches:</b>\n")
        seen_days = []
        for m in upcoming[:5]:
            day_key = f"{m['day']}/{m['month']}"
            date_display = f"{m['day']:02d}/{m['month']:02d}/{m['year']}"
            time_str = format_time(m["hour"], m["minute"])

            lines.append(f"• <b>{date_display}</b>")
            lines.append(
                f"  {m['team1']} vs {m['team2']}")
            lines.append(f"  ⏰ {time_str} IST\n")

    return "\n".join(lines)
