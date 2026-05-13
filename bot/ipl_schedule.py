from datetime import date, datetime
import pytz

# Timezone fix for Singapore/Render servers
IST = pytz.timezone("Asia/Kolkata")

# IPL 2026 Schedule (Verified & Fixed)
# Format: (YYYY, MM, DD, HH_24, MM, "Team1", "Team2", "Venue")
IPL_SCHEDULE = [
    (2026, 5, 12, 19, 30, "PBKS", "DC", "Dharamsala"),
    (2026, 5, 13, 19, 30, "RCB", "MI", "Raipur"),
    (2026, 5, 14, 19, 30, "PBKS", "CSK", "Dharamsala"),
    (2026, 5, 15, 19, 30, "LSG", "GT", "Lucknow"),
    (2026, 5, 16, 19, 30, "KKR", "RCB", "Kolkata"),
    # Double Header 17 May
    (2026, 5, 17, 15, 30, "PBKS", "RR", "Dharamsala"),
    (2026, 5, 17, 19, 30, "DC", "SRH", "Delhi"),
    
    (2026, 5, 18, 19, 30, "CSK", "LSG", "Chennai"),
    (2026, 5, 19, 19, 30, "RR", "MI", "Jaipur"),
    (2026, 5, 20, 19, 30, "KKR", "GT", "Kolkata"),
    
    # Double Header 21 May
    (2026, 5, 21, 15, 30, "CSK", "GT", "Ahmedabad"),
    (2026, 5, 21, 19, 30, "SRH", "RCB", "Hyderabad"),
    
    (2026, 5, 22, 19, 30, "LSG", "PBKS", "Lucknow"),
    (2026, 5, 23, 19, 30, "MI", "RR", "Mumbai"),
    
    # Double Header 24 May
    (2026, 5, 24, 15, 30, "KKR", "DC", "Kolkata"),
    (2026, 5, 24, 19, 30, "GT", "RR", "Ahmedabad"),
    
    # PLAYOFFS
    (2026, 5, 26, 19, 30, "Qualifier 1", "TBD", "Ahmedabad"),
    (2026, 5, 27, 19, 30, "Eliminator", "TBD", "Ahmedabad"),
    (2026, 5, 29, 19, 30, "Qualifier 2", "TBD", "Chennai"),
    (2026, 5, 31, 19, 30, "FINAL", "TBD", "Chennai"),
]

def get_today_matches():
    # India ki current date nikal raha hai
    today = datetime.now(IST).date()
    # Pura list scan karke aaj ke saare matches nikalega (Double headers included)
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
    # 2 PM se 12 AM tak window open rahegi agar aaj koi match hai
    return 14 <= now.hour <= 23 and len(get_today_matches()) > 0

def format_time_12h(hh, mm):
    period = "PM" if hh >= 12 else "AM"
    hour = hh % 12 if hh % 12 != 0 else 12
    return f"{hour}:{mm:02d} {period}"

def format_schedule_message():
    now = datetime.now(IST)
    today_str = now.strftime("%d %b, %Y (%A)")
    lines = [f"📅 *IPL 2026 Schedule*", f"Today: {today_str}", ""]
    
    matches = get_today_matches()
    if matches:
        lines.append("*Today's Thrill:*")
        for m in matches:
            lines.append(f"🏏 {m[5]} vs {m[6]} | ⏰ {format_time_12h(m[3], m[4])} IST")
    else:
        lines.append("No matches scheduled for today. 😴")
    
    upcoming = get_upcoming_matches(3)
    if upcoming:
        lines.append("\n*Next 3 Days:*")
        for m in upcoming:
            m_date = date(m[0], m[1], m[2]).strftime("%d %b")
            lines.append(f"🗓 {m_date} - {m[5]} vs {m[6]} ({format_time_12h(m[3], m[4])})")
            
    return "\n".join(lines)
