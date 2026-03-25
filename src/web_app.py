#!/usr/bin/env python3
"""
Family Medication Dashboard
Web interface for family members to monitor and manage elderly patients' medications.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import sqlite3
import time

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database import MedicationDB
from models.family import FamilyCircleManager
from services.auth import AuthService
from services.notifications import NotificationService

# Page configuration
st.set_page_config(
    page_title="Family Medication Dashboard",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for green medical theme
st.markdown("""
<style>
    /* Main app background */
    .main .block-container {
        background: linear-gradient(135deg, #f8fffe 0%, #e8f5e8 100%);
        padding-top: 2rem;
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        color: #2d5a27;
        font-size: 2.8rem;
        font-weight: bold;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(45, 90, 39, 0.1);
    }
    
    /* Welcome styling */
    .welcome-header {
        text-align: center;
        color: #2d5a27;
        font-size: 3.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    
    .welcome-subheader {
        text-align: center;
        color: #4a7c59;
        font-size: 1.3rem;
        margin-bottom: 3rem;
        font-weight: 300;
    }
    
    /* Empty state styling */
    .empty-state {
        text-align: center;
        padding: 3rem 2rem;
        background: linear-gradient(145deg, #ffffff 0%, #f9fff9 100%);
        border-radius: 20px;
        border: 2px dashed #4a7c59;
        margin: 2rem 0;
    }
    
    .empty-state h3 {
        color: #2d5a27;
        font-size: 1.8rem;
        margin-bottom: 1rem;
    }
    
    .empty-state p {
        color: #4a7c59;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Feature cards */
    .feature-card {
        background: linear-gradient(145deg, #ffffff 0%, #f9fff9 100%);
        padding: 2rem;
        border-radius: 15px;
        border-left: 5px solid #4a7c59;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(74, 124, 89, 0.1);
        text-align: center;
    }
    
    /* Alert styling */
    .alert-warning {
        background: linear-gradient(145deg, #fff8e1 0%, #f9f1c4 100%);
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #ff9800;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(255, 152, 0, 0.1);
        color: #e65100;
    }
    
    .alert-success {
        background: linear-gradient(145deg, #e8f5e8 0%, #d4f4d4 100%);
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #4caf50;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(76, 175, 80, 0.1);
        color: #2e7d32;
    }
    
    /* Patient cards */
    .patient-card {
        border: 2px solid #c8e6c9;
        border-radius: 15px;
        padding: 1.8rem;
        margin: 1.2rem 0;
        background: linear-gradient(145deg, #ffffff 0%, #f9fff9 100%);
        box-shadow: 0 6px 20px rgba(74, 124, 89, 0.1);
        transition: all 0.3s ease;
    }
    
    .patient-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(74, 124, 89, 0.15);
        border-color: #4a7c59;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #2d5a27 0%, #4a7c59 100%);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(145deg, #66bb6a 0%, #4caf50 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(76, 175, 80, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(145deg, #4caf50 0%, #388e3c 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(76, 175, 80, 0.4);
    }
    
    /* Primary button */
    .primary-button {
        background: linear-gradient(145deg, #2d5a27 0%, #1b3d19 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 30px;
        font-size: 1.1rem;
        font-weight: bold;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    /* Metric containers */
    [data-testid="metric-container"] {
        background: linear-gradient(145deg, #ffffff 0%, #f1f8e9 100%);
        border: 2px solid #c8e6c9;
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(74, 124, 89, 0.08);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(145deg, #e8f5e8 0%, #d4f4d4 100%);
        border-radius: 10px;
        color: #2d5a27;
        font-weight: 600;
    }
    
    /* Chart containers */
    .js-plotly-plot {
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(74, 124, 89, 0.1);
    }
    
    /* Success message styling */
    .success-message {
        background: linear-gradient(145deg, #e8f5e8 0%, #d4f4d4 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #4caf50;
        color: #2e7d32;
        margin: 2rem 0;
        text-align: center;
        font-weight: bold;
    }
    
    /* Medication log card */
    .med-log-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #4a7c59;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def init_database():
    """Initialize database, family manager, and auth service."""
    if 'db' not in st.session_state:
        st.session_state.db = MedicationDB()
        st.session_state.family_manager = FamilyCircleManager(st.session_state.db)
        st.session_state.notification_service = NotificationService()
        st.session_state.auth_service = AuthService(
            st.session_state.db,
            st.session_state.notification_service
        )
    return st.session_state.db, st.session_state.family_manager

def get_auth_service():
    """Get the auth service instance."""
    init_database()
    return st.session_state.auth_service

def init_user_session():
    """Initialize user session variables."""
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'onboarding_complete' not in st.session_state:
        st.session_state.onboarding_complete = False
    if 'family_circles' not in st.session_state:
        st.session_state.family_circles = []
    if 'show_login' not in st.session_state:
        st.session_state.show_login = True
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False
    # New auth flow states
    if 'auth_step' not in st.session_state:
        st.session_state.auth_step = 'phone'  # 'phone', 'otp', 'complete_profile', 'email_login'
    if 'auth_phone' not in st.session_state:
        st.session_state.auth_phone = None
    if 'otp_sent_time' not in st.session_state:
        st.session_state.otp_sent_time = None
    if 'session_token' not in st.session_state:
        st.session_state.session_token = None
    if 'is_new_user' not in st.session_state:
        st.session_state.is_new_user = False

def show_login_screen():
    """Show Life360-style login screen with phone-first approach."""
    auth_step = st.session_state.get('auth_step', 'phone')

    if auth_step == 'phone':
        show_phone_login()
    elif auth_step == 'otp':
        show_otp_verification()
    elif auth_step == 'complete_profile':
        show_complete_profile()
    elif auth_step == 'email_login':
        show_email_login()
    else:
        show_phone_login()


def show_phone_login():
    """Show phone number login screen (Life360 style)."""
    st.markdown('<h1 class="welcome-header">🏥 Welcome to FamilyCare</h1>', unsafe_allow_html=True)
    st.markdown('<p class="welcome-subheader">Keep your loved ones healthy and connected</p>', unsafe_allow_html=True)

    st.markdown("### 📱 Sign in with your phone number")

    with st.form("phone_login_form"):
        phone = st.text_input(
            "Phone Number",
            placeholder="+1 (555) 123-4567",
            help="We'll send you a verification code"
        )

        submitted = st.form_submit_button("Continue with Phone", use_container_width=True, type="primary")

        if submitted:
            if phone:
                auth = get_auth_service()
                result = auth.request_otp(phone, purpose='login')

                if result['success']:
                    st.session_state.auth_phone = result['phone']
                    st.session_state.otp_sent_time = time.time()
                    st.session_state.auth_step = 'otp'
                    st.success(result['message'])
                    st.rerun()
                else:
                    st.error(result['error'])
            else:
                st.error("Please enter your phone number")

    st.markdown("---")
    st.markdown('<p style="text-align: center; color: #666;">or</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📧 Use Email Instead", use_container_width=True):
            st.session_state.auth_step = 'email_login'
            st.rerun()
    with col2:
        if st.button("📝 Create Account", use_container_width=True):
            st.session_state.show_login = False
            st.session_state.show_register = True
            st.rerun()

    # Demo options
    st.markdown("---")
    with st.expander("🔧 Demo Options", expanded=False):
        st.markdown("**For demo/portfolio purposes:**")
        st.info("💡 In demo mode, OTP codes are logged to console. Check terminal for the code.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 Skip Login (Guest Mode)", type="secondary"):
                st.session_state.show_login = False
                st.rerun()
        with col2:
            if st.button("🗑️ Reset All Data", type="secondary"):
                db_path = "data/medications.db"
                if os.path.exists(db_path):
                    os.remove(db_path)
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.success("✅ All data cleared!")
                    st.rerun()


def show_otp_verification():
    """Show OTP verification screen."""
    st.markdown('<h1 class="welcome-header">🔐 Verify Your Phone</h1>', unsafe_allow_html=True)

    phone = st.session_state.auth_phone
    phone_display = f"***-***-{phone[-4:]}" if phone and len(phone) >= 4 else "your phone"
    st.markdown(f'<p class="welcome-subheader">We sent a 6-digit code to {phone_display}</p>', unsafe_allow_html=True)

    # Calculate time remaining
    sent_time = st.session_state.get('otp_sent_time', time.time())
    elapsed = time.time() - sent_time
    remaining = max(0, 300 - elapsed)  # 5 minutes = 300 seconds

    if remaining > 0:
        mins, secs = divmod(int(remaining), 60)
        st.info(f"⏱️ Code expires in {mins}:{secs:02d}")
    else:
        st.warning("⚠️ Code may have expired. Request a new one.")

    with st.form("otp_form"):
        otp_code = st.text_input(
            "Verification Code",
            max_chars=6,
            placeholder="Enter 6-digit code",
            help="Check your SMS messages"
        )

        col1, col2 = st.columns(2)
        with col1:
            verify_submitted = st.form_submit_button("✅ Verify", use_container_width=True, type="primary")
        with col2:
            back_submitted = st.form_submit_button("← Back", use_container_width=True)

        if verify_submitted:
            if otp_code and len(otp_code) == 6:
                auth = get_auth_service()
                result = auth.verify_otp(phone, otp_code)

                if result['success']:
                    if result.get('is_new_user'):
                        # New user - need to complete profile
                        st.session_state.is_new_user = True
                        st.session_state.auth_step = 'complete_profile'
                        st.success("✅ Phone verified! Let's set up your profile.")
                        st.rerun()
                    else:
                        # Existing user - log them in
                        user = result['user']
                        st.session_state.session_token = result['session_token']
                        st.session_state.user_profile = {
                            'id': user['id'],
                            'name': user['name'],
                            'email': user.get('email', ''),
                            'age': user.get('age'),
                            'type': user.get('role', 'patient'),
                            'phone': user.get('phone', ''),
                            'relationship': 'family_member'
                        }
                        db, _ = init_database()
                        user_circles = db.get_user_family_circles(user['id'])
                        st.session_state.onboarding_complete = len(user_circles) > 0
                        st.session_state.show_login = False
                        st.session_state.auth_step = 'phone'
                        st.success(f"✅ Welcome back, {user['name']}!")
                        st.rerun()
                else:
                    st.error(result['error'])
            else:
                st.error("Please enter the 6-digit code")

        if back_submitted:
            st.session_state.auth_step = 'phone'
            st.rerun()

    # Resend option
    st.markdown("---")
    if remaining <= 0 or elapsed > 30:  # Allow resend after 30 seconds
        if st.button("📲 Resend Code", use_container_width=True):
            auth = get_auth_service()
            result = auth.request_otp(phone, purpose='login')
            if result['success']:
                st.session_state.otp_sent_time = time.time()
                st.success("✅ New code sent!")
                st.rerun()
            else:
                st.error(result['error'])
    else:
        wait_time = 30 - int(elapsed)
        st.markdown(f"<p style='text-align:center; color:#666;'>Resend available in {wait_time}s</p>", unsafe_allow_html=True)


def show_complete_profile():
    """Show profile completion form for new users after OTP verification."""
    st.markdown('<h1 class="welcome-header">👤 Complete Your Profile</h1>', unsafe_allow_html=True)
    st.markdown('<p class="welcome-subheader">Just a few more details to get started</p>', unsafe_allow_html=True)

    phone = st.session_state.auth_phone

    with st.form("complete_profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Full Name *", placeholder="Enter your full name")
            email = st.text_input("Email (optional)", placeholder="your.email@example.com")

        with col2:
            age = st.number_input("Age", min_value=1, max_value=120, value=30)
            user_type = st.selectbox(
                "I am a:",
                ["family_member", "patient"],
                format_func=lambda x: "Family Member (caring for someone)" if x == "family_member" else "Patient (managing my own health)"
            )

        st.markdown("---")
        st.markdown("**Optional: Set a password for email login**")
        st.caption("This allows you to also sign in with email & password")

        col1, col2 = st.columns(2)
        with col1:
            password = st.text_input("Password (optional)", type="password", placeholder="At least 8 characters")
        with col2:
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password")

        submitted = st.form_submit_button("🎯 Create My Account", use_container_width=True, type="primary")

        if submitted:
            if name:
                # Validate password if provided
                if password:
                    if password != confirm_password:
                        st.error("❌ Passwords do not match")
                        st.stop()
                    auth = get_auth_service()
                    is_strong, errors = auth.validate_password_strength(password)
                    if not is_strong:
                        st.error(f"❌ {errors[0]}")
                        st.stop()

                auth = get_auth_service()
                result = auth.complete_phone_registration(
                    phone=phone,
                    name=name,
                    email=email if email else None,
                    password=password if password else None,
                    age=age,
                    role=user_type
                )

                if result['success']:
                    user = result['user']
                    st.session_state.session_token = result['session_token']
                    st.session_state.user_profile = {
                        'id': user['id'],
                        'name': user['name'],
                        'email': user.get('email', ''),
                        'age': user.get('age'),
                        'type': user.get('role', 'patient'),
                        'phone': user.get('phone', ''),
                        'relationship': 'family_member' if user_type == 'family_member' else 'patient'
                    }
                    st.session_state.show_login = False
                    st.session_state.onboarding_complete = False
                    st.session_state.auth_step = 'phone'
                    st.session_state.is_new_user = False
                    st.success(f"✅ Welcome to FamilyCare, {name}!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(result['error'])
            else:
                st.error("Please enter your name")

    if st.button("← Back"):
        st.session_state.auth_step = 'phone'
        st.rerun()


def show_email_login():
    """Show email/password login screen."""
    st.markdown('<h1 class="welcome-header">🏥 Sign In with Email</h1>', unsafe_allow_html=True)
    st.markdown('<p class="welcome-subheader">Use your email and password</p>', unsafe_allow_html=True)

    with st.form("email_login_form"):
        email = st.text_input("Email Address", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        col1, col2 = st.columns(2)
        with col1:
            login_submitted = st.form_submit_button("🔑 Sign In", use_container_width=True, type="primary")
        with col2:
            back_submitted = st.form_submit_button("← Back to Phone", use_container_width=True)

        if login_submitted:
            if email and password:
                auth = get_auth_service()
                result = auth.login_with_email(email, password)

                if result['success']:
                    user = result['user']
                    st.session_state.session_token = result['session_token']
                    st.session_state.user_profile = {
                        'id': user['id'],
                        'name': user['name'],
                        'email': user.get('email', ''),
                        'age': user.get('age'),
                        'type': user.get('role', 'patient'),
                        'phone': user.get('phone', ''),
                        'relationship': 'family_member'
                    }
                    db, _ = init_database()
                    user_circles = db.get_user_family_circles(user['id'])
                    st.session_state.onboarding_complete = len(user_circles) > 0
                    st.session_state.show_login = False
                    st.session_state.auth_step = 'phone'
                    st.success(f"✅ Welcome back, {user['name']}!")
                    st.rerun()
                else:
                    st.error(result['error'])
            else:
                st.error("Please enter email and password")

        if back_submitted:
            st.session_state.auth_step = 'phone'
            st.rerun()

    st.markdown("---")

    # Forgot password
    with st.expander("🔑 Forgot Password?"):
        with st.form("forgot_password_form"):
            reset_email = st.text_input("Enter your email address", key="reset_email")
            if st.form_submit_button("Send Reset Link"):
                if reset_email:
                    auth = get_auth_service()
                    result = auth.request_password_reset(reset_email)
                    st.success(result['message'])
                else:
                    st.error("Please enter your email address")

    # Demo options
    with st.expander("🔧 Demo Options", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 Skip Login (Guest)", type="secondary", key="guest_email"):
                st.session_state.show_login = False
                st.session_state.auth_step = 'phone'
                st.rerun()
        with col2:
            if st.button("🗑️ Reset All Data", type="secondary", key="reset_email_page"):
                db_path = "data/medications.db"
                if os.path.exists(db_path):
                    os.remove(db_path)
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.success("✅ All data cleared!")
                    st.rerun()

def show_register_screen():
    """Show registration screen with phone-first approach (Life360 style)."""
    st.markdown('<h1 class="welcome-header">🏥 Join FamilyCare</h1>', unsafe_allow_html=True)
    st.markdown('<p class="welcome-subheader">Create your account to start managing family health</p>', unsafe_allow_html=True)

    if st.button("← Back to Sign In"):
        st.session_state.show_register = False
        st.session_state.show_login = True
        st.session_state.auth_step = 'phone'
        st.rerun()

    # Registration options
    st.markdown("### Choose how to register:")

    tab1, tab2 = st.tabs(["📱 Phone (Recommended)", "📧 Email"])

    with tab1:
        st.markdown("#### Register with Phone Number")
        st.caption("Quick and secure - we'll verify with a text message")

        with st.form("register_phone_form"):
            phone = st.text_input(
                "Phone Number *",
                placeholder="+1 (555) 123-4567",
                help="We'll send a verification code to this number"
            )

            submitted = st.form_submit_button("📲 Send Verification Code", use_container_width=True, type="primary")

            if submitted:
                if phone:
                    auth = get_auth_service()
                    # Check if phone already registered
                    db, _ = init_database()
                    existing = db.get_user_by_phone(auth.normalize_phone(phone))
                    if existing:
                        st.error("❌ This phone number is already registered. Try signing in instead.")
                    else:
                        result = auth.request_otp(phone, purpose='register')
                        if result['success']:
                            st.session_state.auth_phone = result['phone']
                            st.session_state.otp_sent_time = time.time()
                            st.session_state.show_register = False
                            st.session_state.show_login = True
                            st.session_state.auth_step = 'otp'
                            st.session_state.is_new_user = True
                            st.success(result['message'])
                            st.rerun()
                        else:
                            st.error(result['error'])
                else:
                    st.error("Please enter your phone number")

    with tab2:
        st.markdown("#### Register with Email")
        st.caption("Traditional email and password registration")

        with st.form("register_email_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Full Name *", placeholder="Enter your full name", key="reg_name")
                email = st.text_input("Email Address *", placeholder="your.email@example.com", key="reg_email")
                password = st.text_input("Password *", type="password", placeholder="At least 8 characters", key="reg_pass")

            with col2:
                age = st.number_input("Age", min_value=1, max_value=120, value=30, key="reg_age")
                phone = st.text_input("Phone (optional)", placeholder="+1 (555) 123-4567", key="reg_phone_opt")
                confirm_password = st.text_input("Confirm Password *", type="password", placeholder="Confirm password", key="reg_confirm")

            user_type = st.selectbox(
                "I am a:",
                ["family_member", "patient"],
                format_func=lambda x: "Family Member (caring for someone)" if x == "family_member" else "Patient (managing my own health)",
                key="reg_type"
            )

            st.markdown("---")
            register_submitted = st.form_submit_button("🎯 Create Account", use_container_width=True, type="primary")

            if register_submitted:
                if name and email and password:
                    if password != confirm_password:
                        st.error("❌ Passwords do not match")
                    else:
                        auth = get_auth_service()
                        result = auth.register_with_email(
                            email=email,
                            password=password,
                            name=name,
                            phone=phone if phone else None,
                            age=age,
                            role=user_type
                        )

                        if result['success']:
                            user = result['user']
                            st.session_state.session_token = result['session_token']
                            st.session_state.user_profile = {
                                'id': user['id'],
                                'name': user['name'],
                                'email': user.get('email', ''),
                                'age': user.get('age'),
                                'type': user.get('role', 'patient'),
                                'phone': user.get('phone', ''),
                                'relationship': 'family_member' if user_type == 'family_member' else 'patient'
                            }
                            st.session_state.show_register = False
                            st.session_state.onboarding_complete = False
                            st.success(f"✅ Welcome to FamilyCare, {name}!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(result['error'])
                            if result.get('password_errors'):
                                for err in result['password_errors']:
                                    st.warning(f"• {err}")
                else:
                    st.error("Please fill in all required fields (Name, Email, Password)")

def show_welcome_screen():
    """Show welcome screen for guest mode (no login)."""
    st.markdown('<h1 class="welcome-header">🏥 Welcome to FamilyCare</h1>', unsafe_allow_html=True)
    st.markdown('<p class="welcome-subheader">Keep your loved ones healthy and connected with smart medication management</p>', unsafe_allow_html=True)
    
    st.info("🔄 **Guest Mode** - You're exploring FamilyCare without an account. Create an account to save your data!")
    
    # Feature showcase
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>👥 Family Circles</h3>
            <p>Connect with family members to monitor and support elderly care remotely</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>💊 Medication Tracking</h3>
            <p>Set up medication schedules and track adherence with smart reminders</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>📊 Health Insights</h3>
            <p>View detailed analytics and receive alerts when attention is needed</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Getting started options
    st.markdown("## 🚀 Create Your Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### I'm a Family Member")
        st.markdown("I want to help monitor and manage a loved one's medications")
        if st.button("👨‍👩‍👧‍👦 Start as Family Member", key="family_member", use_container_width=True):
            st.session_state.user_type = "family_member"
            st.session_state.show_profile_setup = True
            st.rerun()
    
    with col2:
        st.markdown("### I'm a Patient")
        st.markdown("I want to manage my own medications and connect with family")
        if st.button("👵 Start as Patient", key="patient", use_container_width=True):
            st.session_state.user_type = "patient"
            st.session_state.show_profile_setup = True
            st.rerun()
    
    # Login option
    st.markdown("---")
    st.markdown("### 🔐 Already have an account?")
    if st.button("🔑 Sign In to Your Account", key="go_to_login", use_container_width=True):
        st.session_state.show_login = True
        st.rerun()

def show_profile_setup():
    """Show profile setup form."""
    user_type = st.session_state.get('user_type', 'family_member')
    
    st.markdown(f"# 👤 Set Up Your Profile")
    st.markdown(f"**Account Type:** {'Family Member' if user_type == 'family_member' else 'Patient'}")
    
    with st.form("profile_setup"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name *", placeholder="Enter your full name")
            email = st.text_input("Email Address *", placeholder="your.email@example.com")
        
        with col2:
            age = st.number_input("Age", min_value=1, max_value=120, value=30 if user_type == 'family_member' else 70)
            phone = st.text_input("Phone Number", placeholder="+1 (555) 123-4567")
        
        if user_type == 'family_member':
            relationship = st.selectbox("Your relationship to patients you'll monitor:", 
                                      ["Child", "Spouse", "Sibling", "Caregiver", "Other"])
        else:
            relationship = "patient"
        
        st.markdown("---")
        
        submitted = st.form_submit_button("🎯 Create My Profile", use_container_width=True)
        
        if submitted:
            if name and email:
                # Create user profile
                db, family_manager = init_database()
                
                # Check if email already exists
                existing_user = db.get_user_by_email(email)
                if existing_user:
                    st.error(f"❌ An account with email {email} already exists. Please use a different email or contact support.")
                    st.info("💡 For this demo, you can use a different email address to create a new profile.")
                else:
                    try:
                        user_id = db.add_user(name, email, age, user_type, phone)
                        
                        st.session_state.user_profile = {
                            'id': user_id,
                            'name': name,
                            'email': email,
                            'age': age,
                            'type': user_type,
                            'phone': phone,
                            'relationship': relationship
                        }
                        
                        st.session_state.show_profile_setup = False
                        st.session_state.profile_created = True
                        st.success(f"✅ Welcome, {name}! Your profile has been created.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error creating profile: {str(e)}")
                        st.info("💡 Please try with a different email address.")
            else:
                st.error("Please fill in your name and email address.")

def show_getting_started():
    """Show getting started options after profile creation."""
    user = st.session_state.user_profile
    
    st.markdown(f"# 🎉 Welcome, {user['name']}!")
    
    if user['type'] == 'family_member':
        st.markdown("## 👨‍👩‍👧‍👦 Create Your First Family Circle")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            <div class="empty-state">
                <h3>🏠 Start Your Family Care Journey</h3>
                <p>Create a family circle to begin monitoring and supporting your loved one's health. You can invite family members and add patients to track their medications together.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("🆕 Create Family Circle", key="create_circle", use_container_width=True):
                st.session_state.show_create_circle = True
                st.rerun()
            
            st.markdown("**OR**")
            
            if st.button("🔗 Join Existing Circle", key="join_circle", use_container_width=True):
                st.session_state.show_join_circle = True
                st.rerun()
    
    else:  # patient
        st.markdown("## 💊 Set Up Your Medication Profile")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            <div class="empty-state">
                <h3>🩺 Get Started with Your Health</h3>
                <p>Add your medications and connect with family members who can help support your health journey. They'll be able to monitor your progress and provide assistance when needed.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("💊 Add My Medications", key="add_medications", use_container_width=True):
                st.session_state.show_add_patient_medication = True
                st.rerun()
            
            st.markdown("**OR**")
            
            if st.button("👨‍👩‍👧‍👦 Connect with Family", key="connect_family", use_container_width=True):
                st.session_state.show_join_circle = True
                st.rerun()

def show_create_family_circle():
    """Show family circle creation form."""
    st.markdown("# 🏠 Create Your Family Circle")
    
    if st.button("← Back"):
        st.session_state.show_create_circle = False
        st.rerun()
    
    with st.form("create_family_circle"):
        circle_name = st.text_input("Family Circle Name *", placeholder="e.g., Johnson Family Care")
        description = st.text_area("Description (Optional)", placeholder="Brief description of your family circle...")
        
        st.markdown("---")
        st.markdown("**👥 Who will you be monitoring?**")
        add_patient_now = st.checkbox("I want to add a patient now (elderly family member)")
        
        if add_patient_now:
            st.markdown("**Patient Information:**")
            col1, col2 = st.columns(2)
            with col1:
                patient_name = st.text_input("Patient Name", placeholder="Enter patient's full name")
                patient_age = st.number_input("Patient Age", min_value=1, max_value=120, value=75)
            with col2:
                patient_email = st.text_input("Patient Email (Optional)", placeholder="patient@email.com")
                patient_phone = st.text_input("Patient Phone", placeholder="+1 (555) 123-4567")
            
            relationship = st.selectbox("Your relationship to this patient:", 
                                      ["Parent", "Grandparent", "Spouse", "Other Family", "Care Recipient"])
        
        submitted = st.form_submit_button("🎯 Create Family Circle", use_container_width=True)
        
        if submitted:
            if circle_name:
                db, family_manager = init_database()
                user = st.session_state.user_profile
                
                # Create family circle
                circle_id, invite_code = family_manager.create_family_circle(circle_name, user['id'])
                
                # Add patient if specified
                patient_id = None
                if add_patient_now and patient_name:
                    patient_id = db.add_user(patient_name, patient_email or None, patient_age, "patient", patient_phone)
                    db.join_family_circle(invite_code, patient_id, "patient")
                
                # Store in session
                st.session_state.family_circles.append({
                    'id': circle_id,
                    'name': circle_name,
                    'invite_code': invite_code,
                    'patient_id': patient_id
                })
                
                st.session_state.show_create_circle = False
                st.session_state.circle_created = True
                st.session_state.new_invite_code = invite_code
                st.rerun()
            else:
                st.error("Please enter a family circle name.")

def show_circle_created_success():
    """Show success message after circle creation."""
    invite_code = st.session_state.get('new_invite_code')
    
    st.markdown("""
    <div class="success-message">
        <h2>🎉 Family Circle Created Successfully!</h2>
        <p>Your family care network is now active</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📨 Invite Family Members")
        st.info(f"""
        **Invite Code:** `{invite_code}`
        
        Share this code with family members so they can join your care circle and help monitor medications together.
        """)
    
    with col2:
        st.markdown("### 🎯 Next Steps")
        if st.button("💊 Add Medications", key="add_first_med", use_container_width=True):
            st.session_state.show_medication_setup = True
            st.session_state.circle_created = False
            st.rerun()
        
        if st.button("📊 Go to Dashboard", key="go_dashboard", use_container_width=True):
            st.session_state.circle_created = False
            st.session_state.onboarding_complete = True
            st.rerun()

def show_join_family_circle():
    """Show join family circle form."""
    st.markdown("# 🔗 Join a Family Circle")
    
    if st.button("← Back"):
        st.session_state.show_join_circle = False
        st.rerun()
    
    st.markdown("Enter the invite code shared by your family member:")
    
    with st.form("join_family_circle"):
        invite_code = st.text_input("Invite Code *", placeholder="e.g., A1B2C3D4", max_chars=8)
        
        submitted = st.form_submit_button("🎯 Join Family Circle", use_container_width=True)
        
        if submitted:
            if invite_code:
                db, family_manager = init_database()
                user = st.session_state.user_profile
                
                # Attempt to join circle
                success = db.join_family_circle(invite_code.upper(), user['id'], user.get('relationship', 'family_member'))
                
                if success:
                    st.success("✅ Successfully joined the family circle!")
                    st.session_state.show_join_circle = False
                    st.session_state.onboarding_complete = True
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Invalid invite code or you're already a member of this circle.")
            else:
                st.error("Please enter an invite code.")

def show_medication_logging():
    """Show interface for logging today's medications."""
    db, family_manager = init_database()
    user = st.session_state.user_profile
    
    st.markdown("# 💊 Log Today's Medications")
    
    if st.button("← Back to Dashboard"):
        st.session_state.show_medication_logging = False
        st.rerun()
    
    st.markdown("---")
    
    # Get today's schedule
    if user['type'] == 'patient':
        patient_id = user['id']
        patient_name = user['name']
    else:
        # For family members, let them choose which patient
        circles = db.get_user_family_circles(user['id'])
        if not circles:
            st.warning("No family circles found.")
            return
        
        # Get all patients from circles
        patients_status = db.get_family_patients_status(user['id'])
        if not patients_status:
            st.info("No patients to log medications for.")
            return
        
        # Select patient
        patient_names = {p['id']: p['name'] for p in patients_status}
        selected_patient_id = st.selectbox(
            "Select Patient:",
            options=list(patient_names.keys()),
            format_func=lambda x: patient_names[x]
        )
        patient_id = selected_patient_id
        patient_name = patient_names[patient_id]
    
    # Get medications for selected patient
    medications = db.get_patient_medications(patient_id)
    
    if not medications:
        st.info(f"No medications scheduled for {patient_name}.")
        return
    
    # Display today's schedule
    st.markdown(f"## 📅 Today's Schedule for {patient_name}")
    st.markdown(f"**Date:** {datetime.now().strftime('%A, %B %d, %Y')}")
    
    today = datetime.now().date().isoformat()
    
    for medication in medications:
        with st.container():
            st.markdown(f"### 💊 {medication['name']} - {medication['dosage']}")
            
            if medication.get('notes'):
                st.info(f"📝 {medication['notes']}")
            
            for med_time in medication['times']:
                # Check if already logged today
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT taken, actual_time FROM dose_logs
                        WHERE patient_id = ? AND medication_name = ? 
                        AND scheduled_time = ? AND date = ?
                    """, (patient_id, medication['name'], med_time, today))
                    existing_log = cursor.fetchone()
                
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                
                with col1:
                    st.write(f"⏰ **Scheduled:** {med_time}")
                
                with col2:
                    if existing_log:
                        if existing_log[0]:
                            st.success(f"✅ Taken at {existing_log[1]}")
                        else:
                            st.error(f"❌ Marked as missed")
                    else:
                        current_time = datetime.now().time()
                        scheduled_time_obj = datetime.strptime(med_time, "%H:%M").time()
                        
                        if current_time > scheduled_time_obj:
                            st.warning("⏳ Overdue")
                        else:
                            st.info("⏳ Upcoming")
                
                with col3:
                    if not existing_log:
                        if st.button(f"✅", key=f"taken_{medication['id']}_{med_time}", help="Mark as taken"):
                            db.log_dose(
                                patient_id,
                                medication['name'],
                                med_time,
                                True,
                                user['id'],
                                datetime.now().strftime("%H:%M")
                            )
                            st.success(f"Logged {medication['name']} as taken!")
                            st.rerun()
                
                with col4:
                    if not existing_log:
                        if st.button(f"❌", key=f"missed_{medication['id']}_{med_time}", help="Mark as missed"):
                            db.log_dose(
                                patient_id,
                                medication['name'],
                                med_time,
                                False,
                                user['id'],
                                datetime.now().strftime("%H:%M")
                            )
                            st.warning(f"Logged {medication['name']} as missed.")
                            st.rerun()
            
            st.markdown("---")
    
    # Show today's adherence
    st.markdown("### 📊 Today's Progress")
    
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute("""
            SELECT COUNT(*) as total, SUM(taken) as taken_count
            FROM dose_logs
            WHERE patient_id = ? AND date = ?
        """, (patient_id, today))
        result = cursor.fetchone()
        
        if result[0] > 0:
            total = result[0]
            taken = result[1] if result[1] else 0
            adherence = (taken / total) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Doses Today", total)
            with col2:
                st.metric("Taken", taken)
            with col3:
                color = "🟢" if adherence >= 90 else "🟡" if adherence >= 70 else "🔴"
                st.metric(f"{color} Today's Adherence", f"{adherence:.0f}%")
        else:
            st.info("No doses logged yet today.")

def show_family_dashboard():
    """Display family overview dashboard with user's real data."""
    db, family_manager = init_database()
    user = st.session_state.user_profile
    
    st.markdown('<h1 class="main-header">🏥 Family Medication Dashboard</h1>', unsafe_allow_html=True)
    
    # Get user's family circles
    user_circles = db.get_user_family_circles(user['id'])
    
    if not user_circles:
        # Empty state - no family circles
        st.markdown("""
        <div class="empty-state">
            <h3>🏠 No Family Circles Yet</h3>
            <p>Create your first family circle to start monitoring medications and connecting with family members.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🆕 Create Your First Family Circle", key="create_first", use_container_width=True):
                st.session_state.show_create_circle = True
                st.rerun()
        
        return
    
    # Get dashboard data for the user
    dashboard_data = family_manager.get_family_dashboard_data(user['id'])
    
    if dashboard_data['total_patients'] == 0:
        # Has circles but no patients
        st.markdown("## 👥 Your Family Circles")
        for circle in user_circles:
            st.markdown(f"### 🏠 {circle['name']}")
            st.info(f"**Invite Code:** `{circle['invite_code']}` - Share this with family members")
        
        st.markdown("""
        <div class="empty-state">
            <h3>👵 No Patients Added Yet</h3>
            <p>Add elderly family members to start tracking their medications and health progress.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("👵 Add Your First Patient", key="add_first_patient", use_container_width=True):
                st.session_state.show_add_patient = True
                st.rerun()
        
        return
    
    # Show full dashboard with data
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="👵 Patients Monitoring",
            value=dashboard_data['total_patients']
        )
    
    with col2:
        adherence = dashboard_data['average_adherence']
        color = "🟢" if adherence >= 90 else "🟡" if adherence >= 70 else "🔴"
        st.metric(
            label=f"{color} Average Adherence",
            value=f"{adherence}%" if adherence > 0 else "No data"
        )
    
    with col3:
        st.metric(
            label="⚠️ Need Attention",
            value=dashboard_data['patients_needing_attention']
        )
    
    with col4:
        st.metric(
            label="👨‍👩‍👧‍👦 Family Circles",
            value=len(dashboard_data['family_circles'])
        )
    
    # Alerts section
    if dashboard_data['alerts']:
        st.markdown("## 🚨 Alerts & Notifications")
        for alert in dashboard_data['alerts']:
            if "low medication adherence" in alert:
                st.markdown(f'<div class="alert-warning">{alert}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-success">{alert}</div>', unsafe_allow_html=True)
    
    # Patient status cards
    st.markdown("## 👥 Patient Status Overview")
    
    for patient in dashboard_data['patients_status']:
        with st.expander(f"👵 {patient['name']} ({patient['age']} years old)", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💊 Medications", patient['total_medications'])
            
            with col2:
                adherence = patient['adherence_rate']
                color = "🟢" if adherence >= 90 else "🟡" if adherence >= 70 else "🔴"
                st.metric(f"{color} Adherence", f"{adherence:.1f}%" if adherence > 0 else "No data")
            
            with col3:
                st.metric("🏠 Family Circle", patient['family_circle_name'])
            
            # Get patient's medications
            medications = db.get_patient_medications(patient['id'])
            
            if medications:
                st.markdown("**Current Medications:**")
                med_data = []
                for med in medications:
                    med_data.append({
                        'Medication': med['name'],
                        'Dosage': med['dosage'],
                        'Times': ', '.join(med['times']),
                        'Notes': med['notes'] or 'None'
                    })
                
                st.dataframe(pd.DataFrame(med_data), use_container_width=True)
            else:
                st.info("No medications added yet for this patient.")
            
            # Quick actions
            st.markdown("**Quick Actions:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"📊 View Details", key=f"details_{patient['id']}"):
                    st.session_state['selected_patient'] = patient['id']
                    st.rerun()
            
            with col2:
                if st.button(f"💊 Add Medication", key=f"add_med_{patient['id']}"):
                    st.session_state['add_medication_for'] = patient['id']
                    st.rerun()
            
            with col3:
                if st.button(f"📝 Log Doses", key=f"log_{patient['id']}"):
                    st.session_state['show_medication_logging'] = True
                    st.rerun()

def show_patient_details():
    """Show detailed view for a specific patient."""
    if 'selected_patient' not in st.session_state:
        return
    
    db, family_manager = init_database()
    patient_id = st.session_state['selected_patient']
    
    # Get patient info
    users = db.get_users()
    patient = next((u for u in users if u['id'] == patient_id), None)
    
    if not patient:
        st.error("Patient not found")
        return
    
    st.markdown(f"# 📊 {patient['name']} - Detailed View")
    
    if st.button("← Back to Dashboard"):
        del st.session_state['selected_patient']
        st.rerun()
    
    # Create adherence chart
    st.markdown("## 📈 7-Day Adherence Trend")
    
    # Get real adherence data from database
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute("""
            SELECT date, 
                   COUNT(*) as total,
                   SUM(taken) as taken
            FROM dose_logs
            WHERE patient_id = ? AND date >= date('now', '-7 days')
            GROUP BY date
            ORDER BY date
        """, (patient_id,))
        
        logs = cursor.fetchall()
    
    if logs:
        dates = [datetime.fromisoformat(log[0]) for log in logs]
        adherence_data = [(log[2]/log[1]*100) if log[1] > 0 else 0 for log in logs]
    else:
        # Mock data if no logs
        dates = [datetime.now().date() - timedelta(days=x) for x in range(6, -1, -1)]
        adherence_data = [0] * 7
    
    fig = px.line(
        x=dates, 
        y=adherence_data,
        title="Daily Medication Adherence",
        labels={'x': 'Date', 'y': 'Adherence %'}
    )
    fig.update_traces(line_color='#4a7c59', line_width=4, marker_color='#66bb6a', marker_size=8)
    fig.update_layout(
        yaxis_range=[0, 100],
        plot_bgcolor='rgba(248, 255, 254, 0.8)',
        paper_bgcolor='rgba(255, 255, 255, 0.9)',
        title_font_color='#2d5a27',
        font_color='#2d5a27',
        title_font_size=18,
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Medication schedule
    st.markdown("## ⏰ Today's Medication Schedule")
    
    medications = db.get_patient_medications(patient_id)
    
    if medications:
        today = datetime.now().date().isoformat()
        schedule_data = []
        
        for med in medications:
            for time in med['times']:
                # Check if logged today
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT taken FROM dose_logs
                        WHERE patient_id = ? AND medication_name = ? 
                        AND scheduled_time = ? AND date = ?
                    """, (patient_id, med['name'], time, today))
                    log = cursor.fetchone()
                
                if log:
                    status = '✅ Taken' if log[0] else '❌ Missed'
                else:
                    status = '⏳ Pending'
                
                schedule_data.append({
                    'Time': time,
                    'Medication': med['name'],
                    'Dosage': med['dosage'],
                    'Status': status
                })
        
        df = pd.DataFrame(schedule_data).sort_values('Time')
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No medications scheduled for this patient yet.")

def show_add_medication():
    """Show form to add medication for a patient."""
    if 'add_medication_for' not in st.session_state:
        return
    
    db, family_manager = init_database()
    patient_id = st.session_state['add_medication_for']
    
    # Get patient info
    users = db.get_users()
    patient = next((u for u in users if u['id'] == patient_id), None)
    
    if not patient:
        st.error("Patient not found")
        return
    
    st.markdown(f"# 💊 Add Medication for {patient['name']}")
    
    if st.button("← Back to Dashboard"):
        del st.session_state['add_medication_for']
        st.rerun()
    
    with st.form("add_medication_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            medication_name = st.text_input("Medication Name *", placeholder="e.g., Aspirin")
            dosage = st.text_input("Dosage *", placeholder="e.g., 81mg")
            
        with col2:
            frequency = st.selectbox("Frequency", ["daily", "twice_daily", "three_times_daily", "as_needed"])
            notes = st.text_area("Notes", placeholder="Special instructions...")
        
        st.markdown("**Medication Times:**")
        if frequency == "daily":
            time1 = st.time_input("Time", value=datetime.strptime("08:00", "%H:%M").time())
            times = [time1.strftime("%H:%M")]
        elif frequency == "twice_daily":
            col1, col2 = st.columns(2)
            with col1:
                time1 = st.time_input("Morning", value=datetime.strptime("08:00", "%H:%M").time())
            with col2:
                time2 = st.time_input("Evening", value=datetime.strptime("20:00", "%H:%M").time())
            times = [time1.strftime("%H:%M"), time2.strftime("%H:%M")]
        else:
            time1 = st.time_input("Time 1", value=datetime.strptime("08:00", "%H:%M").time())
            time2 = st.time_input("Time 2", value=datetime.strptime("14:00", "%H:%M").time())
            time3 = st.time_input("Time 3", value=datetime.strptime("20:00", "%H:%M").time())
            times = [time1.strftime("%H:%M"), time2.strftime("%H:%M"), time3.strftime("%H:%M")]
        
        submitted = st.form_submit_button("💊 Add Medication")
        
        if submitted:
            if medication_name and dosage:
                user = st.session_state.user_profile
                family_manager.add_medication_for_patient(
                    user['id'], patient_id,
                    {
                        'name': medication_name,
                        'dosage': dosage,
                        'frequency': frequency,
                        'times': times,
                        'notes': notes
                    }
                )
                st.success(f"✅ Added {medication_name} for {patient['name']}")
                st.info("💡 Automated reminders will be sent at scheduled times!")
                st.balloons()
                
                # Clear form and return to dashboard
                del st.session_state['add_medication_for']
                st.rerun()
            else:
                st.error("Please fill in medication name and dosage")

def main():
    """Main application with login and user onboarding flow."""
    init_user_session()
    
    # Show login/register screens if user not logged in
    if st.session_state.get('show_login', True) and not st.session_state.user_profile:
        show_login_screen()
        return
    
    if st.session_state.get('show_register', False):
        show_register_screen()
        return
    
    # If no user profile and not showing login, show welcome (guest mode)
    if not st.session_state.user_profile:
        show_welcome_screen()
        return
    
    # Handle various app screens for logged-in users
    if st.session_state.get('show_profile_setup'):
        show_profile_setup()
        return
    
    if st.session_state.get('show_create_circle'):
        show_create_family_circle()
        return
    
    if st.session_state.get('circle_created'):
        show_circle_created_success()
        return
    
    if st.session_state.get('show_join_circle'):
        show_join_family_circle()
        return
    
    # Check if user has completed onboarding
    if not st.session_state.onboarding_complete:
        show_getting_started()
        return
    
    # Show medication logging interface
    if st.session_state.get('show_medication_logging'):
        show_medication_logging()
        return
    
    # Show appropriate main screen
    if 'selected_patient' in st.session_state:
        show_patient_details()
    elif 'add_medication_for' in st.session_state:
        show_add_medication()
    else:
        show_family_dashboard()
    
    # Sidebar for logged-in users
    if st.session_state.user_profile:
        user = st.session_state.user_profile
        st.sidebar.title("🏠 Navigation")
        st.sidebar.markdown(f"**Welcome, {user['name']}!**")
        st.sidebar.markdown(f"*{user['type'].title()}*")
        st.sidebar.markdown(f"📧 {user['email']}")
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("## 🔗 Quick Actions")
        
        if st.sidebar.button("📝 Log Medications"):
            st.session_state.show_medication_logging = True
            st.rerun()
        
        if st.sidebar.button("🆕 Create New Circle"):
            st.session_state.show_create_circle = True
            st.rerun()
        
        if st.sidebar.button("🔗 Join Circle"):
            st.session_state.show_join_circle = True
            st.rerun()
        
        if st.sidebar.button("📞 Emergency Contact"):
            st.sidebar.error("Emergency features coming soon!")
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("## 👤 Account")
        
        if st.sidebar.button("🚪 Sign Out"):
            # Invalidate session token if exists
            if st.session_state.get('session_token'):
                auth = get_auth_service()
                auth.logout(st.session_state.session_token)
            # Clear user session but keep database
            st.session_state.user_profile = None
            st.session_state.session_token = None
            st.session_state.onboarding_complete = False
            st.session_state.show_login = True
            st.session_state.auth_step = 'phone'
            st.session_state.auth_phone = None
            # Clear other session states
            for key in list(st.session_state.keys()):
                if key.startswith(('show_', 'selected_', 'add_', 'circle_', 'family_')):
                    del st.session_state[key]
            st.success("👋 Signed out successfully!")
            st.rerun()
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Built with ❤️ for Family Care**")
        
        # Demo reset for portfolio presentations
        with st.sidebar.expander("🔧 Demo Tools", expanded=False):
            if st.sidebar.button("🔄 Reset App Data", type="secondary"):
                db_path = "data/medications.db"
                if os.path.exists(db_path):
                    os.remove(db_path)
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("🔄 App reset complete!")
                st.rerun()

if __name__ == "__main__":
    main()