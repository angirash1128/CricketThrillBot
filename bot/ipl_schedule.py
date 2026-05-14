import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")

def format_schedule_message(matches_data):
    if not matches_data:
        return "📅 *IPL 2026 Schedule*\n\nData refresh ho raha hai... ⏳"

    now = datetime.now(IST)
    # Sort matches by date (Today first)
    sorted_matches = sorted(matches_data, key=lambda x: x.get("dateTimeGMT", ""))

    lines = [f"📅 *IPL 2026 Schedule*", f"Last Updated: {now.strftime('%I:%M %p')} IST", "_" * 20, ""]
    
    count = 0
    for m in sorted_matches:
        if count >= 6: break
        t1, t2 = m.get("t1"), m.get("t2")
        status = m.get("status")
        dt_gmt = m.get("dateTimeGMT")
        
        if dt_gmt:
            try:
                utc_dt = datetime.strptime(dt_gmt, "%Y-%m-%dT%H:%M:%S")
                ist_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(IST)
                
                if ist_dt.date() < now.date(): continue
                
                lines.append(f"🗓 *{ist_dt.strftime('%d %b (%A)')}*")
                lines.append(f"🏏 {t1} vs {t2}")
                lines.append(f"⏰ {ist_dt.strftime('%I:%M %p')} IST | 📍 {status}")
                lines.append("-" * 15)
                count += 1
            except: continue
    return "\n".join(lines)
