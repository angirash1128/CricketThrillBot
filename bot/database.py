# database.py
# Ye file SQLite database manage karti hai
# Saare user data yahan save hota hai

import sqlite3
import os
from datetime import datetime

# Database file ka path
DB_PATH = "cricket_thrill.db"

def get_connection():
    """Database se connection banao"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Results dict jaisi milein
    return conn

def setup_database():
    """
    Pehli baar chalane par database aur table banao
    Agar pehle se hai to kuch nahi hoga
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table banao
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            join_date TEXT,
            favorite_team TEXT,
            alert_preference TEXT,
            setup_complete INTEGER DEFAULT 0,
            last_active TEXT,
            notifications_enabled INTEGER DEFAULT 1,
            selected_match_id TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database ready")

def user_exists(user_id):
    """Check karo ki user pehle se registered hai ya nahi"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id = ?", 
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def is_setup_complete(user_id):
    """Check karo ki user ka onboarding complete hua hai ya nahi"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT setup_complete FROM users WHERE user_id = ?", 
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result["setup_complete"] == 1
    return False

def create_user(user_id, name):
    """Naya user database mein add karo"""
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Agar user pehle se hai to ignore karo
    cursor.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, name, join_date, last_active, setup_complete, notifications_enabled)
        VALUES (?, ?, ?, ?, 0, 1)
    ''', (user_id, name, now, now))
    
    conn.commit()
    conn.close()

def update_user_field(user_id, field, value):
    """User ka koi bhi ek field update karo"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # last_active bhi update karo
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        f"UPDATE users SET {field} = ?, last_active = ? WHERE user_id = ?",
        (value, now, user_id)
    )
    
    conn.commit()
    conn.close()

def complete_setup(user_id):
    """User ka setup complete mark karo"""
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        UPDATE users 
        SET setup_complete = 1, last_active = ?
        WHERE user_id = ?
    ''', (now, user_id))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    """Ek user ki saari info lao"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM users WHERE user_id = ?", 
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def get_all_active_users():
    """
    Saare active users lao jinhe alerts bhejna hai
    setup_complete = 1 AND notifications_enabled = 1
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, name, favorite_team, alert_preference 
        FROM users 
        WHERE setup_complete = 1 
        AND notifications_enabled = 1
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def stop_notifications(user_id):
    """User ke notifications band karo"""
    update_user_field(user_id, "notifications_enabled", 0)

def resume_notifications(user_id):
    """User ke notifications chalu karo"""
    update_user_field(user_id, "notifications_enabled", 1)

def update_last_active(user_id):
    """User ki last active time update karo"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE users SET last_active = ? WHERE user_id = ?",
        (now, user_id)
    )
    conn.commit()
    conn.close()