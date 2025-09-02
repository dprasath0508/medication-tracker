import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

class MedicationDB:
    """SQLite database handler for medication tracking with family circle support."""
    
    def __init__(self, db_path: str = "data/medications.db"):
        self.db_path = db_path
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables including family circle support."""
        with sqlite3.connect(self.db_path) as conn:
            # Users table (expanded)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    age INTEGER,
                    role TEXT DEFAULT 'patient',  -- 'patient' or 'family_member'
                    phone TEXT,
                    created_date TEXT
                )
            ''')
            
            # Family circles table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS family_circles (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    invite_code TEXT UNIQUE,
                    created_by INTEGER,
                    created_date TEXT,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # Family members relationship table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS family_members (
                    id INTEGER PRIMARY KEY,
                    family_circle_id INTEGER,
                    user_id INTEGER,
                    relationship TEXT,  -- 'patient', 'child', 'spouse', 'caregiver'
                    permissions TEXT,   -- JSON: ['view', 'manage_meds', 'set_reminders']
                    joined_date TEXT,
                    FOREIGN KEY (family_circle_id) REFERENCES family_circles (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(family_circle_id, user_id)
                )
            ''')
            
            # Medications table (updated with managed_by field)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS medications (
                    id INTEGER PRIMARY KEY,
                    patient_id INTEGER,
                    managed_by INTEGER,  -- who set up this medication
                    name TEXT NOT NULL,
                    dosage TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    times TEXT NOT NULL,  -- JSON array of times
                    active BOOLEAN DEFAULT 1,
                    notes TEXT,
                    created_date TEXT,
                    FOREIGN KEY (patient_id) REFERENCES users (id),
                    FOREIGN KEY (managed_by) REFERENCES users (id)
                )
            ''')
            
            # Dose logs table (existing)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS dose_logs (
                    id INTEGER PRIMARY KEY,
                    patient_id INTEGER,
                    medication_name TEXT,
                    scheduled_time TEXT,
                    taken BOOLEAN,
                    actual_time TEXT,
                    date TEXT,
                    timestamp TEXT,
                    logged_by INTEGER,  -- who marked this as taken/missed
                    FOREIGN KEY (patient_id) REFERENCES users (id),
                    FOREIGN KEY (logged_by) REFERENCES users (id)
                )
            ''')
            
            # Reminders table (new)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY,
                    patient_id INTEGER,
                    created_by INTEGER,
                    medication_name TEXT,
                    reminder_time TEXT,
                    message TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_date TEXT,
                    FOREIGN KEY (patient_id) REFERENCES users (id),
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
    
    # USER MANAGEMENT
    def add_user(self, name: str, email: str = None, age: int = None, role: str = 'patient', phone: str = None) -> int:
        """Add a new user and return their ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, age, role, phone, created_date) VALUES (?, ?, ?, ?, ?, ?)",
                (name, email, age, role, phone, datetime.now().isoformat())
            )
            return cursor.lastrowid
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # FAMILY CIRCLE MANAGEMENT
    def create_family_circle(self, name: str, created_by: int) -> tuple[int, str]:
        """Create a family circle and return (circle_id, invite_code)."""
        invite_code = str(uuid.uuid4())[:8].upper()  # 8-character invite code
        
        with sqlite3.connect(self.db_path) as conn:
            # Create family circle
            cursor = conn.execute(
                "INSERT INTO family_circles (name, invite_code, created_by, created_date) VALUES (?, ?, ?, ?)",
                (name, invite_code, created_by, datetime.now().isoformat())
            )
            circle_id = cursor.lastrowid
            
            # Add creator as first member
            conn.execute(
                "INSERT INTO family_members (family_circle_id, user_id, relationship, permissions, joined_date) VALUES (?, ?, ?, ?, ?)",
                (circle_id, created_by, 'creator', json.dumps(['view', 'manage_meds', 'set_reminders', 'invite_members']), datetime.now().isoformat())
            )
            
            return circle_id, invite_code
    
    def join_family_circle(self, invite_code: str, user_id: int, relationship: str = 'family_member') -> bool:
        """Join a family circle using invite code."""
        with sqlite3.connect(self.db_path) as conn:
            # Find family circle
            cursor = conn.execute("SELECT id FROM family_circles WHERE invite_code = ?", (invite_code,))
            circle = cursor.fetchone()
            if not circle:
                return False
            
            circle_id = circle[0]
            
            # Add member to circle
            try:
                conn.execute(
                    "INSERT INTO family_members (family_circle_id, user_id, relationship, permissions, joined_date) VALUES (?, ?, ?, ?, ?)",
                    (circle_id, user_id, relationship, json.dumps(['view', 'set_reminders']), datetime.now().isoformat())
                )
                return True
            except sqlite3.IntegrityError:  # User already in circle
                return False
    
    def get_user_family_circles(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all family circles a user belongs to."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT fc.*, fm.relationship, fm.permissions
                FROM family_circles fc
                JOIN family_members fm ON fc.id = fm.family_circle_id
                WHERE fm.user_id = ?
            """, (user_id,))
            circles = []
            for row in cursor.fetchall():
                circle = dict(row)
                circle['permissions'] = json.loads(circle['permissions'])
                circles.append(circle)
            return circles
    
    def get_family_circle_members(self, circle_id: int) -> List[Dict[str, Any]]:
        """Get all members of a family circle."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT u.*, fm.relationship, fm.permissions, fm.joined_date
                FROM users u
                JOIN family_members fm ON u.id = fm.user_id
                WHERE fm.family_circle_id = ?
            """, (circle_id,))
            members = []
            for row in cursor.fetchall():
                member = dict(row)
                member['permissions'] = json.loads(member['permissions'])
                members.append(member)
            return members
    
    # MEDICATION MANAGEMENT (updated for family support)
    def add_medication(self, patient_id: int, managed_by: int, name: str, dosage: str, frequency: str, times: List[str], notes: str = None) -> int:
        """Add a medication for a patient (can be managed by family member)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO medications 
                   (patient_id, managed_by, name, dosage, frequency, times, notes, created_date) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (patient_id, managed_by, name, dosage, frequency, json.dumps(times), notes, datetime.now().isoformat())
            )
            return cursor.lastrowid
    
    def get_patient_medications(self, patient_id: int) -> List[Dict[str, Any]]:
        """Get all active medications for a patient."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT m.*, u.name as managed_by_name
                FROM medications m
                LEFT JOIN users u ON m.managed_by = u.id
                WHERE m.patient_id = ? AND m.active = 1
            """, (patient_id,))
            medications = []
            for row in cursor.fetchall():
                med = dict(row)
                med['times'] = json.loads(med['times'])
                medications.append(med)
            return medications
    
    def log_dose(self, patient_id: int, medication_name: str, scheduled_time: str, taken: bool, logged_by: int, actual_time: str = None) -> int:
        """Log a dose taken/missed."""
        actual_time = actual_time or datetime.now().strftime("%H:%M")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO dose_logs 
                   (patient_id, medication_name, scheduled_time, taken, actual_time, date, timestamp, logged_by) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (patient_id, medication_name, scheduled_time, taken, actual_time, 
                 datetime.now().date().isoformat(), datetime.now().isoformat(), logged_by)
            )
            return cursor.lastrowid
    
    # FAMILY DASHBOARD QUERIES
    def get_family_patients_status(self, family_member_id: int) -> List[Dict[str, Any]]:
        """Get medication status for all patients in family member's circles."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT DISTINCT u.id, u.name, u.age,
                       COUNT(m.id) as total_medications,
                       fc.name as family_circle_name
                FROM users u
                JOIN family_members fm_patient ON u.id = fm_patient.user_id
                JOIN family_circles fc ON fm_patient.family_circle_id = fc.id
                JOIN family_members fm_viewer ON fc.id = fm_viewer.family_circle_id
                LEFT JOIN medications m ON u.id = m.patient_id AND m.active = 1
                WHERE fm_viewer.user_id = ? AND u.role = 'patient'
                GROUP BY u.id, u.name, u.age, fc.name
            """, (family_member_id,))
            
            patients = []
            for row in cursor.fetchall():
                patient = dict(row)
                # Get recent adherence
                patient['adherence_rate'] = self.get_patient_adherence(patient['id'], days=7)
                patients.append(patient)
            return patients
    
    def get_patient_adherence(self, patient_id: int, days: int = 7) -> float:
        """Calculate adherence rate for patient over last X days."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT COUNT(*) as total, SUM(taken) as taken_count 
                   FROM dose_logs 
                   WHERE patient_id = ? AND date >= date('now', '-{} days')""".format(days),
                (patient_id,)
            )
            result = cursor.fetchone()
            if result[0] == 0:
                return 0.0
            return (result[1] / result[0]) * 100
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users")
            return [dict(row) for row in cursor.fetchall()]