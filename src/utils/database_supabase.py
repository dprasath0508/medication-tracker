"""Supabase database adapter for medication tracking.
Uses the same interface as database.py but connects to Supabase.
"""
import os
import json
import uuid
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from supabase import create_client, Client


class MedicationDB:
    """Supabase database handler for medication tracking with family circle support."""

    def __init__(self, db_path: str = None):
        """Initialize Supabase client. db_path is ignored (kept for compatibility)."""
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")

        self.client: Client = create_client(supabase_url, supabase_key)
        # For compatibility with scheduler.py which accesses db_path
        self.db_path = None

    def init_database(self):
        """No-op for Supabase - tables created via SQL schema."""
        pass

    # USER MANAGEMENT
    def add_user(self, name: str, email: str = None, age: int = None,
                 role: str = 'patient', phone: str = None) -> int:
        """Add a new user and return their ID."""
        data = {
            'name': name,
            'email': email,
            'age': age,
            'role': role,
            'phone': phone,
            'created_date': datetime.now().isoformat()
        }
        result = self.client.table('users').insert(data).execute()
        return result.data[0]['id']

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        result = self.client.table('users').select('*').eq('email', email).execute()
        return result.data[0] if result.data else None

    def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number."""
        result = self.client.table('users').select('*').eq('phone', phone).execute()
        return result.data[0] if result.data else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        result = self.client.table('users').select('*').eq('id', user_id).execute()
        return result.data[0] if result.data else None

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        result = self.client.table('users').select('*').execute()
        return result.data

    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields."""
        if not kwargs:
            return False
        self.client.table('users').update(kwargs).eq('id', user_id).execute()
        return True

    # FAMILY CIRCLE MANAGEMENT
    def create_family_circle(self, name: str, created_by: int) -> tuple:
        """Create a family circle and return (circle_id, invite_code)."""
        invite_code = str(uuid.uuid4())[:8].upper()

        # Create family circle
        data = {
            'name': name,
            'invite_code': invite_code,
            'created_by': created_by,
            'created_date': datetime.now().isoformat()
        }
        result = self.client.table('family_circles').insert(data).execute()
        circle_id = result.data[0]['id']

        # Add creator as first member
        member_data = {
            'family_circle_id': circle_id,
            'user_id': created_by,
            'relationship': 'creator',
            'permissions': ['view', 'manage_meds', 'set_reminders', 'invite_members'],
            'joined_date': datetime.now().isoformat()
        }
        self.client.table('family_members').insert(member_data).execute()

        return circle_id, invite_code

    def join_family_circle(self, invite_code: str, user_id: int,
                           relationship: str = 'family_member') -> bool:
        """Join a family circle using invite code."""
        # Find family circle
        result = self.client.table('family_circles').select('id').eq('invite_code', invite_code).execute()
        if not result.data:
            return False

        circle_id = result.data[0]['id']

        # Add member to circle
        try:
            member_data = {
                'family_circle_id': circle_id,
                'user_id': user_id,
                'relationship': relationship,
                'permissions': ['view', 'set_reminders'],
                'joined_date': datetime.now().isoformat()
            }
            self.client.table('family_members').insert(member_data).execute()
            return True
        except Exception:
            return False

    def get_user_family_circles(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all family circles a user belongs to."""
        result = self.client.table('family_members').select(
            '*, family_circles(*)'
        ).eq('user_id', user_id).execute()

        circles = []
        for row in result.data:
            circle = row['family_circles']
            circle['relationship'] = row['relationship']
            circle['permissions'] = row['permissions']
            circles.append(circle)
        return circles

    def get_family_circle_members(self, circle_id: int) -> List[Dict[str, Any]]:
        """Get all members of a family circle."""
        result = self.client.table('family_members').select(
            '*, users(*)'
        ).eq('family_circle_id', circle_id).execute()

        members = []
        for row in result.data:
            member = row['users']
            member['relationship'] = row['relationship']
            member['permissions'] = row['permissions']
            member['joined_date'] = row['joined_date']
            members.append(member)
        return members

    # MEDICATION MANAGEMENT
    def add_medication(self, patient_id: int, managed_by: int, name: str,
                       dosage: str, frequency: str, times: List[str],
                       notes: str = None) -> int:
        """Add a medication for a patient."""
        data = {
            'patient_id': patient_id,
            'managed_by': managed_by,
            'name': name,
            'dosage': dosage,
            'frequency': frequency,
            'times': times,  # Supabase handles JSON natively
            'notes': notes,
            'created_date': datetime.now().isoformat()
        }
        result = self.client.table('medications').insert(data).execute()
        return result.data[0]['id']

    def get_patient_medications(self, patient_id: int) -> List[Dict[str, Any]]:
        """Get all active medications for a patient."""
        result = self.client.table('medications').select(
            '*, users!managed_by(name)'
        ).eq('patient_id', patient_id).eq('active', True).execute()

        medications = []
        for row in result.data:
            med = dict(row)
            if 'users' in med and med['users']:
                med['managed_by_name'] = med['users']['name']
            del med['users']
            medications.append(med)
        return medications

    def log_dose(self, patient_id: int, medication_name: str, scheduled_time: str,
                 taken: bool, logged_by: int, actual_time: str = None) -> int:
        """Log a dose taken/missed."""
        actual_time = actual_time or datetime.now().strftime("%H:%M")
        data = {
            'patient_id': patient_id,
            'medication_name': medication_name,
            'scheduled_time': scheduled_time,
            'taken': taken,
            'actual_time': actual_time,
            'date': datetime.now().date().isoformat(),
            'timestamp': datetime.now().isoformat(),
            'logged_by': logged_by
        }
        result = self.client.table('dose_logs').insert(data).execute()
        return result.data[0]['id']

    # FAMILY DASHBOARD QUERIES
    def get_family_patients_status(self, family_member_id: int) -> List[Dict[str, Any]]:
        """Get medication status for all patients in family member's circles."""
        # Get family circles the member belongs to
        circles = self.get_user_family_circles(family_member_id)

        patients = []
        seen_ids = set()

        for circle in circles:
            members = self.get_family_circle_members(circle['id'])
            for member in members:
                if member['role'] == 'patient' and member['id'] not in seen_ids:
                    seen_ids.add(member['id'])
                    meds = self.get_patient_medications(member['id'])
                    patient = {
                        'id': member['id'],
                        'name': member['name'],
                        'age': member['age'],
                        'total_medications': len(meds),
                        'family_circle_name': circle['name'],
                        'adherence_rate': self.get_patient_adherence(member['id'], days=7)
                    }
                    patients.append(patient)

        return patients

    def get_patient_adherence(self, patient_id: int, days: int = 7) -> float:
        """Calculate adherence rate for patient over last X days."""
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()

        result = self.client.table('dose_logs').select('taken').eq(
            'patient_id', patient_id
        ).gte('date', start_date).execute()

        if not result.data:
            return 0.0

        total = len(result.data)
        taken = sum(1 for log in result.data if log['taken'])
        return (taken / total) * 100

    # USER CREDENTIALS
    def create_user_credentials(self, user_id: int, password_hash: str) -> int:
        """Create credentials entry for a user."""
        data = {
            'user_id': user_id,
            'password_hash': password_hash,
            'created_date': datetime.now().isoformat(),
            'updated_date': datetime.now().isoformat()
        }
        result = self.client.table('user_credentials').insert(data).execute()
        return result.data[0]['id']

    def get_user_credentials(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get credentials for a user."""
        result = self.client.table('user_credentials').select('*').eq('user_id', user_id).execute()
        return result.data[0] if result.data else None

    def update_password_hash(self, user_id: int, password_hash: str) -> bool:
        """Update user's password hash."""
        self.client.table('user_credentials').update({
            'password_hash': password_hash,
            'updated_date': datetime.now().isoformat()
        }).eq('user_id', user_id).execute()
        return True

    def set_email_verification_token(self, user_id: int, token: str, expiry_hours: int = 24) -> bool:
        """Set email verification token."""
        expiry = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        self.client.table('user_credentials').update({
            'email_verification_token': token,
            'email_verification_expiry': expiry
        }).eq('user_id', user_id).execute()
        return True

    def verify_email_token(self, token: str) -> Optional[int]:
        """Verify email token and return user_id if valid."""
        result = self.client.table('user_credentials').select('user_id').eq(
            'email_verification_token', token
        ).gt('email_verification_expiry', datetime.now().isoformat()).execute()

        if result.data:
            user_id = result.data[0]['user_id']
            self.client.table('user_credentials').update({
                'email_verified': True,
                'email_verification_token': None
            }).eq('user_id', user_id).execute()
            return user_id
        return None

    def set_password_reset_token(self, user_id: int, token: str, expiry_hours: int = 1) -> bool:
        """Set password reset token."""
        expiry = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        self.client.table('user_credentials').update({
            'password_reset_token': token,
            'password_reset_expiry': expiry
        }).eq('user_id', user_id).execute()
        return True

    def verify_password_reset_token(self, token: str) -> Optional[int]:
        """Verify password reset token and return user_id if valid."""
        result = self.client.table('user_credentials').select('user_id').eq(
            'password_reset_token', token
        ).gt('password_reset_expiry', datetime.now().isoformat()).execute()
        return result.data[0]['user_id'] if result.data else None

    def clear_password_reset_token(self, user_id: int) -> bool:
        """Clear password reset token after use."""
        self.client.table('user_credentials').update({
            'password_reset_token': None
        }).eq('user_id', user_id).execute()
        return True

    # OTP VERIFICATIONS
    def create_otp(self, phone: str, otp_hash: str, purpose: str = 'login',
                   user_id: int = None, expiry_minutes: int = 5) -> int:
        """Create OTP verification entry."""
        # Delete existing unverified OTPs
        self.client.table('otp_verifications').delete().eq('phone', phone).eq('verified', False).execute()

        now = datetime.now()
        expires = now + timedelta(minutes=expiry_minutes)

        data = {
            'phone': phone,
            'otp_hash': otp_hash,
            'created_at': now.isoformat(),
            'expires_at': expires.isoformat(),
            'user_id': user_id,
            'purpose': purpose
        }
        result = self.client.table('otp_verifications').insert(data).execute()
        return result.data[0]['id']

    def get_active_otp(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get active (non-expired, non-verified) OTP for phone."""
        result = self.client.table('otp_verifications').select('*').eq(
            'phone', phone
        ).eq('verified', False).gt(
            'expires_at', datetime.now().isoformat()
        ).order('created_at', desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    def increment_otp_attempts(self, otp_id: int) -> int:
        """Increment OTP attempt count and return new count."""
        result = self.client.table('otp_verifications').select('attempts').eq('id', otp_id).execute()
        current = result.data[0]['attempts'] if result.data else 0
        new_count = current + 1
        self.client.table('otp_verifications').update({'attempts': new_count}).eq('id', otp_id).execute()
        return new_count

    def mark_otp_verified(self, otp_id: int) -> bool:
        """Mark OTP as verified."""
        self.client.table('otp_verifications').update({'verified': True}).eq('id', otp_id).execute()
        return True

    def cleanup_expired_otps(self) -> int:
        """Remove expired OTPs."""
        result = self.client.table('otp_verifications').delete().lt(
            'expires_at', datetime.now().isoformat()
        ).execute()
        return len(result.data) if result.data else 0

    # USER SESSIONS
    def create_session(self, user_id: int, session_token: str, device_fingerprint: str = None,
                       device_name: str = None, ip_address: str = None, expiry_days: int = 7) -> int:
        """Create a new user session."""
        now = datetime.now()
        expires = now + timedelta(days=expiry_days)

        data = {
            'user_id': user_id,
            'session_token': session_token,
            'device_fingerprint': device_fingerprint,
            'device_name': device_name,
            'ip_address': ip_address,
            'created_at': now.isoformat(),
            'last_activity': now.isoformat(),
            'expires_at': expires.isoformat()
        }
        result = self.client.table('user_sessions').insert(data).execute()
        return result.data[0]['id']

    def get_session_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get session by token if active and not expired."""
        result = self.client.table('user_sessions').select('*').eq(
            'session_token', token
        ).eq('is_active', True).gt(
            'expires_at', datetime.now().isoformat()
        ).execute()
        return result.data[0] if result.data else None

    def update_session_activity(self, token: str) -> bool:
        """Update last activity timestamp for session."""
        self.client.table('user_sessions').update({
            'last_activity': datetime.now().isoformat()
        }).eq('session_token', token).execute()
        return True

    def invalidate_session(self, token: str) -> bool:
        """Invalidate a session (logout)."""
        self.client.table('user_sessions').update({'is_active': False}).eq('session_token', token).execute()
        return True

    def invalidate_all_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user."""
        result = self.client.table('user_sessions').update(
            {'is_active': False}
        ).eq('user_id', user_id).execute()
        return len(result.data) if result.data else 0

    def get_user_active_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active sessions for a user."""
        result = self.client.table('user_sessions').select(
            'id, device_name, ip_address, created_at, last_activity'
        ).eq('user_id', user_id).eq('is_active', True).gt(
            'expires_at', datetime.now().isoformat()
        ).order('last_activity', desc=True).execute()
        return result.data

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        result = self.client.table('user_sessions').delete().lt(
            'expires_at', datetime.now().isoformat()
        ).execute()
        return len(result.data) if result.data else 0

    # INVITE CODES
    def create_invite_code(self, family_circle_id: int, created_by: int,
                           expiry_hours: int = 72, max_uses: int = 10) -> Dict[str, Any]:
        """Create an invite code with expiration."""
        code = str(uuid.uuid4())[:8].upper()
        deep_link_token = secrets.token_urlsafe(32)
        now = datetime.now()
        expires = now + timedelta(hours=expiry_hours)

        data = {
            'family_circle_id': family_circle_id,
            'code': code,
            'created_by': created_by,
            'created_at': now.isoformat(),
            'expires_at': expires.isoformat(),
            'max_uses': max_uses,
            'deep_link_token': deep_link_token
        }
        result = self.client.table('invite_codes').insert(data).execute()

        return {
            'id': result.data[0]['id'],
            'code': code,
            'deep_link_token': deep_link_token,
            'expires_at': expires.isoformat(),
            'max_uses': max_uses
        }

    def get_invite_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get invite code if valid."""
        result = self.client.table('invite_codes').select(
            '*, family_circles(name)'
        ).eq('code', code.upper()).eq('is_active', True).gt(
            'expires_at', datetime.now().isoformat()
        ).execute()

        if result.data and result.data[0]['current_uses'] < result.data[0]['max_uses']:
            row = result.data[0]
            row['circle_name'] = row['family_circles']['name'] if row['family_circles'] else None
            return row
        return None

    def get_invite_by_deep_link(self, token: str) -> Optional[Dict[str, Any]]:
        """Get invite code by deep link token."""
        result = self.client.table('invite_codes').select(
            '*, family_circles(name)'
        ).eq('deep_link_token', token).eq('is_active', True).gt(
            'expires_at', datetime.now().isoformat()
        ).execute()

        if result.data and result.data[0]['current_uses'] < result.data[0]['max_uses']:
            row = result.data[0]
            row['circle_name'] = row['family_circles']['name'] if row['family_circles'] else None
            return row
        return None

    def use_invite_code(self, code: str, user_id: int, relationship: str = 'family_member') -> bool:
        """Use an invite code to join a family circle."""
        invite = self.get_invite_code(code)
        if not invite:
            return False

        # Increment usage count
        self.client.table('invite_codes').update({
            'current_uses': invite['current_uses'] + 1
        }).eq('code', code.upper()).execute()

        # Add member to circle
        try:
            member_data = {
                'family_circle_id': invite['family_circle_id'],
                'user_id': user_id,
                'relationship': relationship,
                'permissions': ['view', 'set_reminders'],
                'joined_date': datetime.now().isoformat()
            }
            self.client.table('family_members').insert(member_data).execute()
            return True
        except Exception:
            return False

    def deactivate_invite_code(self, code: str) -> bool:
        """Deactivate an invite code."""
        self.client.table('invite_codes').update({'is_active': False}).eq('code', code.upper()).execute()
        return True

    # LOGIN ATTEMPTS
    def record_login_attempt(self, identifier: str, attempt_type: str, success: bool,
                             ip_address: str = None, user_agent: str = None) -> int:
        """Record a login attempt."""
        data = {
            'identifier': identifier,
            'attempt_type': attempt_type,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.now().isoformat()
        }
        result = self.client.table('login_attempts').insert(data).execute()
        return result.data[0]['id']

    def get_recent_failed_attempts(self, identifier: str, minutes: int = 15) -> int:
        """Get count of failed login attempts in the last X minutes."""
        since = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        result = self.client.table('login_attempts').select('id').eq(
            'identifier', identifier
        ).eq('success', False).gt('timestamp', since).execute()
        return len(result.data)

    def set_lockout(self, identifier: str, lockout_minutes: int = 30) -> bool:
        """Set lockout for an identifier."""
        lockout_until = (datetime.now() + timedelta(minutes=lockout_minutes)).isoformat()
        # Get the most recent attempt
        result = self.client.table('login_attempts').select('id').eq(
            'identifier', identifier
        ).order('timestamp', desc=True).limit(1).execute()

        if result.data:
            self.client.table('login_attempts').update({
                'lockout_until': lockout_until
            }).eq('id', result.data[0]['id']).execute()
        return True

    def is_locked_out(self, identifier: str) -> bool:
        """Check if identifier is currently locked out."""
        result = self.client.table('login_attempts').select('lockout_until').eq(
            'identifier', identifier
        ).not_.is_('lockout_until', 'null').order('timestamp', desc=True).limit(1).execute()

        if result.data and result.data[0]['lockout_until']:
            return result.data[0]['lockout_until'] > datetime.now().isoformat()
        return False

    def cleanup_old_login_attempts(self, days: int = 30) -> int:
        """Remove old login attempts."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        result = self.client.table('login_attempts').delete().lt('timestamp', since).execute()
        return len(result.data) if result.data else 0
