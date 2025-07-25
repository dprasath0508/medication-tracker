import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
import os

class MedicationDB:
    """SQLite database handler for medication tracking."""
    
    def __init__(self, db_path: str = "data/medications.db"):
        self.db_path = db_path
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER,
                    created_date TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS medications (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    dosage TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    times TEXT NOT NULL,  -- JSON array of times
                    active BOOLEAN DEFAULT 1,
                    created_date TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS dose_logs (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    medication_name TEXT,
                    scheduled_time TEXT,
                    taken BOOLEAN,
                    actual_time TEXT,
                    date TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
    
    def add_user(self, name: str, age: int = None) -> int:
        """Add a new user and return their ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, age, created_date) VALUES (?, ?, ?)",
                (name, age, datetime.now().isoformat())
            )
            return cursor.lastrowid
    
    def add_medication(self, user_id: int, name: str, dosage: str, frequency: str, times: List[str]) -> int:
        """Add a medication for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO medications 
                   (user_id, name, dosage, frequency, times, created_date) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, name, dosage, frequency, json.dumps(times), datetime.now().isoformat())
            )
            return cursor.lastrowid
    
    def get_user_medications(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active medications for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM medications WHERE user_id = ? AND active = 1",
                (user_id,)
            )
            medications = []
            for row in cursor.fetchall():
                med = dict(row)
                med['times'] = json.loads(med['times'])  # Convert JSON back to list
                medications.append(med)
            return medications
    
    def log_dose(self, user_id: int, medication_name: str, scheduled_time: str, taken: bool, actual_time: str = None) -> int:
        """Log a dose taken/missed."""
        actual_time = actual_time or datetime.now().strftime("%H:%M")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO dose_logs 
                   (user_id, medication_name, scheduled_time, taken, actual_time, date, timestamp) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, medication_name, scheduled_time, taken, actual_time, 
                 datetime.now().date().isoformat(), datetime.now().isoformat())
            )
            return cursor.lastrowid
    
    def get_user_adherence(self, user_id: int, days: int = 7) -> float:
        """Calculate adherence rate for user over last X days."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT COUNT(*) as total, SUM(taken) as taken_count 
                   FROM dose_logs 
                   WHERE user_id = ? AND date >= date('now', '-{} days')""".format(days),
                (user_id,)
            )
            result = cursor.fetchone()
            if result[0] == 0:  # total count
                return 0.0
            return (result[1] / result[0]) * 100  # taken_count / total * 100
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users")
            return [dict(row) for row in cursor.fetchall()]
        
        