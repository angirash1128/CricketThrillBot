import sqlite3
import os
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")
DB_PATH = "/tmp/thrill_bot.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        subscribed INTEGER DEFAULT 1,
        joined_at TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS notified_alerts (
        match_id TEXT,
        alert_type TEXT,
        sent_at TEXT,
        PRIMARY KEY (match_id, alert_type)
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS match_history (
        match_id TEXT PRIMARY KEY,
        team1 TEXT,
        team2 TEXT,
        winner TEXT,
        thrill_score REAL,
        result_summary TEXT,
        played_on TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS probability_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        team1_prob REAL,
        team2_prob REAL,
        thrill_score REAL,
        logged_at TEXT
    )""")
    
    conn.commit()
    conn.close()

def add_user(user_id, username=""):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO users (user_id, username, subscribed, joined_at) VALUES (?, ?, 1, ?)",
              (user_id, username, now))
    c.execute("UPDATE users SET subscribed=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def remove_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET subscribed=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_all_subscribed_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE subscribed=1")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def is_alert_sent(match_id, alert_type):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM notified_alerts WHERE match_id=? AND alert_type=?",
              (str(match_id), alert_type))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_alert_sent(match_id, alert_type):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO notified_alerts (match_id, alert_type, sent_at) VALUES (?, ?, ?)",
              (str(match_id), alert_type, now))
    conn.commit()
    conn.close()

def save_match_result(match_id, team1, team2, winner, thrill_score, summary):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(IST).strftime("%Y-%m-%d")
    c.execute("""INSERT OR REPLACE INTO match_history 
                 (match_id, team1, team2, winner, thrill_score, result_summary, played_on) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (str(match_id), team1, team2, winner, thrill_score, summary, now))
    conn.commit()
    conn.close()

def get_today_matches():
    conn = get_conn()
    c = conn.cursor()
    today = datetime.now(IST).strftime("%Y-%m-%d")
    c.execute("SELECT team1, team2, winner, thrill_score, result_summary FROM match_history WHERE played_on=?",
              (today,))
    rows = c.fetchall()
    conn.close()
    return rows

def log_probability(match_id, t1_prob, t2_prob, thrill):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO probability_log (match_id, team1_prob, team2_prob, thrill_score, logged_at) VALUES (?, ?, ?, ?, ?)",
              (str(match_id), t1_prob, t2_prob, thrill, now))
    conn.commit()
    conn.close()

def get_last_probability(match_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT team1_prob, team2_prob, thrill_score FROM probability_log 
                 WHERE match_id=? ORDER BY id DESC LIMIT 1""", (str(match_id),))
    row = c.fetchone()
    conn.close()
    return row

def get_user_count():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE subscribed=1")
    count = c.fetchone()[0]
    conn.close()
    return count
