import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")

def format_schedule_message(matches_data):
    """API data ko professional format mein badalta hai"""
    if not matches_data:
        return "📅 *IPL 2026 Schedule*\n\nData fetch ho raha hai, thodi der mein check karein... ⏳"

    now = datetime.now(IST)
    lines = [f"📅 *IPL 2026 Schedule*", f"Last Updated: {now.strftime('%I:%M %p')} IST", ""]
    
    lines.append("*Upcoming Thrill:*")
    # Sirf top 5 matches dikhayenge taaki list clean rahe
    for m in matches_data[:5]:
        t1 = m.get("t1", "TBD")
        t2 = m.get("t2", "TBD")
        status = m.get("status", "Upcoming")
        dateTimeGMT = m.get("dateTimeGMT", "")
        
        time_display = "TBD"
        if dateTimeGMT:
            try:
                # GMT to IST conversion
                utc_dt = datetime.strptime(dateTimeGMT, "%Y-%m-%dT%H:%M:%S")
                ist_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(IST)
                time_display = ist_dt.strftime("%d %b | %I:%M %p")
            except: pass

        lines.append(f"🏏 *{t1} vs {t2}*")
        lines.append(f"⏰ {time_display} IST | 📍 {status}")
        lines.append("----------------------------")

    return "\n".join(lines)
