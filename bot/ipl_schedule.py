import pytz
from datetime import datetime, timedelta

IST = pytz.timezone("Asia/Kolkata")

def parse_match_datetime(dt_gmt_str):
    try:
        dt_utc = datetime.strptime(dt_gmt_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.utc)
        return dt_utc.astimezone(IST)
    except:
        return None

def filter_ipl_matches(all_matches):
    if not all_matches:
        return []
    
    ipl_keywords = ["indian premier league", "ipl"]
    ipl_matches = []
    
    for m in all_matches:
        series = (m.get("series") or "").lower()
        if any(k in series for k in ipl_keywords):
            ipl_matches.append(m)
    
    return ipl_matches

def get_today_ipl_match(all_matches):
    """Returns today's IPL match (if any) with parsed IST datetime."""
    ipl_matches = filter_ipl_matches(all_matches)
    today = datetime.now(IST).date()
    
    for m in ipl_matches:
        dt_ist = parse_match_datetime(m.get("dateTimeGMT", ""))
        if dt_ist and dt_ist.date() == today:
            m["_ist_datetime"] = dt_ist
            return m
    
    return None

def get_upcoming_ipl_matches(all_matches, limit=5):
    """Returns next N upcoming IPL matches sorted by date."""
    ipl_matches = filter_ipl_matches(all_matches)
    now = datetime.now(IST)
    
    upcoming = []
    for m in ipl_matches:
        dt_ist = parse_match_datetime(m.get("dateTimeGMT", ""))
        if dt_ist and dt_ist >= now - timedelta(hours=4):
            m_copy = dict(m)
            m_copy["_ist_datetime"] = dt_ist
            m_copy["date_ist"] = dt_ist.strftime("%d %b")
            m_copy["time_ist"] = dt_ist.strftime("%I:%M %p")
            upcoming.append(m_copy)
    
    upcoming.sort(key=lambda x: x["_ist_datetime"])
    return upcoming[:limit]

def is_match_time_close(match_data, minutes_before=20):
    """Check if match is starting within next X minutes."""
    dt_ist = parse_match_datetime(match_data.get("dateTimeGMT", ""))
    if not dt_ist:
        return False
    
    now = datetime.now(IST)
    diff = (dt_ist - now).total_seconds() / 60
    return 0 <= diff <= minutes_before

def is_match_started(match_data):
    """Check if match start time has passed."""
    dt_ist = parse_match_datetime(match_data.get("dateTimeGMT", ""))
    if not dt_ist:
        return False
    return datetime.now(IST) >= dt_ist

def minutes_until_match(match_data):
    """Returns minutes left until match starts (negative if started)."""
    dt_ist = parse_match_datetime(match_data.get("dateTimeGMT", ""))
    if not dt_ist:
        return None
    diff = (dt_ist - datetime.now(IST)).total_seconds() / 60
    return int(diff)

def format_schedule_message(matches_data):
    """Legacy function - kept for backward compatibility."""
    from alert_manager import upcoming_matches_message
    upcoming = get_upcoming_ipl_matches(matches_data, limit=5)
    return upcoming_matches_message(upcoming)
