-- =============================================================================
-- MEDSYNC - Supabase Database Schema
-- =============================================================================
-- Run this in Supabase SQL Editor:
-- 1. Go to your Supabase Dashboard
-- 2. Click "SQL Editor" in the left sidebar
-- 3. Click "New Query"
-- 4. Paste this entire file
-- 5. Click "Run"
-- =============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    age INTEGER,
    role TEXT DEFAULT 'patient',
    phone TEXT,
    created_date TIMESTAMPTZ DEFAULT NOW(),
    phone_verified BOOLEAN DEFAULT FALSE,
    primary_auth_method TEXT DEFAULT 'phone',
    account_status TEXT DEFAULT 'active',
    last_login TIMESTAMPTZ
);

-- Family circles table
CREATE TABLE IF NOT EXISTS family_circles (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    invite_code TEXT UNIQUE,
    created_by BIGINT REFERENCES users(id),
    created_date TIMESTAMPTZ DEFAULT NOW()
);

-- Family members relationship table
CREATE TABLE IF NOT EXISTS family_members (
    id BIGSERIAL PRIMARY KEY,
    family_circle_id BIGINT REFERENCES family_circles(id),
    user_id BIGINT REFERENCES users(id),
    relationship TEXT,
    permissions JSONB DEFAULT '["view", "set_reminders"]',
    joined_date TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(family_circle_id, user_id)
);

-- Medications table
CREATE TABLE IF NOT EXISTS medications (
    id BIGSERIAL PRIMARY KEY,
    patient_id BIGINT REFERENCES users(id),
    managed_by BIGINT REFERENCES users(id),
    name TEXT NOT NULL,
    dosage TEXT NOT NULL,
    frequency TEXT NOT NULL,
    times JSONB NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_date TIMESTAMPTZ DEFAULT NOW()
);

-- Dose logs table
CREATE TABLE IF NOT EXISTS dose_logs (
    id BIGSERIAL PRIMARY KEY,
    patient_id BIGINT REFERENCES users(id),
    medication_name TEXT,
    scheduled_time TEXT,
    taken BOOLEAN,
    actual_time TEXT,
    date DATE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    logged_by BIGINT REFERENCES users(id)
);

-- Reminders table
CREATE TABLE IF NOT EXISTS reminders (
    id BIGSERIAL PRIMARY KEY,
    patient_id BIGINT REFERENCES users(id),
    created_by BIGINT REFERENCES users(id),
    medication_name TEXT,
    reminder_time TEXT,
    message TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMPTZ DEFAULT NOW()
);

-- User credentials (password-based auth)
CREATE TABLE IF NOT EXISTS user_credentials (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token TEXT,
    email_verification_expiry TIMESTAMPTZ,
    password_reset_token TEXT,
    password_reset_expiry TIMESTAMPTZ,
    created_date TIMESTAMPTZ DEFAULT NOW(),
    updated_date TIMESTAMPTZ DEFAULT NOW()
);

-- OTP verifications (phone-based auth)
CREATE TABLE IF NOT EXISTS otp_verifications (
    id BIGSERIAL PRIMARY KEY,
    phone TEXT NOT NULL,
    otp_hash TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    user_id BIGINT REFERENCES users(id),
    purpose TEXT DEFAULT 'login'
);

-- User sessions (secure token-based)
CREATE TABLE IF NOT EXISTS user_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    device_fingerprint TEXT,
    device_name TEXT,
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Enhanced invite codes with expiration
CREATE TABLE IF NOT EXISTS invite_codes (
    id BIGSERIAL PRIMARY KEY,
    family_circle_id BIGINT NOT NULL REFERENCES family_circles(id),
    code TEXT UNIQUE NOT NULL,
    created_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    max_uses INTEGER DEFAULT 1,
    current_uses INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    deep_link_token TEXT UNIQUE
);

-- Login attempts tracking (security/rate limiting)
CREATE TABLE IF NOT EXISTS login_attempts (
    id BIGSERIAL PRIMARY KEY,
    identifier TEXT NOT NULL,
    attempt_type TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    lockout_until TIMESTAMPTZ
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_medications_patient ON medications(patient_id);
CREATE INDEX IF NOT EXISTS idx_dose_logs_patient_date ON dose_logs(patient_id, date);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_verifications(phone);

-- =============================================================================
-- ENABLE ROW LEVEL SECURITY ON ALL TABLES
-- =============================================================================
-- Note: RLS is enabled but no policies are added yet.
-- You will need to add policies based on your authentication strategy.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE medications ENABLE ROW LEVEL SECURITY;
ALTER TABLE dose_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_circles ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE otp_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invite_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE login_attempts ENABLE ROW LEVEL SECURITY;
