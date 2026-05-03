# IPL 2026 Schedule
# Ye hardcoded hai - 0 API calls
# Format: (month, day, hour, minute, team1, team2)

IPL_SCHEDULE = [
    # May 2026 matches (add karte jao)
    (5, 3, 19, 30, "KKR", "PBKS"),
    (5, 4, 15, 30, "LSG", "MI"),
    (5, 4, 19, 30, "RCB", "SRH"),
    (5, 5, 19, 30, "DC", "GT"),
    (5, 6, 19, 30, "CSK", "RR"),
    (5, 7, 19, 30, "PBKS", "MI"),
    (5, 8, 19, 30, "KKR", "RCB"),
    (5, 9, 19, 30, "SRH", "LSG"),
    (5, 10, 15, 30, "GT", "DC"),
    (5, 10, 19, 30, "CSK", "PBKS"),
    (5, 11, 15, 30, "MI", "RR"),
    (5, 11, 19, 30, "SRH", "KKR"),
    # Playoffs (dates TBD - baad me add karenge)
]


def get_todays_matches():
    """Aaj ke matches return karo"""
    from datetime import datetime
    now = datetime.now()
    today_month = now.month
    today_day = now.day

    matches = []
    for m, d, h, mi, t1, t2 in IPL_SCHEDULE:
        if m == today_month and d == today_day:
            matches.append({
                "hour": h,
                "minute": mi,
                "team1": t1,
                "team2": t2
            })

    return matches


def is_match_time_now():
    """Kya abhi match ka time hai?"""
    from datetime import datetime
    now = datetime.now()
    today_matches = get_todays_matches()

    for match in today_matches:
        # Match start se 15 min pehle se
        # Match end tak (roughly 4 hours)
        match_start_hour = match["hour"]
        match_start_min = match["minute"]

        # Current time in minutes
        current_mins = now.hour * 60 + now.minute

        # Match window: 15 min before to 4 hours after
        match_start_mins = match_start_hour * 60 + match_start_min
        window_start = match_start_mins - 15
        window_end = match_start_mins + 240  # 4 hours

        if window_start <= current_mins <= window_end:
            return True

    return False
