import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")

def format_time_12h(hh, mm):
    period = "PM" if hh >= 12 else "AM"
    hour = hh % 12 if hh % 12 != 0 else 12
    return f"{hour}:{mm:02d} {period}"

def format_schedule_message(matches_data):
    """API se aaye matches ko sundar format mein convert karta hai"""
    if not matches_data:
        return "📅 *IPL 2026 Schedule*\n\nAbhi koi upcoming matches ki detail nahi mili. 😴"

    now = datetime.now(IST)
    lines = [f"📅 *IPL 2026 Schedule*", f"Updated: {now.strftime('%d %b, %H:%M')} IST", ""]
    
    # Sirf top 5 upcoming matches dikhayenge taaki message bada na ho
    lines.append("*Upcoming Matches:*")
    for m in matches_data[:5]:
        t1 = m.get("t1", "TBD")
        t2 = m.get("t2", "TBD")
        status = m.get("status", "Upcoming")
        dateTimeGMT = m.get("dateTimeGMT", "")
        
        # Time formatting
        time_display = ""
        if dateTimeGMT:
            try:
                # API time ko IST mein badalna
                utc_dt = datetime.strptime(dateTimeGMT, "%Y-%m-%dT%H:%M:%S")
                ist_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(IST)
                time_display = ist_dt.strftime("%d %b, %I:%M %p")
            except:
                time_display = "TBD"

        lines.append(f"🏏 *{t1} vs {t2}*")
        lines.append(f"⏰ {time_display} IST | 📍 {status}")
        lines.append("")

    return "\n".join(lines)
