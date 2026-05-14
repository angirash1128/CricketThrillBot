import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")

def format_schedule_message(matches_data):
    if not matches_data: return "📅 *IPL 2026 Schedule*\n\nData refresh ho raha hai... ⏳"
    now = datetime.now(IST)
    sorted_matches = sorted(matches_data, key=lambda x: x.get("dateTimeGMT", ""))

    lines = [f"📅 *IPL 2026 Schedule*", "_" * 20, ""]
    count = 0
    for m in sorted_matches:
        dt_gmt = m.get("dateTimeGMT")
        if dt_gmt:
            try:
                ist_dt = datetime.strptime(dt_gmt, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.utc).astimezone(IST)
                if ist_dt.date() < now.date(): continue
                
                label = "📌 *NEXT MATCH*" if count == 0 else f"🗓 {ist_dt.strftime('%d %b')}"
                lines.append(f"{label}\n🏏 {m['t1']} vs {m['t2']}\n⏰ {ist_dt.strftime('%I:%M %p')} IST\n")
                count += 1
                if count >= 5: break
            except: continue
    return "\n".join(lines)
