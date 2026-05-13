import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")

def format_time_12h(hh, mm):
    period = "PM" if hh >= 12 else "AM"
    hour = hh % 12 if hh % 12 != 0 else 12
    return f"{hour}:{mm:02d} {period}"

def format_schedule_message(matches_data):
    """API data ko professional ascending order mein badalta hai"""
    if not matches_data:
        return "📅 *IPL 2026 Schedule*\n\nData refresh ho raha hai... Thodi der mein check karein. ⏳"

    now = datetime.now(IST)
    
    # Matches ko date ke hisaab se sort karna (Pehele aane wala pehle)
    # API data aksar reverse hota hai, hum use sahi kar rahe hain
    sorted_matches = sorted(matches_data, key=lambda x: x.get("dateTimeGMT", ""))

    lines = [
        f"📅 *IPL 2026 Schedule*",
        f"Last Updated: {now.strftime('%I:%M %p')} IST",
        "_" * 20,
        ""
    ]
    
    upcoming_count = 0
    for m in sorted_matches:
        # Sirf 5 matches dikhayenge taaki message readable rahe
        if upcoming_count >= 5:
            break
            
        t1 = m.get("t1", "TBD")
        t2 = m.get("t2", "TBD")
        status = m.get("status", "Upcoming")
        dateTimeGMT = m.get("dateTimeGMT", "")
        
        if dateTimeGMT:
            try:
                # GMT string ko parse karke IST mein badalna
                utc_dt = datetime.strptime(dateTimeGMT, "%Y-%m-%dT%H:%M:%S")
                ist_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(IST)
                
                # Agar match purana ho chuka hai (aaj se pehle ka), to skip karein
                if ist_dt.date() < now.date():
                    continue
                
                date_str = ist_dt.strftime("%d %b (%A)")
                time_str = ist_dt.strftime("%I:%M %p")
                
                lines.append(f"🗓 *{date_str}*")
                lines.append(f"🏏 {t1} vs {t2}")
                lines.append(f"⏰ {time_str} IST | 📍 {status}")
                lines.append("-" * 15)
                upcoming_count += 1
            except Exception as e:
                continue

    if upcoming_count == 0:
        return "📅 *IPL 2026 Schedule*\n\nAaj ki list mein koi upcoming matches nahi mile. 😴"

    return "\n".join(lines)
