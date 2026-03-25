import sqlite3
import json
import uuid
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
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

            # ===== AUTHENTICATION TABLES =====

            # User credentials (password-based auth)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_credentials (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email_verified BOOLEAN DEFAULT 0,
                    email_verification_token TEXT,
                    email_verification_expiry TEXT,
                    password_reset_token TEXT,
                    password_reset_expiry TEXT,
                    created_date TEXT,
                    updated_date TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')

            # OTP verifications (phone-based auth)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS otp_verifications (
                    id INTEGER PRIMARY KEY,
                    phone TEXT NOT NULL,
                    otp_hash TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    verified BOOLEAN DEFAULT 0,
                    user_id INTEGER,
                    purpose TEXT DEFAULT 'login',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # User sessions (secure token-based)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    device_fingerprint TEXT,
                    device_name TEXT,
                    ip_address TEXT,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')

            # Enhanced invite codes with expiration
            conn.execute('''
                CREATE TABLE IF NOT EXISTS invite_codes (
                    id INTEGER PRIMARY KEY,
                    family_circle_id INTEGER NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    max_uses INTEGER DEFAULT 1,
                    current_uses INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    deep_link_token TEXT UNIQUE,
                    FOREIGN KEY (family_circle_id) REFERENCES family_circles (id),
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')

            # Login attempts tracking (security/rate limiting)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY,
                    identifier TEXT NOT NULL,
                    attempt_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TEXT NOT NULL,
                    lockout_until TEXT
                )
            ''')

            # Add new columns to users table if they don't exist
            self._add_column_if_not_exists(conn, 'users', 'phone_verified', 'BOOLEAN DEFAULT 0')
            self._add_column_if_not_exists(conn, 'users', 'primary_auth_method', "TEXT DEFAULT 'phone'")
            self._add_column_if_not_exists(conn, 'users', 'account_status', "TEXT DEFAULT 'active'")
            self._add_column_if_not_exists(conn, 'users', 'last_login', 'TEXT')

    def _add_column_if_not_exists(self, conn, table: str, column: str, column_type: str):
        """Safely add a column to a table if it doesn't exist."""
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
    
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

    # ===== AUTHENTICATION METHODS =====

    def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields."""
        if not kwargs:
            return False
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [user_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE users SET {fields} WHERE id = ?", values)
            return True

    # --- User Credentials (Password Auth) ---

    def create_user_credentials(self, user_id: int, password_hash: str) -> int:
        """Create credentials entry for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO user_credentials
                   (user_id, password_hash, created_date, updated_date)
                   VALUES (?, ?, ?, ?)""",
                (user_id, password_hash, datetime.now().isoformat(), datetime.now().isoformat())
            )
            return cursor.lastrowid

    def get_user_credentials(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get credentials for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM user_credentials WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_password_hash(self, user_id: int, password_hash: str) -> bool:
        """Update user's password hash."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE user_credentials SET password_hash = ?, updated_date = ? WHERE user_id = ?",
                (password_hash, datetime.now().isoformat(), user_id)
            )
            return True

    def set_email_verification_token(self, user_id: int, token: str, expiry_hours: int = 24) -> bool:
        """Set email verification token."""
        expiry = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE user_credentials
                   SET email_verification_token = ?, email_verification_expiry = ?
                   WHERE user_id = ?""",
                (token, expiry, user_id)
            )
            return True

    def verify_email_token(self, token: str) -> Optional[int]:
        """Verify email token and return user_id if valid."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT user_id FROM user_credentials
                   WHERE email_verification_token = ? AND email_verification_expiry > ?""",
                (token, datetime.now().isoformat())
            )
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                conn.execute(
                    """UPDATE user_credentials
                       SET email_verified = 1, email_verification_token = NULL
                       WHERE user_id = ?""",
                    (user_id,)
                )
                return user_id
            return None

    def set_password_reset_token(self, user_id: int, token: str, expiry_hours: int = 1) -> bool:
        """Set password reset token."""
        expiry = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE user_credentials
                   SET password_reset_token = ?, password_reset_expiry = ?
                   WHERE user_id = ?""",
                (token, expiry, user_id)
            )
            return True

    def verify_password_reset_token(self, token: str) -> Optional[int]:
        """Verify password reset token and return user_id if valid."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT user_id FROM user_credentials
                   WHERE password_reset_token = ? AND password_reset_expiry > ?""",
                (token, datetime.now().isoformat())
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def clear_password_reset_token(self, user_id: int) -> bool:
        """Clear password reset token after use."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE user_credentials SET password_reset_token = NULL WHERE user_id = ?",
                (user_id,)
            )
            return True

    # --- OTP Verifications ---

    def create_otp(self, phone: str, otp_hash: str, purpose: str = 'login',
                   user_id: int = None, expiry_minutes: int = 5) -> int:
        """Create OTP verification entry."""
        now = datetime.now()
        expires = now + timedelta(minutes=expiry_minutes)
        with sqlite3.connect(self.db_path) as conn:
            # Invalidate any existing OTPs for this phone
            conn.execute(
                "DELETE FROM otp_verifications WHERE phone = ? AND verified = 0",
                (phone,)
            )
            cursor = conn.execute(
                """INSERT INTO otp_verifications
                   (phone, otp_hash, created_at, expires_at, user_id, purpose)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (phone, otp_hash, now.isoformat(), expires.isoformat(), user_id, purpose)
            )
            return cursor.lastrowid

    def get_active_otp(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get active (non-expired, non-verified) OTP for phone."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM otp_verifications
                   WHERE phone = ? AND verified = 0 AND expires_at > ?
                   ORDER BY created_at DESC LIMIT 1""",
                (phone, datetime.now().isoformat())
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def increment_otp_attempts(self, otp_id: int) -> int:
        """Increment OTP attempt count and return new count."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE otp_verifications SET attempts = attempts + 1 WHERE id = ?", (otp_id,))
            cursor = conn.execute("SELECT attempts FROM otp_verifications WHERE id = ?", (otp_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    def mark_otp_verified(self, otp_id: int) -> bool:
        """Mark OTP as verified."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE otp_verifications SET verified = 1 WHERE id = ?", (otp_id,))
            return True

    def cleanup_expired_otps(self) -> int:
        """Remove expired OTPs and return count deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM otp_verifications WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            return cursor.rowcount

    # --- User Sessions ---

    def create_session(self, user_id: int, session_token: str, device_fingerprint: str = None,
                       device_name: str = None, ip_address: str = None,
                       expiry_days: int = 7) -> int:
        """Create a new user session."""
        now = datetime.now()
        expires = now + timedelta(days=expiry_days)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO user_sessions
                   (user_id, session_token, device_fingerprint, device_name, ip_address,
                    created_at, last_activity, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, session_token, device_fingerprint, device_name, ip_address,
                 now.isoformat(), now.isoformat(), expires.isoformat())
            )
            return cursor.lastrowid

    def get_session_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get session by token if active and not expired."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM user_sessions
                   WHERE session_token = ? AND is_active = 1 AND expires_at > ?""",
                (token, datetime.now().isoformat())
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_session_activity(self, token: str) -> bool:
        """Update last activity timestamp for session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE user_sessions SET last_activity = ? WHERE session_token = ?",
                (datetime.now().isoformat(), token)
            )
            return True

    def invalidate_session(self, token: str) -> bool:
        """Invalidate a session (logout)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE user_sessions SET is_active = 0 WHERE session_token = ?",
                (token,)
            )
            return True

    def invalidate_all_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE user_sessions SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            return cursor.rowcount

    def get_user_active_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active sessions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT id, device_name, ip_address, created_at, last_activity
                   FROM user_sessions
                   WHERE user_id = ? AND is_active = 1 AND expires_at > ?
                   ORDER BY last_activity DESC""",
                (user_id, datetime.now().isoformat())
            )
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM user_sessions WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            return cursor.rowcount

    # --- Enhanced Invite Codes ---

    def create_invite_code(self, family_circle_id: int, created_by: int,
                           expiry_hours: int = 72, max_uses: int = 10) -> Dict[str, Any]:
        """Create an invite code with expiration."""
        code = str(uuid.uuid4())[:8].upper()
        deep_link_token = secrets.token_urlsafe(32)
        now = datetime.now()
        expires = now + timedelta(hours=expiry_hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO invite_codes
                   (family_circle_id, code, created_by, created_at, expires_at, max_uses, deep_link_token)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (family_circle_id, code, created_by, now.isoformat(), expires.isoformat(),
                 max_uses, deep_link_token)
            )
            return {
                'id': cursor.lastrowid,
                'code': code,
                'deep_link_token': deep_link_token,
                'expires_at': expires.isoformat(),
                'max_uses': max_uses
            }

    def get_invite_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get invite code if valid (not expired, not maxed out)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT ic.*, fc.name as circle_name
                   FROM invite_codes ic
                   JOIN family_circles fc ON ic.family_circle_id = fc.id
                   WHERE ic.code = ? AND ic.is_active = 1
                   AND ic.expires_at > ? AND ic.current_uses < ic.max_uses""",
                (code.upper(), datetime.now().isoformat())
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_invite_by_deep_link(self, token: str) -> Optional[Dict[str, Any]]:
        """Get invite code by deep link token."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT ic.*, fc.name as circle_name
                   FROM invite_codes ic
                   JOIN family_circles fc ON ic.family_circle_id = fc.id
                   WHERE ic.deep_link_token = ? AND ic.is_active = 1
                   AND ic.expires_at > ? AND ic.current_uses < ic.max_uses""",
                (token, datetime.now().isoformat())
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def use_invite_code(self, code: str, user_id: int, relationship: str = 'family_member') -> bool:
        """Use an invite code to join a family circle."""
        invite = self.get_invite_code(code)
        if not invite:
            return False

        with sqlite3.connect(self.db_path) as conn:
            # Increment usage count
            conn.execute(
                "UPDATE invite_codes SET current_uses = current_uses + 1 WHERE code = ?",
                (code.upper(),)
            )

            # Add member to circle
            try:
                conn.execute(
                    """INSERT INTO family_members
                       (family_circle_id, user_id, relationship, permissions, joined_date)
                       VALUES (?, ?, ?, ?, ?)""",
                    (invite['family_circle_id'], user_id, relationship,
                     json.dumps(['view', 'set_reminders']), datetime.now().isoformat())
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def deactivate_invite_code(self, code: str) -> bool:
        """Deactivate an invite code."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE invite_codes SET is_active = 0 WHERE code = ?", (code.upper(),))
            return True

    # --- Login Attempts (Rate Limiting) ---

    def record_login_attempt(self, identifier: str, attempt_type: str, success: bool,
                             ip_address: str = None, user_agent: str = None) -> int:
        """Record a login attempt."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO login_attempts
                   (identifier, attempt_type, success, ip_address, user_agent, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (identifier, attempt_type, success, ip_address, user_agent, datetime.now().isoformat())
            )
            return cursor.lastrowid

    def get_recent_failed_attempts(self, identifier: str, minutes: int = 15) -> int:
        """Get count of failed login attempts in the last X minutes."""
        since = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT COUNT(*) FROM login_attempts
                   WHERE identifier = ? AND success = 0 AND timestamp > ?""",
                (identifier, since)
            )
            return cursor.fetchone()[0]

    def set_lockout(self, identifier: str, lockout_minutes: int = 30) -> bool:
        """Set lockout for an identifier."""
        lockout_until = (datetime.now() + timedelta(minutes=lockout_minutes)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE login_attempts SET lockout_until = ?
                   WHERE identifier = ? AND timestamp = (
                       SELECT MAX(timestamp) FROM login_attempts WHERE identifier = ?
                   )""",
                (lockout_until, identifier, identifier)
            )
            return True

    def is_locked_out(self, identifier: str) -> bool:
        """Check if identifier is currently locked out."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT lockout_until FROM login_attempts
                   WHERE identifier = ? AND lockout_until IS NOT NULL
                   ORDER BY timestamp DESC LIMIT 1""",
                (identifier,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0] > datetime.now().isoformat()
            return False

    def cleanup_old_login_attempts(self, days: int = 30) -> int:
        """Remove old login attempts and return count deleted."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM login_attempts WHERE timestamp < ?", (since,))
            return cursor.rowcount