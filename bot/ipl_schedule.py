from datetime import date, datetime
import pytz

# Timezone fix for Render (Singapore/US servers)
IST = pytz.timezone("Asia/Kolkata")

# IPL 2026 Schedule
IPL_SCHEDULE = [
    # May 12
    (2026, 5, 12, 19, 30, "Punjab Kings", "Delhi Capitals", "HPCA Stadium, Dharamsala"),
    # May 13
    (2026, 5, 13, 19, 30, "Royal Challengers Bengaluru", "Mumbai Indians", "Raipur"),
    # May 14
    (2026, 5, 14, 19, 30, "Punjab Kings", "Chennai Super Kings", "HPCA Stadium, Dharamsala"),
    # May 15
    (2026, 5, 15, 19, 30, "Lucknow Super Giants", "Gujarat Titans", "Lucknow"),
    # May 16
    (2026, 5, 16, 19, 30, "Kolkata Knight Riders", "Royal Challengers Bengaluru", "Kolkata"),
    # May 17
    (2026, 5, 17, 15, 30, "Punjab Kings", "Rajasthan Royals", "Dharamsala"),
    (2026, 5, 17, 19, 30, "Delhi Capitals", "Sunrisers Hyderabad", "Delhi"),
    # May 18
    (2026, 5, 18, 19, 30, "Chennai Super Kings", "Lucknow Super Giants", "Chennai"),
    # May 19
    (2026, 5, 19, 19, 30, "Rajasthan Royals", "Mumbai Indians", "Jaipur"),
    # May 20
    (2026, 5, 20, 19, 30, "Kolkata Knight Riders", "Gujarat Titans", "Kolkata"),
    # May 21
    (2026, 5, 21, 15, 30, "Chennai Super Kings", "Gujarat Titans", "Ahmedabad"),
    (2026, 5, 21, 19, 30, "Sunrisers Hyderabad", "Royal Challengers Bengaluru", "Hyderabad"),
    # May 22
    (2026, 5, 22, 19, 30, "Lucknow Super Giants", "Punjab Kings", "Lucknow"),
    # May 23
    (2026, 5, 23, 19, 30, "Mumbai Indians", "Rajasthan Royals", "Mumbai"),
    # May 24
    (2026, 5, 24, 15, 30, "Kolkata Knight Riders", "Delhi Capitals", "Kolkata"),
    (2026, 5, 24, 19, 30, "Gujarat Titans", "Rajasthan Royals", "Ahmedabad"),
    # PLAYOFFS
    (2026, 5, 26, 19, 30, "Qualifier 1", "Teams TBD", "Dharamsala"),
    (2026, 5, 27, 19, 30, "Eliminator", "Teams TBD", "Chandigarh"),
    (2026, 5, 29, 19, 30, "Qualifier 2", "Teams TBD", "Chandigarh"),
    (2026, 5, 31, 19, 30, "Final", "Teams TBD", "Ahmedabad"),
]

def get_today_matches():
    # Force India Time
    today = datetime.now(IST).date()
    return [m for m in IPL_SCHEDULE if date(m[0], m[1], m[2]) == today]

def get_upcoming_matches(days=3):
    today = datetime.now(IST).date()
    upcoming = []
    for m in IPL_SCHEDULE:
        match_date = date(m[0], m[1], m[2])
        delta = (match_date - today).days
        if 1 <= delta <= days:
            upcoming.append(m)
    return upcoming

def is_match_window_open():
    now = datetime.now(IST)
    hour = now.hour
    # Open from 2:00 PM to 11:59 PM IST
    return 14 <= hour <= 23 and len(get_today_matches()) > 0

def format_time_12h(hh, mm):
    period = "AM" if hh < 12 else "PM"
    hour = hh % 12 if hh % 12 != 0 else 12
    return f"{hour}:{mm:02d} {period}"

def format_schedule_message():
    now = datetime.now(IST)
    today = now.date()
    today_str = today.strftime("%d/%m/%Y (%A)")
    
    lines = [f"📅 *IPL 2026 Schedule*", f"Today: {today_str}", ""]
    
    today_matches = get_today_matches()
    if today_matches:
        lines.append("*Today's Matches:*")
        for m in today_matches:
            time_str = format_time_12h(m[3], m[4])
            lines.append(f"🏏 {m[5]} vs {m[6]}")
            lines.append(f"   ⏰ {time_str} IST | 📍 {m[7]}")
            lines.append("")
    else:
        lines.append("*Today:* No match 😴\n")
    
    upcoming = get_upcoming_matches(3)
    if upcoming:
        lines.append("*Upcoming (Next 3 Days):*")
        prev_date = None
        for m in upcoming:
            match_date = date(m[0], m[1], m[2])
            if match_date != prev_date:
                date_str = match_date.strftime("%d %b (%A)")
                lines.append(f"\n📆 *{date_str}*")
                prev_date = match_date
            time_str = format_time_12h(m[3], m[4])
            lines.append(f"  🏏 {m[5]} vs {m[6]}")
            lines.append(f"     ⏰ {time_str} IST | 📍 {m[7]}")
    
    return "\n".join(lines)
