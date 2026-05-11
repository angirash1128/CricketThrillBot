# IPL 2026 Complete Schedule
# Format: (month, day, hour, minute, team1, team2)

IPL_SCHEDULE = [
    # April 2026 - already played
    (4, 25, 19, 30, "MI", "KKR"),
    (4, 26, 15, 30, "SRH", "RR"),
    (4, 26, 19, 30, "DC", "CSK"),
    (4, 27, 19, 30, "GT", "LSG"),
    (4, 28, 19, 30, "PBKS", "RCB"),
    (4, 29, 19, 30, "KKR", "SRH"),
    (4, 30, 19, 30, "RR", "MI"),

    # May 2026
    (5, 1, 19, 30, "CSK", "GT"),
    (5, 2, 19, 30, "RR", "DC"),
    (5, 3, 15, 30, "LSG", "PBKS"),
    (5, 3, 19, 30, "KKR", "MI"),
    (5, 4, 19, 30, "SRH", "CSK"),
    (5, 5, 19, 30, "RCB", "GT"),
    (5, 6, 19, 30, "DC", "LSG"),
    (5, 7, 19, 30, "MI", "RR"),
    (5, 8, 19, 30, "PBKS", "KKR"),
    (5, 9, 19, 30, "CSK", "SRH"),
    (5, 10, 15, 30, "GT", "RCB"),
    (5, 10, 19, 30, "LSG", "DC"),
    (5, 11, 15, 30, "RR", "PBKS"),
    (5, 11, 19, 30, "MI", "CSK"),
    (5, 12, 19, 30, "KKR", "GT"),
    (5, 13, 19, 30, "SRH", "RCB"),
    (5, 14, 19, 30, "DC", "MI"),
    (5, 15, 19, 30, "LSG", "RR"),
    (5, 16, 15, 30, "PBKS", "SRH"),
    (5, 16, 19, 30, "CSK", "KKR"),
    (5, 17, 15, 30, "GT", "DC"),
    (5, 17, 19, 30, "RCB", "MI"),
    (5, 18, 19, 30, "RR", "LSG"),
    (5, 19, 19, 30, "KKR", "PBKS"),
    (5, 20, 19, 30, "SRH", "GT"),

    # Qualifier 1
    (5, 20, 19, 30, "TBD", "TBD"),
    # Eliminator
    (5, 21, 19, 30, "TBD", "TBD"),
    # Qualifier 2
    (5, 23, 19, 30, "TBD", "TBD"),
    # FINAL
    (5, 25, 19, 30, "TBD", "TBD"),
]


def get_todays_matches():
    """Aaj ke matches return karo"""
    from datetime import datetime
    now = datetime.now()

    matches = []
    for m, d, h, mi, t1, t2 in IPL_SCHEDULE:
        if m == now.month and d == now.day:
            matches.append({
                "hour": h,
                "minute": mi,
                "team1": t1,
                "team2": t2
            })
    return matches


def get_upcoming_matches(days=3):
    """Agle kuch dino ke matches return karo"""
    from datetime import datetime, timedelta
    now = datetime.now()

    upcoming = []
    for i in range(1, days + 1):
        future = now + timedelta(days=i)
        for m, d, h, mi, t1, t2 in IPL_SCHEDULE:
            if m == future.month and d == future.day:
                upcoming.append({
                    "month": m,
                    "day": d,
                    "hour": h,
                    "minute": mi,
                    "team1": t1,
                    "team2": t2
                })
    return upcoming


def is_match_time_now():
    """Kya abhi match ka time hai?"""
    from datetime import datetime
    now = datetime.now()
    today_matches = get_todays_matches()

    for match in today_matches:
        current_mins = now.hour * 60 + now.minute
        match_start_mins = match["hour"] * 60 + match["minute"]
        window_start = match_start_mins - 15
        window_end = match_start_mins + 240

        if window_start <= current_mins <= window_end:
            return True
    return False
