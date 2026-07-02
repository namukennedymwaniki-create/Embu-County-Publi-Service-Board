import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, timedelta, date
import traceback
import plotly.express as px
import plotly.graph_objects as go
import io
import shutil
import psycopg2  
import os
import random
from dateutil.relativedelta import relativedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets  # ADD THIS - for generating secure tokens
import json  # ADD THIS - for handling JSON data
import requests  # ADD THIS - for API calls (if using SendGrid)

# =========================================================
# EMAIL FUNCTIONS
# =========================================================

def generate_otp():
    """Generate a 6-digit OTP"""
    import random
    return str(random.randint(100000, 999999))

def send_otp_email(recipient_email, otp, username, purpose="verification"):
    """
    Send OTP verification code to user's email
    
    Parameters:
    - recipient_email: User's email address
    - otp: 6-digit OTP code
    - username: User's username
    - purpose: 'verification' for new accounts, 'reset' for password reset
    """
    try:
        smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = st.secrets.get("SMTP_PORT", 587)
        sender_email = st.secrets.get("SMTP_USER")
        sender_password = st.secrets.get("SMTP_PASSWORD")
        
        if not sender_email or not sender_password:
            print("Email credentials not configured")
            return False
        
        # Set subject and body based on purpose
        if purpose == "verification":
            subject = "🔐 Verify Your Account - Embu County PSB"
            body = f"""
Dear {username},

Welcome to the Embu County Public Service Board HR System!

Your account has been created. To activate your account, please use the following One-Time Password (OTP):

🔑 {otp}

This OTP will expire in 15 minutes.

Once verified, you will be prompted to create your own password.

If you did not request this account, please ignore this email.

Regards,
Embu County Public Service Board
"""
        else:  # password reset
            subject = "🔐 Password Reset OTP - Embu County PSB"
            body = f"""
Dear {username},

You requested to reset your password for the Embu County Public Service Board HR System.

Your One-Time Password (OTP) is: {otp}

This OTP will expire in 10 minutes.

If you did not request this, please ignore this email and contact the administrator immediately.

Regards,
Embu County Public Service Board
"""
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ OTP email sent to {recipient_email} for {purpose}")
        return True
        
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False
  
# =========================================================
# ROLE PERMISSIONS DEFINITION
# =========================================================

ROLE_PERMISSIONS = {
    "Super Admin": {
        "menu": [
            "📊 Dashboard",
            "👥 Applicant Profile",
            "📝 Applicant Registration",
            "✏️ Edit Application",
            "⭐ Shortlist Management",
            "📊 Scoresheet",
            "👔 HR Functions",
            "📥 Import Excel",
            "📋 Records",
            "📈 Reports",
            "⭐ Review",
            "📤 Export Center",
            "✅ Data Quality",
            "🔒 Audit Trail",
            "💾 Backup & Restore",
            "🧪 Test Data",
            "⚙️ Settings",
            "👤 Users"
        ],
        "permissions": [
            "view_dashboard", "view_staff", "add_staff", "edit_staff", "delete_staff",
            "import_staff", "process_promotions", "manage_redesignation", "manage_contracts",
            "manage_translation", "manage_salary", "manage_leave", "manage_confirmation",
            "manage_discipline", "manage_acting", "view_reports", "export_data",
            "manage_users", "view_audit", "backup_restore", "system_settings", "test_data",
            "view_scoresheet", "edit_applications", "view_all_reports", "review_applicants"
        ]
    },
    "Admin": {
        "menu": [
            "📊 Dashboard",
            "👥 Applicant Profile",
            "📝 Applicant Registration",
            "✏️ Edit Application",
            "⭐ Shortlist Management",
            "📊 Scoresheet",
            "👔 HR Functions",
            "📥 Import Excel",
            "📋 Records",
            "📈 Reports",
            "📤 Export Center",
            "✅ Data Quality",
            "⚙️ Settings",
            "👤 Users"
        ],
        "permissions": [
            "view_dashboard", "view_staff", "add_staff", "edit_staff", "delete_staff",
            "import_staff", "process_promotions", "manage_redesignation", "manage_contracts",
            "manage_translation", "manage_salary", "manage_leave", "manage_confirmation",
            "manage_discipline", "manage_acting", "view_reports", "export_data",
            "manage_users", "system_settings", "view_scoresheet", "edit_applications"
        ]
    },
    "HR": {  # NEW ROLE
        "menu": [
            "👔 HR Functions"
        ],
        "permissions": [
            "view_hr_functions"
        ]
    },
    "User": {
        "menu": [
            "📊 Dashboard",
            "👥 Applicant Profile",
            "📝 Applicant Registration",
            "⭐ Shortlist Management",
            "👔 HR Functions",
            "📋 Records",
            "📤 Export Center"
        ],
        "permissions": [
            "view_dashboard", "view_staff", "add_staff",
            "import_staff", "view_reports"
        ]
    }
}
def get_user_menu():
    """Return menu items based on user role"""
    if "user" not in st.session_state or st.session_state.user is None:
        return []
    
    role = st.session_state.user.get("role", "User")
    
    # HR role only sees HR Functions
    if role == "HR":
        return ROLE_PERMISSIONS.get(role, {}).get("menu", [])
    
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["User"])["menu"]

def has_permission(permission):
    """Check if current user has specific permission"""
    if "user" not in st.session_state or st.session_state.user is None:
        return False
    
    role = st.session_state.user.get("role", "User")
    permissions = ROLE_PERMISSIONS.get(role, {}).get("permissions", [])
    return permission in permissions

def require_permission(permission):
    """Require specific permission - shows error if not authorized"""
    if not has_permission(permission):
        st.error(f"⛔ Access Denied. You don't have permission for this action.")
        st.stop()
    return True
# =========================================================
# WHATSAPP HR ASSISTANT CLASS
# =========================================================

class WhatsAppHRAssistant:
    def __init__(self):
        # Get configuration from secrets
        self.county_name = st.secrets.get("COUNTY_NAME", "Embu")
        self.hr_phone = st.secrets.get("HR_PHONE", "+254711536570")
        self.hr_email = st.secrets.get("HR_EMAIL", "namukennedymwaniki@gmail.com")
        self.hr_room = st.secrets.get("HR_ROOM", "Trade House, Second Floor")
        self.portal_url = st.secrets.get("APP_URL", "https://embucountypublicserviceboardsystem.streamlit.app")
        
        # Intent patterns
        self.intents = {
            "vacancies": ["1", "job", "vacancy", "vacancies", "apply", "application"],
            "policies": ["2", "policy", "leave", "promotion", "conduct", "pension", "hr"],
            "portal": ["3", "portal", "upload", "password", "reset", "claim", "login"],
            "menu": ["0", "menu", "back", "main menu"]
        }
    
    def process_message(self, phone_number, message):
        """Process incoming WhatsApp message and return response"""
        message_lower = message.lower().strip()
        
        # Check for PII (security guard)
        import re
        pii_patterns = [r'\b\d{8,}\b', r'password', r'bank', r'account']
        for pattern in pii_patterns:
            if re.search(pattern, message_lower):
                return self._get_security_warning()
        
        # Route intent
        intent = self._detect_intent(message_lower)
        
        if intent == "vacancies":
            response = self._handle_vacancies()
        elif intent == "policies":
            response = self._handle_policies(message_lower)
        elif intent == "portal":
            response = self._handle_portal(message_lower)
        elif intent == "menu":
            response = self._get_main_menu()
        else:
            response = self._get_fallback_response()
        
        # Save to database
        self._save_conversation(phone_number, message, response, intent)
        
        return response
    
    def _detect_intent(self, message):
        """Detect user intent from message"""
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in message:
                    return intent
        return None
    
    def _get_main_menu(self):
        return f"""Hello! 👋 Welcome to the *{self.county_name} County Public Service Board* HR Assistant.

How can I assist you today? Please reply with a number:

1️⃣ Job Vacancies & Applications
2️⃣ HR Policies (Leave, Promotion, Conduct, Pension)
3️⃣ HR Portal Support (Uploads, Password Reset, Claims)

Reply *0* at any time to return to this menu."""
    
    def _handle_vacancies(self):
        return f"""📋 *Job Vacancies & Applications*

*Current Open Positions*
All advertised positions are published on our official portal:

🔗 {self.portal_url}

*How to Apply*
1. Visit {self.portal_url}
2. Click on *'Applicant Registration'*
3. Fill in your personal details and qualifications
4. Upload required documents (ID, certificates, CV)
5. Submit — you'll receive a confirmation

*Application Status Check*
To check your status, please log in to the portal:
🔗 {self.portal_url} → *'Applicant Profile'*

For further assistance, contact the HR Registry:
📞 {self.hr_phone}
📧 {self.hr_email}

Reply *0* for the main menu."""
    
    def _handle_policies(self, message):
        if "leave" in message:
            return f"""🌴 *Leave Entitlements*

• *Annual Leave:* 30 working days per year
• *Sick Leave:* Up to 30 days on full pay, then 30 days on half pay
• *Maternity Leave:* 90 consecutive calendar days on full pay
• *Paternity Leave:* 14 days on full pay
• *Compassionate Leave:* Up to 3 days per occurrence

All leave must be applied for via the HR portal.

Reply *0* for the main menu."""
        
        elif "promotion" in message:
            return f"""🏅 *Promotion Procedures*

1. Vacancy must be advertised internally
2. Officers apply via the HR portal
3. Qualifications & performance appraisals are reviewed
4. Shortlisted candidates are interviewed
5. Successful officers are notified

For details, contact HR at {self.hr_email}

Reply *0* for the main menu."""
        
        elif "conduct" in message:
            return f"""⚖️ *Code of Conduct*

All county officers are expected to:
• Act with integrity and professionalism
• Declare any conflict of interest
• Respect colleagues and the public
• Protect confidential information
• Report corruption or misconduct

Reply *0* for the main menu."""
        
        elif "pension" in message:
            return f"""🏦 *Pension Scheme*

• Contributions are deducted monthly from salary
• Benefits depend on years of service and final salary
• Retirement age is 60 years

For your individual pension statement, contact HR:
📞 {self.hr_phone}
📧 {self.hr_email}

Reply *0* for the main menu."""
        
        else:
            return f"""📚 *HR Policies*

Which policy area do you need information on?

• *Leave* – Annual, Sick, Maternity/Paternity
• *Promotion* – Career progression
• *Conduct* – Code of Ethics
• *Pension* – Retirement benefits

Reply with the policy name (e.g., "leave") or *0* for the main menu."""
    
    def _handle_portal(self, message):
        if "upload" in message:
            return f"""📎 *How to Upload Documents*

1. Log in at {self.portal_url}
2. Go to *'Staff Registry'* or *'Applicant Profile'*
3. Use the import feature to upload data
4. Select your file (Excel or CSV format)
5. Click *'Import'*

⚠️ Ensure files are in the correct template format.

Reply *0* for the main menu."""
        
        elif "password" in message or "reset" in message:
            return f"""🔐 *Reset Your Portal Password*

1. Go to {self.portal_url}
2. Click *'Forgot Password?'*
3. Enter your registered email or phone number
4. You'll receive a reset link or OTP
5. Follow the instructions to set a new password

⚠️ *Never share your password with anyone.*

Reply *0* for the main menu."""
        
        elif "claim" in message:
            return f"""📬 *Submit a Claim or Allowance Request*

Currently, claims and allowances are processed through the HR department.

Please contact HR directly:
📞 {self.hr_phone}
📧 {self.hr_email}

Reply *0* for the main menu."""
        
        else:
            return f"""💻 *HR Portal Support*

What do you need help with?

• *Upload* – How to upload documents/data
• *Password* – Reset my portal password
• *Claim* – Submit a claim or allowance

Reply with the action (e.g., "upload") or *0* for the main menu."""
    
    def _get_fallback_response(self):
        return f"""I'm sorry, I didn't quite catch that.

To make sure I give you the right HR information, please reply with *1*, *2*, or *3*:

1️⃣ Job Vacancies & Applications
2️⃣ HR Policies
3️⃣ Portal Support

Or reply *0* for the main menu."""
    
    def _get_security_warning(self):
        return f"""⚠️ *Security Reminder:* 

Please do not share sensitive information such as your National ID number, password, or banking details in this chat. 

Only enter these on the secure official portal at {self.portal_url}.

Reply *0* for the main menu."""
    
    def _save_conversation(self, phone_number, message, response, intent):
        """Save conversation to database"""
        try:
            conn = get_conn()
            cursor = conn.cursor()
            is_cloud = st.secrets.get("DATABASE_URL") is not None
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if is_cloud:
                cursor.execute("""
                    INSERT INTO whatsapp_conversations (phone_number, message, response, intent, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (phone_number, message, response, intent, now))
            else:
                cursor.execute("""
                    INSERT INTO whatsapp_conversations (phone_number, message, response, intent, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (phone_number, message, response, intent, now))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving conversation: {e}")
# =========================================================
# APP CONFIG
# =========================================================
# At the VERY TOP of your app (before any other code)
st.set_page_config(
    page_title="EMBU COUNTY PUBLIC SERVICE BOARD",  
    layout="wide",
    page_icon="🏛️",
    initial_sidebar_state="expanded",  # Can be "expanded" or "collapsed"
    menu_items={
        'Get help': None,
        'Report a bug': None,
        'About': None
    }
)
# Add at the top of your app
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_staff_count():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM staff")
    count = cursor.fetchone()[0]
    conn.close()
    return count

@st.cache_data(ttl=300)
def get_positions():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM advertised_positions WHERE status = 'Open'", conn)
    conn.close()
    return df
# =========================================================
# DB CONNECTION
# =========================================================
def get_conn():
    """Get database connection - works on both local and Streamlit Cloud"""
    
    # Check if we're on Streamlit Cloud with a DATABASE_URL secret
    database_url = st.secrets.get("DATABASE_URL")
    
    if database_url:
        # Running on Streamlit Cloud - use PostgreSQL
        try:
            # Ensure SSL is enabled for Neon
            if "sslmode" not in database_url:
                if "?" in database_url:
                    database_url += "&sslmode=require"
                else:
                    database_url += "?sslmode=require"
            
            conn = psycopg2.connect(
                database_url,
                connect_timeout=30,
                keepalives=1,
                keepalives_idle=5,
                keepalives_interval=2,
                keepalives_count=2
            )
            return conn
            
        except Exception as e:
            st.error(f"❌ Database connection failed: {e}")
            return None
    else:
        # Running locally - use SQLite
        return sqlite3.connect("ecde.db", check_same_thread=False)
# =========================================================
# CACHED DATA FUNCTIONS (Add these after get_conn())
# =========================================================

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_stats():
    """Get cached stats to avoid repeated database queries"""
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM staff")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM staff WHERE application_status='Shortlisted'")
    shortlisted = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM staff WHERE interview_score IS NOT NULL AND interview_score > 0")
    interviewed = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM staff WHERE application_status='Recommended'")
    successful = c.fetchone()[0]
    
    conn.close()
    return total, shortlisted, interviewed, successful

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_staff_data():
    """Get cached staff data for dashboard"""
    conn = get_conn()
    df = pd.read_sql("SELECT application_status, subcounty, gender, yob, created_at, disability, ethnicity, interview_score FROM staff", conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def get_cached_shortlisted_candidates():
    """Get cached shortlisted candidates"""
    conn = get_conn()
    df = pd.read_sql("""
        SELECT id, name, id_number, contact, email, qualifications, experience_years, 
               subcounty, created_at, remarks
        FROM staff  
        WHERE application_status = 'Shortlisted'
        ORDER BY shortlist_date DESC, name
    """, conn)
    conn.close()
    return df
# =========================================================
# SECURITY FUNCTIONS
# =========================================================
def hash_password(password):
    """Hash a password using SHA256"""
    salt = "ecde_secure_salt"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def create_default_admin():
    """Create default Super Admin user if doesn't exist"""
    conn = get_conn()
    
    if conn is None:
        return
    
    c = conn.cursor()
    
    # Check which database we're using
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    try:
        # Check if admin exists (case-insensitive)
        if is_cloud:
            c.execute("SELECT * FROM users WHERE LOWER(username) = %s", ("admin",))
        else:
            c.execute("SELECT * FROM users WHERE LOWER(username) = ?", ("admin",))
        
        if not c.fetchone():
            # Insert Super Admin user
            admin_password = hash_password("cpsb123")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if is_cloud:
                c.execute("""
                    INSERT INTO users (username, password, role, created_at)
                    VALUES (%s, %s, %s, %s)
                """, ("admin", admin_password, "Super Admin", created_at))
            else:
                c.execute("""
                    INSERT INTO users (username, password, role, created_at)
                    VALUES (?, ?, ?, ?)
                """, ("admin", admin_password, "Super Admin", created_at))
            
            conn.commit()
            print("✅ Default Super Admin user created (username: admin, password: cpsb123)")
    
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        conn.close()

def login_user(identifier, password):
    """Login using username, email, or phone - also accepts OTP for new users"""
    conn = get_conn()
    if conn is None:
        return None
    
    cursor = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    try:
        # Find user by identifier
        if '@' in identifier:
            if is_cloud:
                cursor.execute("SELECT * FROM users WHERE email = %s", (identifier,))
            else:
                cursor.execute("SELECT * FROM users WHERE email = ?", (identifier,))
        elif identifier.isdigit() and len(identifier) >= 10:
            if is_cloud:
                cursor.execute("SELECT * FROM users WHERE phone = %s", (identifier,))
            else:
                cursor.execute("SELECT * FROM users WHERE phone = ?", (identifier,))
        else:
            identifier_lower = identifier.lower()
            if is_cloud:
                cursor.execute("SELECT * FROM users WHERE LOWER(username) = %s", (identifier_lower,))
            else:
                cursor.execute("SELECT * FROM users WHERE LOWER(username) = ?", (identifier_lower,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return None
        
        # Check user fields (is_verified at index 6, verification_otp at index 8)
        is_verified = user[6] if len(user) > 6 else True
        verification_otp = user[8] if len(user) > 8 else None
        
        # Check if this is a new user trying to log in with OTP
        if not is_verified and verification_otp and password == verification_otp:
            conn.close()
            return (user, "otp_login")
        
        # Normal password check
        hashed_password = hash_password(password)
        
        # Find user by username with password
        identifier_lower = identifier.lower()
        if is_cloud:
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = %s AND password = %s", (identifier_lower, hashed_password))
        else:
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = ? AND password = ?", (identifier_lower, hashed_password))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return (user, "password_login")
        
        return None
        
    except Exception as e:
        st.error(f"Login error: {e}")
        conn.close()
        return None

# =========================================================
# DATABASE INIT
# =========================================================
# =========================================================
# DATABASE INIT
# =========================================================
# =========================================================
# DATABASE INIT
# =========================================================
# =========================================================
# DATABASE INIT
# =========================================================
# =========================================================
# DATABASE INIT
# =========================================================
def init_db():
    conn = get_conn()
    
    if conn is None:
        st.error("Cannot initialize database - no connection")
        return
    
    c = conn.cursor()
    
    # Check which database we're using
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    if is_cloud:
        # ===========================================
        # POSTGRESQL SYNTAX (for Streamlit Cloud)
        # ===========================================
        
        # Users table
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            created_at TEXT
        )
        """)
        
        # Staff/Applicants table
        c.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id SERIAL PRIMARY KEY,
            sno INTEGER,
            name TEXT,
            gender TEXT,
            id_number TEXT UNIQUE,
            yob INTEGER,
            ethnicity TEXT,
            disability TEXT,
            contact TEXT,
            kcse TEXT,
            qualifications TEXT,
            subcounty TEXT,
            ward TEXT,
            experience TEXT,
            remarks TEXT,
            created_at TEXT,
            created_by TEXT,
            application_status TEXT DEFAULT 'Pending',
            position_applied TEXT,
            application_date TEXT,
            interview_date TEXT,
            interview_score REAL,
            email TEXT,
            kcse_grade TEXT,
            institution TEXT,
            graduation_year INTEGER,
            professional_body TEXT,
            experience_years INTEGER,
            current_employer TEXT,
            referee1_name TEXT,
            referee1_contact TEXT,
            referee2_name TEXT,
            referee2_contact TEXT,
            documents_ready TEXT,
            declaration_accepted TEXT DEFAULT 'No',
            advertisement_ref TEXT
        )
        """)
        
        # Dropdown options table
        c.execute("""
        CREATE TABLE IF NOT EXISTS dropdown_options (
            id SERIAL PRIMARY KEY,
            category TEXT,
            option_value TEXT,
            option_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        # Advertised positions table
        c.execute("""
        CREATE TABLE IF NOT EXISTS advertised_positions (
            id SERIAL PRIMARY KEY,
            position_title TEXT,
            position_code TEXT,
            department TEXT,
            employment_type TEXT,
            vacancies INTEGER,
            requirements TEXT,
            responsibilities TEXT,
            salary_range TEXT,
            application_deadline TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        # Recruitment rounds table
        c.execute("""
        CREATE TABLE IF NOT EXISTS recruitment_rounds (
            id SERIAL PRIMARY KEY,
            round_name TEXT,
            start_date TEXT,
            end_date TEXT,
            positions_available TEXT,
            status TEXT DEFAULT 'Upcoming',
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        # Audit log table - FIXED: changed 'user' to 'username'
        c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            username TEXT,
            action TEXT,
            record_id INTEGER,
            details TEXT,
            timestamp TEXT
        )
        """)
        
        # Position tracking tables
        c.execute("""
        CREATE TABLE IF NOT EXISTS position_applications (
            id SERIAL PRIMARY KEY,
            position_id INTEGER,
            position_title TEXT,
            position_code TEXT,
            applicant_id INTEGER,
            applicant_name TEXT,
            id_number TEXT,
            application_date TEXT,
            status TEXT DEFAULT 'Pending',
            status_updated_date TEXT,
            interview_date TEXT,
            interview_score REAL,
            interview_remarks TEXT,
            shortlist_date TEXT,
            hired_date TEXT,
            rejection_reason TEXT,
            notes TEXT,
            updated_by TEXT
        )
        """)
        
        # ===========================================
        # HR TABLES
        # ===========================================
        
        # Employees table (HR)
        c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            staff_no TEXT PRIMARY KEY,
            name TEXT,
            personal_no TEXT,
            age INTEGER,
            department TEXT,
            first_appointment_date TEXT,
            first_appointment_designation TEXT,
            current_designation TEXT,
            current_job_group TEXT,
            academic_qualifications TEXT,
            professional_qualifications TEXT,
            discipline_history TEXT,
            chrmc_approval_date TEXT,
            cpsb_approval_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT
        )
        """)
        
        # Employee history table (HR)
        c.execute("""
        CREATE TABLE IF NOT EXISTS employee_history (
            id SERIAL PRIMARY KEY,
            staff_no TEXT,
            event_type TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT
        )
        """)
        
        # Panelists table (Scoresheet)
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelists (
            id SERIAL PRIMARY KEY,
            name TEXT,
            role TEXT,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
        
        # Scoring criteria table (Scoresheet)
        c.execute("""
        CREATE TABLE IF NOT EXISTS scoring_criteria (
            id SERIAL PRIMARY KEY,
            criteria_key TEXT UNIQUE,
            criteria_name TEXT,
            max_score INTEGER,
            description TEXT,
            is_active INTEGER DEFAULT 1
        )
        """)
        
        # Scoring parameters table (Scoresheet)
        c.execute("""
        CREATE TABLE IF NOT EXISTS scoring_parameters (
            id SERIAL PRIMARY KEY,
            param_key TEXT UNIQUE,
            param_name TEXT,
            param_value TEXT,
            description TEXT
        )
        """)
        
        # Panelist scores table (Scoresheet)
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelist_scores (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER,
            panelist_id INTEGER,
            academic_score INTEGER,
            hr_knowledge_score INTEGER,
            procurement_score INTEGER,
            gov_structure_score INTEGER,
            leadership_score INTEGER,
            communication_score INTEGER,
            general_knowledge_score INTEGER,
            technical_score INTEGER,
            total_score REAL,
            timestamp TEXT
        )
        """)
        
    else:
        # ===========================================
        # SQLITE SYNTAX (for local development)
        # ===========================================
        
        # Users table
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            created_at TEXT
        )
        """)
        
        # Staff/Applicants table
        c.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sno INTEGER,
            name TEXT,
            gender TEXT,
            id_number TEXT UNIQUE,
            yob INTEGER,
            ethnicity TEXT,
            disability TEXT,
            contact TEXT,
            kcse TEXT,
            qualifications TEXT,
            subcounty TEXT,
            ward TEXT,
            experience TEXT,
            remarks TEXT,
            created_at TEXT,
            created_by TEXT,
            application_status TEXT DEFAULT 'Pending',
            position_applied TEXT,
            application_date TEXT,
            interview_date TEXT,
            interview_score REAL,
            email TEXT,
            kcse_grade TEXT,
            institution TEXT,
            graduation_year INTEGER,
            professional_body TEXT,
            experience_years INTEGER,
            current_employer TEXT,
            referee1_name TEXT,
            referee1_contact TEXT,
            referee2_name TEXT,
            referee2_contact TEXT,
            documents_ready TEXT,
            declaration_accepted TEXT DEFAULT 'No',
            advertisement_ref TEXT
        )
        """)
        
        # Dropdown options table
        c.execute("""
        CREATE TABLE IF NOT EXISTS dropdown_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            option_value TEXT,
            option_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        # Advertised positions table
        c.execute("""
        CREATE TABLE IF NOT EXISTS advertised_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_title TEXT,
            position_code TEXT,
            department TEXT,
            employment_type TEXT,
            vacancies INTEGER,
            requirements TEXT,
            responsibilities TEXT,
            salary_range TEXT,
            application_deadline TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        # Recruitment rounds table
        c.execute("""
        CREATE TABLE IF NOT EXISTS recruitment_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_name TEXT,
            start_date TEXT,
            end_date TEXT,
            positions_available TEXT,
            status TEXT DEFAULT 'Upcoming',
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        # Audit log table
        c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            record_id INTEGER,
            details TEXT,
            timestamp TEXT
        )
        """)
        
        # Position tracking tables
        c.execute("""
        CREATE TABLE IF NOT EXISTS position_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER,
            position_title TEXT,
            position_code TEXT,
            applicant_id INTEGER,
            applicant_name TEXT,
            id_number TEXT,
            application_date TEXT,
            status TEXT DEFAULT 'Pending',
            status_updated_date TEXT,
            interview_date TEXT,
            interview_score REAL,
            interview_remarks TEXT,
            shortlist_date TEXT,
            hired_date TEXT,
            rejection_reason TEXT,
            notes TEXT,
            updated_by TEXT
        )
        """)
        
        # ===========================================
        # HR TABLES
        # ===========================================
        
        # Employees table (HR)
        c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            staff_no TEXT PRIMARY KEY,
            name TEXT,
            personal_no TEXT,
            age INTEGER,
            department TEXT,
            first_appointment_date TEXT,
            first_appointment_designation TEXT,
            current_designation TEXT,
            current_job_group TEXT,
            academic_qualifications TEXT,
            professional_qualifications TEXT,
            discipline_history TEXT,
            chrmc_approval_date TEXT,
            cpsb_approval_date TEXT,
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        # Employee history table (HR)
        c.execute("""
        CREATE TABLE IF NOT EXISTS employee_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_no TEXT,
            event_type TEXT,
            details TEXT,
            timestamp TEXT,
            created_by TEXT
        )
        """)
        
        # Panelists table (Scoresheet)
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
        
        # Scoring criteria table (Scoresheet)
        c.execute("""
        CREATE TABLE IF NOT EXISTS scoring_criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            criteria_key TEXT UNIQUE,
            criteria_name TEXT,
            max_score INTEGER,
            description TEXT,
            is_active INTEGER DEFAULT 1
        )
        """)
        
        # Scoring parameters table (Scoresheet)
        c.execute("""
        CREATE TABLE IF NOT EXISTS scoring_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            param_key TEXT UNIQUE,
            param_name TEXT,
            param_value TEXT,
            description TEXT
        )
        """)
        
        # Panelist scores table (Scoresheet)
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelist_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            panelist_id INTEGER,
            academic_score INTEGER,
            hr_knowledge_score INTEGER,
            procurement_score INTEGER,
            gov_structure_score INTEGER,
            leadership_score INTEGER,
            communication_score INTEGER,
            general_knowledge_score INTEGER,
            technical_score INTEGER,
            total_score REAL,
            timestamp TEXT
        )
        """)
    
    # ===========================================
    # CREATE INDEXES
    # ===========================================
    
    if is_cloud:
        # PostgreSQL indexes
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_id_number ON staff(id_number)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_name ON staff(name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_subcounty ON staff(subcounty)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_status ON staff(application_status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_position ON position_applications(position_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_status ON position_applications(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_applicant ON position_applications(applicant_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_employees_staff_no ON employees(staff_no)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department)")
        except Exception as e:
            print(f"Index creation warning: {e}")
    else:
        # SQLite indexes
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_id_number ON staff(id_number)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_name ON staff(name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_subcounty ON staff(subcounty)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_status ON staff(application_status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_position ON position_applications(position_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_status ON position_applications(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_applicant ON position_applications(applicant_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_employees_staff_no ON employees(staff_no)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department)")
        except Exception as e:
            print(f"Index creation warning: {e}")
    
    conn.commit()
    conn.close()
def ensure_database_columns():
    """Add missing columns - safe for both SQLite and PostgreSQL"""
    conn = get_conn()
    if conn is None:
        return
    
    c = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Columns that should exist (name: type)
    required_columns = {
        'gender': "TEXT",
        'email': "TEXT",
        'position_applied': "TEXT",
        'application_status': "TEXT DEFAULT 'Pending'",
        'subcounty': "TEXT",
        'ward': "TEXT",
        'qualifications': "TEXT",
        'institution': "TEXT",
        'graduation_year': "INTEGER",
        'experience_years': "INTEGER",
        'kcse_grade': "TEXT",
        'interview_score': "REAL",
        'interview_date': "TEXT"
    }
    
    if is_cloud:
        # PostgreSQL - try to add each column (ignores if already exists)
        for col_name, col_type in required_columns.items():
            try:
                # PostgreSQL 9.6+ supports IF NOT EXISTS
                c.execute(f"ALTER TABLE staff ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            except Exception:
                try:
                    # Fallback for older PostgreSQL versions
                    c.execute(f"ALTER TABLE staff ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass  # Column already exists or can't be added
    else:
        # SQLite - check existing columns first
        try:
            c.execute("PRAGMA table_info(staff)")
            existing_columns = [col[1] for col in c.fetchall()]
            
            for col_name, col_type in required_columns.items():
                if col_name not in existing_columns:
                    try:
                        # Extract default value if present
                        if "DEFAULT" in col_type:
                            default_part = col_type.split("DEFAULT")[1].strip()
                            base_type = col_type.split("DEFAULT")[0].strip()
                            c.execute(f"ALTER TABLE staff ADD COLUMN {col_name} {base_type} DEFAULT {default_part}")
                        else:
                            c.execute(f"ALTER TABLE staff ADD COLUMN {col_name} {col_type}")
                    except Exception as e:
                        print(f"Error adding {col_name}: {e}")
        except Exception as e:
            print(f"Error checking columns: {e}")
    
    conn.commit()
    conn.close()
    # Create default admin user
    create_default_admin()
# =========================================================
# MIGRATE DATABASE (Works for both SQLite and PostgreSQL)
# =========================================================
def migrate_database():
    """Add new columns to existing database - safe for both SQLite and PostgreSQL"""
    conn = get_conn()
    if conn is None:
        return
    
    c = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # List of columns to add
    new_columns = [
        ("application_status", "TEXT DEFAULT 'Pending'"),
        ("position_applied", "TEXT"),
        ("application_date", "TEXT"),
        ("interview_date", "TEXT"),
        ("interview_score", "REAL"),
        ("email", "TEXT"),
        ("kcse_grade", "TEXT"),
        ("institution", "TEXT"),
        ("graduation_year", "INTEGER"),
        ("professional_body", "TEXT"),
        ("experience_years", "INTEGER"),
        ("current_employer", "TEXT"),
        ("referee1_name", "TEXT"),
        ("referee1_contact", "TEXT"),
        ("referee2_name", "TEXT"),
        ("referee2_contact", "TEXT"),
        ("documents_ready", "TEXT"),
        ("declaration_accepted", "TEXT DEFAULT 'No'"),
        ("shortlist_date", "TIMESTAMP")
    ]
    
    # Add each column
    for col_name, col_type in new_columns:
        try:
            if is_cloud:
                # PostgreSQL syntax with IF NOT EXISTS
                c.execute(f"ALTER TABLE staff ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            else:
                # SQLite syntax - check if column exists first
                c.execute("PRAGMA table_info(staff)")
                existing_columns = [col[1] for col in c.fetchall()]
                if col_name not in existing_columns:
                    c.execute(f"ALTER TABLE staff ADD COLUMN {col_name} {col_type}")
        except Exception as e:
            # Column might already exist or other error
            print(f"Column {col_name} add skipped: {e}")
    
    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_id_number ON staff(id_number)",
        "CREATE INDEX IF NOT EXISTS idx_name ON staff(name)",
        "CREATE INDEX IF NOT EXISTS idx_subcounty ON staff(subcounty)",
        "CREATE INDEX IF NOT EXISTS idx_status ON staff(application_status)",
        "CREATE INDEX IF NOT EXISTS idx_position ON staff(position_applied)",
        "CREATE INDEX IF NOT EXISTS idx_application_date ON staff(application_date)"
    ]
    
    for idx_sql in indexes:
        try:
            c.execute(idx_sql)
        except Exception as e:
            print(f"Index creation skipped: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Database migration completed")

# Call this function after init_db() in main()
# =========================================================
# SESSION INIT
# =========================================================
if "user" not in st.session_state:
    st.session_state.user = None
if "edit_staff_id" not in st.session_state:
    st.session_state.edit_staff_id = None
# =========================================================
# HR FUNCTIONS MODULE
# =========================================================

# =========================================================
# HR FUNCTIONS MODULE
# =========================================================

def hr_dashboard():
    """HR Functions Dashboard"""
    
    # Check if user is logged in
    if "user" not in st.session_state or st.session_state.user is None:
        st.error("Please login to access HR Functions")
        return
    
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">👔 HR Functions</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Human Resource Management Dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    cursor = conn.cursor()
    
    # =========================================================
    # STEP 1: CREATE ALL TABS FIRST - THIS MUST COME FIRST
    # =========================================================
    hr_tab1, hr_tab2, hr_tab3, hr_tab4, hr_tab5, hr_tab6, hr_tab7, hr_tab8, hr_tab9, hr_tab10, hr_tab11, hr_tab12, hr_tab13, hr_tab14, hr_tab15, hr_tab16 = st.tabs([
        "📊 HR Analytics",
        "👥 Staff Registry",
        "📥 Import Staff",
        "📈 Promotions",
        "🔄 Redesignation",
        "📄 Contracts",
        "🔄 Translation of Terms",
        "💰 Salary Harmonization",
        "🏖️ Unpaid Leave",
        "✅ Confirmation",
        "⚖️ Discipline Cases",
        "🎭 Appointment in Acting Capacity",
        "📋 Reports",
        "📊 Staff Establishment",
        "📋 Monthly Staff Returns",
        "💬 HR Assistant"
    ])
    
    # =========================================================
    # STEP 2: TAB 1 - HR ANALYTICS
    # =========================================================
    with hr_tab1:
        st.subheader("📊 HR Analytics Dashboard")
        
        try:
            # Check if employees table exists
            if is_cloud:
                cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'employees')")
                table_exists = cursor.fetchone()[0]
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                st.info("📋 HR module is being set up. Please add staff records using the Staff Registry tab.")
            else:
                employees_df = pd.read_sql("SELECT * FROM employees", conn)
                
                if employees_df.empty:
                    st.info("No employee records found. Add staff in the Staff Registry tab.")
                else:
                    # ==================== TOP METRICS ====================
                    total_employees = len(employees_df)
                    
                    # Get promotion data
                    promotions_df = pd.read_sql("SELECT * FROM hr_promotions", conn) if table_exists else pd.DataFrame()
                    total_promotions = len(promotions_df)
                    
                    # Get discipline cases
                    discipline_df = pd.read_sql("SELECT * FROM hr_discipline", conn) if table_exists else pd.DataFrame()
                    total_discipline = len(discipline_df)
                    
                    # Get unpaid leave
                    leave_df = pd.read_sql("SELECT * FROM hr_unpaid_leave WHERE status = 'Approved'", conn) if table_exists else pd.DataFrame()
                    total_leave = len(leave_df)
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Total Employees", total_employees)
                    col2.metric("Total Promotions", total_promotions)
                    col3.metric("Discipline Cases", total_discipline)
                    col4.metric("On Unpaid Leave", total_leave)
                    
                    # Calculate turnover rate (employees joined in last 12 months)
                    if 'created_at' in employees_df.columns:
                        one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                        new_employees = len(employees_df[employees_df['created_at'] >= one_year_ago])
                        turnover_rate = (new_employees / total_employees * 100) if total_employees > 0 else 0
                        col5.metric("New Employees (12m)", f"{new_employees} ({turnover_rate:.0f}%)")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 1: TWO COLUMNS ====================
                    col1, col2 = st.columns(2)
                    
                    # Chart 1: Department Distribution
                    with col1:
                        st.markdown("### 🏢 Department Distribution")
                        if 'department' in employees_df.columns:
                            dept_counts = employees_df['department'].value_counts().reset_index()
                            dept_counts.columns = ['Department', 'Count']
                            
                            fig_dept = px.bar(dept_counts, x='Department', y='Count', 
                                             title="Employees by Department",
                                             color='Count',
                                             color_continuous_scale='Blues')
                            fig_dept.update_layout(height=400)
                            st.plotly_chart(fig_dept, use_container_width=True)
                        else:
                            st.info("Department data not available")
                    
                    # Chart 2: Gender Distribution
                    with col2:
                        st.markdown("### 👥 Gender Distribution")
                        if 'gender' in employees_df.columns:
                            gender_counts = employees_df['gender'].value_counts().reset_index()
                            gender_counts.columns = ['Gender', 'Count']
                            
                            fig_gender = px.pie(gender_counts, values='Count', names='Gender',
                                               title="Gender Ratio", hole=0.4,
                                               color_discrete_sequence=['#3b82f6', '#ef4444'])
                            fig_gender.update_layout(height=400)
                            st.plotly_chart(fig_gender, use_container_width=True)
                        else:
                            st.info("Gender data not available. Add gender field to employees.")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 2: PROMOTION ANALYTICS ====================
                    st.markdown("## 📈 Promotion Analytics")
                    
                    col1, col2 = st.columns(2)
                    
                    # Chart 3: Promotions by Department
                    with col1:
                        st.markdown("### 📊 Promotions by Department")
                        if not promotions_df.empty and 'staff_no' in promotions_df.columns:
                            promo_dept = pd.merge(promotions_df, employees_df[['staff_no', 'department']], 
                                                  on='staff_no', how='left')
                            dept_promo_counts = promo_dept['department'].value_counts().reset_index()
                            dept_promo_counts.columns = ['Department', 'Promotions']
                            
                            fig_promo_dept = px.bar(dept_promo_counts, x='Department', y='Promotions',
                                                   title="Promotion Distribution by Department",
                                                   color='Promotions',
                                                   color_continuous_scale='Greens')
                            fig_promo_dept.update_layout(height=400)
                            st.plotly_chart(fig_promo_dept, use_container_width=True)
                        else:
                            st.info("No promotion data available")
                    
                    # Chart 4: Promotions Trend Over Time
                    with col2:
                        st.markdown("### 📅 Promotions Trend")
                        if not promotions_df.empty and 'effective_date' in promotions_df.columns:
                            promotions_df['effective_date'] = pd.to_datetime(promotions_df['effective_date'])
                            promotions_df['year_month'] = promotions_df['effective_date'].dt.strftime('%Y-%m')
                            monthly_promos = promotions_df.groupby('year_month').size().reset_index(name='count')
                            
                            fig_promo_trend = px.line(monthly_promos, x='year_month', y='count',
                                                     title="Monthly Promotion Trends",
                                                     markers=True, line_shape='linear')
                            fig_promo_trend.update_layout(height=400, xaxis_title="Month", yaxis_title="Number of Promotions")
                            st.plotly_chart(fig_promo_trend, use_container_width=True)
                        else:
                            st.info("No promotion trend data available")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 3: STAGNATION ANALYSIS ====================
                    st.markdown("## ⏰ Stagnation Analysis")
                    st.markdown("Employees who have stayed in the same position for **more than 3 years** from Date of Current Designation")
                    
                    if 'current_designation_date' in employees_df.columns:
                        employees_analysis = employees_df.copy()
                        employees_analysis['current_designation_date_dt'] = pd.to_datetime(employees_analysis['current_designation_date'], errors='coerce')
                        today = datetime.now()
                        employees_analysis['years_in_current_role'] = (today - employees_analysis['current_designation_date_dt']).dt.days / 365.25
                        
                        stagnated_employees = employees_analysis[
                            (employees_analysis['years_in_current_role'] >= 3) & 
                            (employees_analysis['years_in_current_role'].notna())
                        ].copy()
                        
                        no_date_employees = employees_analysis[
                            employees_analysis['current_designation_date'].isna() | 
                            (employees_analysis['current_designation_date'] == '') |
                            (employees_analysis['current_designation_date'] == 'None')
                        ].copy()
                        
                        if not no_date_employees.empty:
                            no_date_employees['years_in_current_role'] = 'Date not recorded'
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### 📊 Stagnation Statistics")
                            st.metric("Employees Stagnated (3+ years)", len(stagnated_employees))
                            if len(stagnated_employees) > 0:
                                avg_years = stagnated_employees['years_in_current_role'].mean()
                                st.metric("Average Years in Current Role", f"{avg_years:.1f} years")
                            st.metric("Employees with No Date Recorded", len(no_date_employees))
                        
                        with col2:
                            st.markdown("#### 📊 Stagnation by Department")
                            if not stagnated_employees.empty and 'department' in stagnated_employees.columns:
                                dept_stagnation = stagnated_employees['department'].value_counts().reset_index()
                                dept_stagnation.columns = ['Department', 'Stagnated Count']
                                fig_stagnation = px.bar(dept_stagnation.head(10), x='Department', y='Stagnated Count',
                                                       title="Stagnated Employees by Department (3+ years)",
                                                       color='Stagnated Count',
                                                       color_continuous_scale='Reds')
                                fig_stagnation.update_layout(height=400)
                                st.plotly_chart(fig_stagnation, use_container_width=True, key="stagnation_dept_chart")
                            else:
                                st.info("No stagnated employees in selected filter")
                        
                        st.markdown("---")
                        
                        st.markdown("#### 📋 Stagnated Employees List (3+ years in current role)")
                        if not stagnated_employees.empty:
                            display_columns = ['staff_no', 'name', 'department', 'current_designation', 'current_job_group', 'current_designation_date', 'years_in_current_role']
                            available_columns = [col for col in display_columns if col in stagnated_employees.columns]
                            display_stagnated = stagnated_employees[available_columns].copy()
                            
                            if 'years_in_current_role' in display_stagnated.columns:
                                display_stagnated['years_in_current_role'] = display_stagnated['years_in_current_role'].apply(lambda x: f"{x:.1f} years")
                            
                            column_renames = {
                                'staff_no': 'Staff No',
                                'personal_no': 'Personal No',
                                'name': 'Name',
                                'department': 'Department',
                                'current_designation': 'Current Designation',
                                'current_job_group': 'Job Group',
                                'current_designation_date': 'Date of Current Designation',
                                'years_in_current_role': 'Years in Role'
                            }
                            display_stagnated = display_stagnated.rename(columns={k: v for k, v in column_renames.items() if k in display_stagnated.columns})
                            
                            st.dataframe(display_stagnated, use_container_width=True)
                            
                            csv_stagnated = stagnated_employees.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "📥 Download Stagnated Employees List (CSV)",
                                csv_stagnated,
                                f"stagnated_employees_{datetime.now().strftime('%Y%m%d')}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        else:
                            st.info(f"✅ No employees have been stagnated (3+ years) in their current role")
                        
                        if not no_date_employees.empty:
                            with st.expander(f"⚠️ Employees with No Current Designation Date Recorded ({len(no_date_employees)})"):
                                display_columns = ['staff_no', 'name', 'department', 'current_designation']
                                available_columns = [col for col in display_columns if col in no_date_employees.columns]
                                display_no_date = no_date_employees[available_columns].copy()
                                
                                column_renames = {
                                    'staff_no': 'Staff No',
                                    'personal_no': 'Personal No',
                                    'name': 'Name',
                                    'department': 'Department',
                                    'current_designation': 'Current Designation'
                                }
                                display_no_date = display_no_date.rename(columns={k: v for k, v in column_renames.items() if k in display_no_date.columns})
                                st.dataframe(display_no_date, use_container_width=True)
                                st.info("💡 Tip: Update the 'Date of Current Designation' for these employees to track stagnation accurately.")
                    else:
                        st.info("Current Designation Date not available. Please ensure employees have their 'Date of Current Designation' filled.")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 4: DISCIPLINE CASES ANALYSIS ====================
                    st.markdown("## ⚖️ Discipline Cases Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 📊 Discipline Cases by Department")
                        if not discipline_df.empty and 'staff_no' in discipline_df.columns:
                            disc_dept = pd.merge(discipline_df, employees_df[['staff_no', 'department']], 
                                                 on='staff_no', how='left')
                            dept_disc_counts = disc_dept['department'].value_counts().reset_index()
                            dept_disc_counts.columns = ['Department', 'Cases']
                            
                            fig_disc_dept = px.bar(dept_disc_counts, x='Department', y='Cases',
                                                  title="Discipline Cases Distribution by Department",
                                                  color='Cases',
                                                  color_continuous_scale='Oranges')
                            fig_disc_dept.update_layout(height=400)
                            st.plotly_chart(fig_disc_dept, use_container_width=True)
                        else:
                            st.info("No discipline case data available")
                    
                    with col2:
                        st.markdown("### 📋 Discipline Cases by Type")
                        if not discipline_df.empty and 'case_type' in discipline_df.columns:
                            case_type_counts = discipline_df['case_type'].value_counts().reset_index()
                            case_type_counts.columns = ['Case Type', 'Count']
                            
                            fig_case_type = px.pie(case_type_counts, values='Count', names='Case Type',
                                                  title="Case Type Distribution", hole=0.3)
                            fig_case_type.update_layout(height=400)
                            st.plotly_chart(fig_case_type, use_container_width=True)
                        else:
                            st.info("No case type data available")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 5: AGE ANALYSIS ====================
                    st.markdown("## 🎂 Age Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 📊 Age Distribution")
                        if 'age' in employees_df.columns:
                            ages = employees_df['age'].dropna()
                            if not ages.empty:
                                fig_age = px.histogram(ages, x='age', nbins=15,
                                                      title="Age Distribution of Employees",
                                                      labels={'age': 'Age', 'count': 'Number of Employees'},
                                                      color_discrete_sequence=['#3b82f6'])
                                fig_age.update_layout(height=400)
                                st.plotly_chart(fig_age, use_container_width=True)
                                
                                age_bins = [0, 25, 35, 45, 55, 65, 100]
                                age_labels = ['Under 25', '25-35', '35-45', '45-55', '55-65', '65+']
                                employees_df['age_group'] = pd.cut(employees_df['age'], bins=age_bins, labels=age_labels, right=False)
                                age_group_counts = employees_df['age_group'].value_counts().reset_index()
                                age_group_counts.columns = ['Age Group', 'Count']
                                
                                st.markdown("#### Age Group Summary")
                                st.dataframe(age_group_counts, use_container_width=True)
                            else:
                                st.info("Age data not available")
                        else:
                            st.info("Age data not available")
                    
                    with col2:
                        st.markdown("### 📊 Average Age by Department")
                        if 'age' in employees_df.columns and 'department' in employees_df.columns:
                            dept_age = employees_df.groupby('department')['age'].mean().reset_index()
                            dept_age.columns = ['Department', 'Average Age']
                            dept_age = dept_age.sort_values('Average Age', ascending=False)
                            
                            fig_dept_age = px.bar(dept_age, x='Department', y='Average Age',
                                                 title="Average Age by Department",
                                                 color='Average Age',
                                                 color_continuous_scale='Viridis')
                            fig_dept_age.update_layout(height=400)
                            st.plotly_chart(fig_dept_age, use_container_width=True)
                        else:
                            st.info("Department or age data not available")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 6: MONTHLY ANALYSIS ====================
                    st.markdown("## 📅 Monthly Analysis (All Modules)")
                    
                    monthly_data = pd.DataFrame()
                    
                    if 'created_at' in employees_df.columns:
                        employees_df['created_month'] = pd.to_datetime(employees_df['created_at']).dt.strftime('%Y-%m')
                        monthly_growth = employees_df.groupby('created_month').size().reset_index(name='New Employees')
                        monthly_data['month'] = monthly_growth['created_month']
                        monthly_data['New Employees'] = monthly_growth['New Employees']
                    
                    if not promotions_df.empty and 'effective_date' in promotions_df.columns:
                        promotions_df['promo_month'] = pd.to_datetime(promotions_df['effective_date']).dt.strftime('%Y-%m')
                        monthly_promos = promotions_df.groupby('promo_month').size().reset_index(name='Promotions')
                        monthly_data = pd.merge(monthly_data, monthly_promos, left_on='month', right_on='promo_month', how='outer') if not monthly_data.empty else monthly_promos.rename(columns={'promo_month': 'month'})
                        monthly_data['Promotions'] = monthly_data['Promotions'].fillna(0)
                    
                    if not discipline_df.empty and 'created_at' in discipline_df.columns:
                        discipline_df['disc_month'] = pd.to_datetime(discipline_df['created_at']).dt.strftime('%Y-%m')
                        monthly_disc = discipline_df.groupby('disc_month').size().reset_index(name='Discipline Cases')
                        monthly_data = pd.merge(monthly_data, monthly_disc, left_on='month', right_on='disc_month', how='outer') if not monthly_data.empty else monthly_disc.rename(columns={'disc_month': 'month'})
                        monthly_data['Discipline Cases'] = monthly_data['Discipline Cases'].fillna(0)
                    
                    if not leave_df.empty and 'created_at' in leave_df.columns:
                        leave_df['leave_month'] = pd.to_datetime(leave_df['created_at']).dt.strftime('%Y-%m')
                        monthly_leave = leave_df.groupby('leave_month').size().reset_index(name='Unpaid Leave')
                        monthly_data = pd.merge(monthly_data, monthly_leave, left_on='month', right_on='leave_month', how='outer') if not monthly_data.empty else monthly_leave.rename(columns={'leave_month': 'month'})
                        monthly_data['Unpaid Leave'] = monthly_data['Unpaid Leave'].fillna(0)
                    
                    confirm_df = pd.read_sql("SELECT * FROM hr_confirmation", conn) if table_exists else pd.DataFrame()
                    if not confirm_df.empty and 'created_at' in confirm_df.columns:
                        confirm_df['conf_month'] = pd.to_datetime(confirm_df['created_at']).dt.strftime('%Y-%m')
                        monthly_conf = confirm_df.groupby('conf_month').size().reset_index(name='Confirmations')
                        monthly_data = pd.merge(monthly_data, monthly_conf, left_on='month', right_on='conf_month', how='outer') if not monthly_data.empty else monthly_conf.rename(columns={'conf_month': 'month'})
                        monthly_data['Confirmations'] = monthly_data['Confirmations'].fillna(0)
                    
                    if not monthly_data.empty:
                        monthly_data = monthly_data.sort_values('month').fillna(0)
                        monthly_data = monthly_data.set_index('month')
                        
                        fig_monthly = px.line(monthly_data, x=monthly_data.index, y=monthly_data.columns,
                                             title="Monthly HR Activity Trends",
                                             markers=True,
                                             labels={'value': 'Count', 'variable': 'Module', 'month': 'Month'})
                        fig_monthly.update_layout(height=500, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
                        st.plotly_chart(fig_monthly, use_container_width=True)
                        
                        with st.expander("📋 Monthly Data Table"):
                            st.dataframe(monthly_data, use_container_width=True)
                    else:
                        st.info("No monthly trend data available yet")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 7: EMPLOYEE STATUS SUMMARY ====================
                    st.markdown("## 📋 Employee Status Summary")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'department' in employees_df.columns:
                            dept_summary = employees_df.groupby('department').agg({
                                'staff_no': 'count',
                                'age': 'mean' if 'age' in employees_df.columns else None
                            }).reset_index()
                            dept_summary.columns = ['Department', 'Employee Count', 'Average Age'] if 'age' in employees_df.columns else ['Department', 'Employee Count']
                            
                            st.markdown("#### 📊 Department Summary")
                            st.dataframe(dept_summary, use_container_width=True)
                    
                    with col2:
                        st.markdown("#### 📈 Career Progression Summary")
                        if not promotions_df.empty:
                            promo_summary = promotions_df.groupby('staff_no').size().reset_index(name='promotion_count')
                            avg_promotions = promo_summary['promotion_count'].mean()
                            max_promotions = promo_summary['promotion_count'].max()
                            
                            st.metric("Average Promotions per Employee", f"{avg_promotions:.1f}")
                            st.metric("Highest Promotions (Single Employee)", max_promotions)
                            
                            if 'effective_date' in promotions_df.columns:
                                promo_dates = pd.to_datetime(promotions_df['effective_date'])
                                if len(promo_dates) > 1:
                                    avg_interval = (promo_dates.max() - promo_dates.min()).days / len(promo_dates) / 30
                                    st.metric("Average Promotion Interval", f"{avg_interval:.0f} months")
                        else:
                            st.info("No promotion data available")
                    
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        report_data = {
                            'Total Employees': total_employees,
                            'Total Promotions': total_promotions,
                            'Total Discipline Cases': total_discipline,
                            'Employees on Unpaid Leave': total_leave,
                            'Departments': employees_df['department'].nunique() if 'department' in employees_df.columns else 0,
                            'Average Age': employees_df['age'].mean() if 'age' in employees_df.columns else 0,
                            'Gender Ratio': f"{len(employees_df[employees_df['gender']=='Male'])}:{len(employees_df[employees_df['gender']=='Female'])}" if 'gender' in employees_df.columns else 'N/A'
                        }
                        report_df = pd.DataFrame([report_data])
                        csv = report_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download HR Analytics Report (CSV)",
                            csv,
                            f"hr_analytics_report_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                        
        except Exception as e:
            st.info(f"HR Analytics ready. Add employees to see data. ({e})")
    
    # =========================================================
    # STEP 3: TAB 2 - STAFF REGISTRY
    # =========================================================
    with hr_tab2:
        st.subheader("👥 Staff Registry")
        
        def update_employees_table():
            new_columns = [
                ("gender", "TEXT"),
                ("first_designation", "TEXT"),
                ("first_job_group", "TEXT"),
                ("current_designation_date", "TEXT"),
                ("current_designation", "TEXT"),
                ("current_job_group", "TEXT")
            ]
            for col_name, col_type in new_columns:
                try:
                    if is_cloud:
                        cursor.execute(f"ALTER TABLE employees ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                    else:
                        cursor.execute("PRAGMA table_info(employees)")
                        existing_cols = [col[1] for col in cursor.fetchall()]
                        if col_name not in existing_cols:
                            cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
                except Exception as e:
                    pass
            conn.commit()
        
        update_employees_table()
        
        tab_add, tab_view = st.tabs(["➕ Add Staff", "📋 View Staff"])
        
        with tab_add:
            with st.form("add_employee_form_hr"):
                st.markdown("### 📝 Staff Information")
                st.info("Personal Number (National ID) is the unique identifier")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    personal_no = st.text_input("Personal No * (National ID)", placeholder="e.g., 12345678", key="hr_personal_no")
                    name = st.text_input("Full Name *", placeholder="Enter full name", key="hr_name")
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="hr_gender")
                    age = st.number_input("Age", min_value=18, max_value=100, value=30, step=1, key="hr_age")
                
                with col2:
                    department = st.selectbox("Department", 
                        ["Administration", "Finance", "Trade and Tourism", "ICT", "Health", "Education", "Public Works", "Agriculture", "ECRA", "Environment", "Office of The Governor", "Lands", "Other"],
                        key="hr_department")
                    terms_of_service = st.selectbox("Terms of Service", 
                        ["Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"],
                        key="hr_terms_of_service")
                    first_appointment_date = st.date_input("First Date of Appointment", min_value=datetime(1900, 1, 1).date(), max_value=datetime(2100, 12, 31).date(), key="hr_appointment_date")
                    first_designation = st.text_input("First Designation", placeholder="e.g., Assistant Officer", key="hr_first_designation")
                    first_job_group = st.text_input("First Appointment Job Group", placeholder="e.g., JG 'H'", key="hr_first_job_group")
                
                with col3:
                    current_designation_date = st.date_input("Date of Current Designation", min_value=datetime(1900, 1, 1), max_value=datetime(2100, 12, 31), key="hr_current_designation_date")
                    current_designation = st.text_input("Current Designation", placeholder="e.g., Senior Officer", key="hr_current_designation")
                    current_job_group = st.text_input("Current Job Group", placeholder="e.g., JG 'M'", key="hr_current_job_group")
                
                st.markdown("---")
                st.markdown("### 🎓 Qualifications")
                
                col1, col2 = st.columns(2)
                with col1:
                    academic_qualifications = st.text_area("Academic Qualifications", 
                        placeholder="e.g., Bachelor's Degree in Business Administration\nMBA in Strategic Management",
                        height=100, key="hr_academic")
                with col2:
                    professional_qualifications = st.text_area("Professional Qualifications", 
                        placeholder="e.g., CPA(K)\nCISA\nCertified HR Professional",
                        height=100, key="hr_professional")
                
                submitted = st.form_submit_button("💾 Save Employee", use_container_width=True, type="primary")
                
                if submitted:
                    if not personal_no or not name:
                        st.error("Personal No and Name are required!")
                    else:
                        try:
                            if is_cloud:
                                cursor.execute("""
                                    CREATE TABLE IF NOT EXISTS employees (
                                        personal_no TEXT PRIMARY KEY,
                                        name TEXT,
                                        gender TEXT,
                                        age INTEGER,
                                        department TEXT,
                                        terms_of_service TEXT,
                                        first_appointment_date TEXT,
                                        first_designation TEXT,
                                        first_job_group TEXT,
                                        current_designation_date TEXT,
                                        current_designation TEXT,
                                        current_job_group TEXT,
                                        academic_qualifications TEXT,
                                        professional_qualifications TEXT,
                                        created_at TEXT,
                                        created_by TEXT
                                    )
                                """)
                            else:
                                cursor.execute("""
                                    CREATE TABLE IF NOT EXISTS employees (
                                        personal_no TEXT PRIMARY KEY,
                                        name TEXT,
                                        gender TEXT,
                                        age INTEGER,
                                        department TEXT,
                                        terms_of_service TEXT,
                                        first_appointment_date TEXT,
                                        first_designation TEXT,
                                        first_job_group TEXT,
                                        current_designation_date TEXT,
                                        current_designation TEXT,
                                        current_job_group TEXT,
                                        academic_qualifications TEXT,
                                        professional_qualifications TEXT,
                                        created_at TEXT,
                                        created_by TEXT
                                    )
                                """)
                            conn.commit()
                            
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            username = st.session_state.user['username']
                            
                            if is_cloud:
                                cursor.execute("SELECT personal_no FROM employees WHERE personal_no = %s", (personal_no,))
                            else:
                                cursor.execute("SELECT personal_no FROM employees WHERE personal_no = ?", (personal_no,))
                            
                            if cursor.fetchone():
                                if is_cloud:
                                    cursor.execute("""
                                        UPDATE employees SET
                                            name = %s, gender = %s, age = %s, department = %s,
                                            terms_of_service = %s,
                                            first_appointment_date = %s, first_designation = %s,
                                            first_job_group = %s, current_designation_date = %s,
                                            current_designation = %s, current_job_group = %s,
                                            academic_qualifications = %s, professional_qualifications = %s
                                        WHERE personal_no = %s
                                    """, (name, gender, age, department, terms_of_service,
                                          first_appointment_date.strftime("%Y-%m-%d") if first_appointment_date else None,
                                          first_designation, first_job_group,
                                          current_designation_date.strftime("%Y-%m-%d") if current_designation_date else None,
                                          current_designation, current_job_group,
                                          academic_qualifications, professional_qualifications, personal_no))
                                else:
                                    cursor.execute("""
                                        UPDATE employees SET
                                            name = ?, gender = ?, age = ?, department = ?,
                                            terms_of_service = ?,
                                            first_appointment_date = ?, first_designation = ?,
                                            first_job_group = ?, current_designation_date = ?,
                                            current_designation = ?, current_job_group = ?,
                                            academic_qualifications = ?, professional_qualifications = ?
                                        WHERE personal_no = ?
                                    """, (name, gender, age, department, terms_of_service,
                                          first_appointment_date.strftime("%Y-%m-%d") if first_appointment_date else None,
                                          first_designation, first_job_group,
                                          current_designation_date.strftime("%Y-%m-%d") if current_designation_date else None,
                                          current_designation, current_job_group,
                                          academic_qualifications, professional_qualifications, personal_no))
                                st.success(f"✅ Employee {name} updated successfully!")
                            else:
                                if is_cloud:
                                    cursor.execute("""
                                        INSERT INTO employees (
                                            personal_no, name, gender, age, department, terms_of_service,
                                            first_appointment_date, first_designation, first_job_group,
                                            current_designation_date, current_designation, current_job_group,
                                            academic_qualifications, professional_qualifications,
                                            created_at, created_by
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (personal_no, name, gender, age, department, terms_of_service,
                                          first_appointment_date.strftime("%Y-%m-%d") if first_appointment_date else None,
                                          first_designation, first_job_group,
                                          current_designation_date.strftime("%Y-%m-%d") if current_designation_date else None,
                                          current_designation, current_job_group,
                                          academic_qualifications, professional_qualifications,
                                          now, username))
                                else:
                                    cursor.execute("""
                                        INSERT INTO employees (
                                            personal_no, name, gender, age, department, terms_of_service,
                                            first_appointment_date, first_designation, first_job_group,
                                            current_designation_date, current_designation, current_job_group,
                                            academic_qualifications, professional_qualifications,
                                            created_at, created_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (personal_no, name, gender, age, department, terms_of_service,
                                          first_appointment_date.strftime("%Y-%m-%d") if first_appointment_date else None,
                                          first_designation, first_job_group,
                                          current_designation_date.strftime("%Y-%m-%d") if current_designation_date else None,
                                          current_designation, current_job_group,
                                          academic_qualifications, professional_qualifications,
                                          now, username))
                                st.success(f"✅ Employee {name} added successfully!")
                            
                            conn.commit()
                            log_audit(
                                username=st.session_state.user['username'],
                                action="ADD_STAFF",
                                record_id=0,
                                details=f"Added new staff: {name} (Personal No: {personal_no}) - Department: {department}",
                                status="Success"
                            )
                            st.success(f"✅ New employee {name} added!")
                            st.balloons()
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error: {e}")
        
        with tab_view:
            st.markdown("### 🔍 Search Staff")
            st.info("Search for staff members using any of the criteria below")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_name = st.text_input("Search by Name", placeholder="Enter full or partial name...", key="search_name")
                search_personal_no = st.text_input("Search by Personal No (ID)", placeholder="Enter ID number...", key="search_personal")
                search_terms = st.selectbox("Terms of Service", 
                    ["All", "Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"],
                    key="search_terms")
            
            with col2:
                search_department = st.selectbox("Filter by Department", 
                    ["All Departments", "Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Lands", "Trade and Tourism", "ECRA", "Water", "Environment", "Gender", "Youth", "Cooperative", "Energy", "Transport", "Legal", "Audit", "Procurement", "Other"],
                    key="search_department")
                search_gender = st.selectbox("Filter by Gender", ["All", "Male", "Female", "Other"], key="search_gender")
                search_job_group = st.text_input("Search by Job Group", placeholder="e.g., JG H, JG M", key="search_job_group")
            
            with col3:
                search_designation = st.text_input("Search by Designation", placeholder="Enter designation...", key="search_designation")
                min_age = st.number_input("Minimum Age", min_value=18, max_value=100, value=18, key="min_age")
                max_age = st.number_input("Maximum Age", min_value=18, max_value=100, value=100, key="max_age")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                search_clicked = st.button("🔍 Search Staff", use_container_width=True, type="primary")
            
            with col1:
                if st.button("🗑️ Clear Search", use_container_width=True):
                    if 'search_results' in st.session_state:
                        del st.session_state.search_results
                    if 'search_performed' in st.session_state:
                        del st.session_state.search_performed
                    st.rerun()
            
            if search_clicked:
                query = "SELECT * FROM employees WHERE 1=1"
                params = []
                
                if search_name:
                    if is_cloud:
                        query += " AND name ILIKE %s"
                    else:
                        query += " AND name LIKE ?"
                    params.append(f"%{search_name}%")
                
                if search_personal_no:
                    if is_cloud:
                        query += " AND personal_no::TEXT = %s"
                    else:
                        query += " AND personal_no = ?"
                    params.append(search_personal_no)
                
                if search_department != "All Departments":
                    if is_cloud:
                        query += " AND department = %s"
                    else:
                        query += " AND department = ?"
                    params.append(search_department)
                
                if search_gender != "All":
                    if is_cloud:
                        query += " AND gender = %s"
                    else:
                        query += " AND gender = ?"
                    params.append(search_gender)
                
                if search_terms != "All":
                    if is_cloud:
                        query += " AND terms_of_service = %s"
                    else:
                        query += " AND terms_of_service = ?"
                    params.append(search_terms)
                
                if search_job_group:
                    if is_cloud:
                        query += " AND (current_job_group ILIKE %s OR first_job_group ILIKE %s)"
                    else:
                        query += " AND (current_job_group LIKE ? OR first_job_group LIKE ?)"
                    params.extend([f"%{search_job_group}%", f"%{search_job_group}%"])
                
                if search_designation:
                    if is_cloud:
                        query += " AND (current_designation ILIKE %s OR first_designation ILIKE %s)"
                    else:
                        query += " AND (current_designation LIKE ? OR first_designation LIKE ?)"
                    params.extend([f"%{search_designation}%", f"%{search_designation}%"])
                
                if min_age > 18 or max_age < 100:
                    if is_cloud:
                        query += " AND age BETWEEN %s AND %s"
                    else:
                        query += " AND age BETWEEN ? AND ?"
                    params.extend([min_age, max_age])
                
                query += " ORDER BY name"
                
                try:
                    if is_cloud:
                        results_df = pd.read_sql(query, conn, params=tuple(params))
                    else:
                        results_df = pd.read_sql(query, conn, params=tuple(params))
                    
                    st.session_state.search_results = results_df
                    st.session_state.search_performed = True
                    
                    if 'editing_staff' in st.session_state:
                        del st.session_state.editing_staff
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error searching staff: {e}")
                    st.session_state.search_results = pd.DataFrame()
                    st.session_state.search_performed = True
            
            if 'editing_staff' in st.session_state and st.session_state.editing_staff:
                st.markdown("---")
                st.subheader("✏️ Edit Staff Details")
                
                personal_no_edit = str(st.session_state.editing_staff).split('.')[0]
                
                if is_cloud:
                    edit_query = "SELECT * FROM employees WHERE personal_no::TEXT = %s"
                    edit_df = pd.read_sql(edit_query, conn, params=(personal_no_edit,))
                else:
                    edit_df = pd.read_sql(f"SELECT * FROM employees WHERE personal_no = '{personal_no_edit}'", conn)
                
                if not edit_df.empty:
                    emp = edit_df.iloc[0]
                    
                    with st.form("edit_employee_form"):
                        st.markdown(f"### Editing: {emp['name']}")
                        
                        personal_no_clean = str(emp['personal_no']).split('.')[0] if emp['personal_no'] else ''
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.text_input("Personal No (National ID)", value=personal_no_clean, disabled=True, key="edit_personal_no")
                            name = st.text_input("Full Name", value=emp['name'] if emp['name'] else "", key="edit_name")
                            gender = st.selectbox("Gender", ["Male", "Female", "Other"], 
                                                  index=["Male", "Female", "Other"].index(emp['gender']) if emp['gender'] in ["Male", "Female", "Other"] else 0,
                                                  key="edit_gender")
                            age = st.number_input("Age", min_value=18, max_value=100, 
                                                  value=int(float(emp['age'])) if emp['age'] else 30, step=1, key="edit_age")
                        
                        with col2:
                            department = st.selectbox("Department", 
                                ["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Lands", "Trade", "Tourism", "Water", "Environment", "Gender", "Youth", "Cooperative", "Energy", "Transport", "Legal", "Audit", "Procurement", "Other"],
                                index=["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Lands", "Trade", "Tourism", "Water", "Environment", "Gender", "Youth", "Cooperative", "Energy", "Transport", "Legal", "Audit", "Procurement", "Other"].index(emp['department']) if emp['department'] in ["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Lands", "Trade", "Tourism", "Water", "Environment", "Gender", "Youth", "Cooperative", "Energy", "Transport", "Legal", "Audit", "Procurement", "Other"] else 0,
                                key="edit_department")
                            
                            try:
                                current_terms = emp['terms_of_service'] if pd.notna(emp.get('terms_of_service')) else "Permanent"
                            except:
                                current_terms = "Permanent"
                            
                            terms_options = ["Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"]
                            terms_index = terms_options.index(current_terms) if current_terms in terms_options else 0
                            
                            terms_of_service = st.selectbox("Terms of Service", 
                                terms_options,
                                index=terms_index,
                                key="edit_terms_of_service")
                            
                            first_appointment_date = None
                            if emp['first_appointment_date'] and emp['first_appointment_date'] != 'None':
                                try:
                                    first_appointment_date = pd.to_datetime(emp['first_appointment_date']).date()
                                except:
                                    first_appointment_date = datetime.now().date()
                            else:
                                first_appointment_date = datetime.now().date()
                            
                            first_appointment_date = st.date_input("First Date of Appointment", value=first_appointment_date, min_value=datetime(1900, 1, 1).date(), max_value=datetime(2100, 12, 31).date(), key="edit_appointment_date")
                            first_designation = st.text_input("First Designation", value=emp['first_designation'] if emp['first_designation'] else "", key="edit_first_designation")
                            first_job_group = st.text_input("First Appointment Job Group", value=emp['first_job_group'] if emp['first_job_group'] else "", key="edit_first_job_group")
                        
                        with col3:
                            current_designation_date = None
                            if emp['current_designation_date'] and emp['current_designation_date'] != 'None':
                                try:
                                    current_designation_date = pd.to_datetime(emp['current_designation_date']).date()
                                except:
                                    current_designation_date = datetime.now().date()
                            else:
                                current_designation_date = datetime.now().date()
                            
                            current_designation_date = st.date_input("Date of Current Designation", value=current_designation_date, min_value=datetime(1900, 1, 1).date(), max_value=datetime(2100, 12, 31).date(), key="edit_current_date")
                            current_designation = st.text_input("Current Designation", value=emp['current_designation'] if emp['current_designation'] else "", key="edit_current_designation")
                            current_job_group = st.text_input("Current Job Group", value=emp['current_job_group'] if emp['current_job_group'] else "", key="edit_current_job_group")
                        
                        st.markdown("---")
                        st.markdown("### 🎓 Qualifications")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            academic_qualifications = st.text_area("Academic Qualifications", 
                                value=emp['academic_qualifications'] if emp['academic_qualifications'] else "",
                                height=100, key="edit_academic")
                        with col2:
                            professional_qualifications = st.text_area("Professional Qualifications", 
                                value=emp['professional_qualifications'] if emp['professional_qualifications'] else "",
                                height=100, key="edit_professional")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                                try:
                                    if is_cloud:
                                        cursor.execute("""
                                            UPDATE employees SET
                                                name = %s, gender = %s, age = %s, department = %s,
                                                terms_of_service = %s,
                                                first_appointment_date = %s, first_designation = %s,
                                                first_job_group = %s, current_designation_date = %s,
                                                current_designation = %s, current_job_group = %s,
                                                academic_qualifications = %s, professional_qualifications = %s
                                            WHERE personal_no::TEXT = %s
                                        """, (name, gender, age, department, terms_of_service,
                                              first_appointment_date.strftime("%Y-%m-%d"),
                                              first_designation, first_job_group,
                                              current_designation_date.strftime("%Y-%m-%d"),
                                              current_designation, current_job_group,
                                              academic_qualifications, professional_qualifications, personal_no_edit))
                                    else:
                                        cursor.execute("""
                                            UPDATE employees SET
                                                name = ?, gender = ?, age = ?, department = ?,
                                                terms_of_service = ?,
                                                first_appointment_date = ?, first_designation = ?,
                                                first_job_group = ?, current_designation_date = ?,
                                                current_designation = ?, current_job_group = ?,
                                                academic_qualifications = ?, professional_qualifications = ?
                                            WHERE personal_no = ?
                                        """, (name, gender, age, department, terms_of_service,
                                              first_appointment_date.strftime("%Y-%m-%d"),
                                              first_designation, first_job_group,
                                              current_designation_date.strftime("%Y-%m-%d"),
                                              current_designation, current_job_group,
                                              academic_qualifications, professional_qualifications, personal_no_edit))
                                    conn.commit()
                                    
                                    log_audit(
                                        username=st.session_state.user['username'],
                                        action="EDIT_STAFF",
                                        record_id=0,
                                        details=f"Edited staff: {name} (Personal No: {personal_no_edit}) - Terms: {terms_of_service}",
                                        status="Success"
                                    )
                                    
                                    st.success(f"✅ Employee {name} updated successfully!")
                                    del st.session_state.editing_staff
                                    if 'search_results' in st.session_state:
                                        del st.session_state.search_results
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating employee: {e}")
                        
                        with col2:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                del st.session_state.editing_staff
                                st.rerun()
                else:
                    st.error("Staff record not found")
                    del st.session_state.editing_staff
                    st.rerun()
                
                st.markdown("---")
            
            if 'search_results' in st.session_state and st.session_state.search_performed:
                results_df = st.session_state.search_results
                
                if results_df.empty:
                    st.warning("No staff records found matching your search criteria.")
                else:
                    st.markdown("---")
                    st.subheader("📋 Search Results")
                    st.success(f"✅ Found {len(results_df)} staff record(s)")
                    
                    for idx, row in results_df.iterrows():
                        personal_no_clean = str(row['personal_no']).split('.')[0] if row['personal_no'] else ''
                        unique_suffix = f"{idx}_{hash(row['name'])}_{hash(personal_no_clean)}"
                        edit_key = f"edit_{unique_suffix}"
                        delete_key = f"delete_{unique_suffix}"
                        
                        with st.container():
                            col1, col2, col3, col4, col5, col6 = st.columns([2.5, 1.5, 1, 1.5, 0.8, 0.8])
                            with col1:
                                st.write(f"**{row['name']}**")
                            with col2:
                                st.write(f"ID: {personal_no_clean}")
                            with col3:
                                st.write(f"Age: {int(float(row['age'])) if row['age'] else 'N/A'}")
                            with col4:
                                st.write(f"Dept: {row['department'][:15] if row['department'] else 'N/A'}")
                            with col5:
                                if st.button("✏️ Edit", key=edit_key, use_container_width=True):
                                    st.session_state.editing_staff = row['personal_no']
                                    st.rerun()
                            with col6:
                                if st.button("🗑️ Delete", key=delete_key, use_container_width=True):
                                    st.session_state.delete_target = row['personal_no']
                                    st.session_state.delete_name = row['name']
                                    st.rerun()
                            st.divider()
                    
                    if 'delete_target' in st.session_state:
                        st.warning(f"⚠️ Are you sure you want to delete **{st.session_state.delete_name}**?")
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            if st.button("✅ Yes, Delete", key="confirm_delete_yes", use_container_width=True):
                                try:
                                    if is_cloud:
                                        cursor.execute("DELETE FROM employees WHERE personal_no::TEXT = %s", (str(st.session_state.delete_target).split('.')[0],))
                                    else:
                                        cursor.execute("DELETE FROM employees WHERE personal_no = ?", (str(st.session_state.delete_target).split('.')[0],))
                                    conn.commit()
                                    st.success(f"✅ Employee {st.session_state.delete_name} deleted successfully!")
                                    del st.session_state.delete_target
                                    del st.session_state.delete_name
                                    if 'search_results' in st.session_state:
                                        del st.session_state.search_results
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting employee: {e}")
                        with col2:
                            if st.button("❌ Cancel", key="confirm_delete_no", use_container_width=True):
                                del st.session_state.delete_target
                                del st.session_state.delete_name
                                st.rerun()
                        st.markdown("---")
                    
                    with st.expander("📊 View as Table"):
                        display_cols = ['personal_no', 'name', 'gender', 'age', 'department', 'terms_of_service', 
                                       'current_designation', 'current_job_group', 'first_appointment_date']
                        available_cols = [col for col in display_cols if col in results_df.columns]
                        display_df = results_df[available_cols].copy()
                        
                        if 'personal_no' in display_df.columns:
                            display_df['personal_no'] = display_df['personal_no'].apply(lambda x: str(x).split('.')[0] if x else '')
                        
                        display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
                        display_df = display_df.rename(columns={
                            'Personal No': 'Personal No',
                            'Name': 'Name',
                            'Gender': 'Gender',
                            'Age': 'Age',
                            'Department': 'Department',
                            'Terms Of Service': 'Terms of Service',
                            'Current Designation': 'Current Designation',
                            'Current Job Group': 'Current Job Group',
                            'First Appointment Date': 'First Appointment Date'
                        })
                        
                        st.dataframe(display_df, use_container_width=True)
                        
                        csv = results_df.to_csv(index=False).encode('utf-8')
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                "📥 Download Search Results (CSV)",
                                csv,
                                f"staff_search_results_{datetime.now().strftime('%Y%m%d')}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        with col2:
                            if st.button("🔄 Clear Results", use_container_width=True):
                                del st.session_state.search_results
                                del st.session_state.search_performed
                                st.rerun()
            
            elif 'search_performed' not in st.session_state and 'editing_staff' not in st.session_state:
                st.info("👆 Use the search filters above to find staff members. Click the Edit button to modify staff details or Delete to remove a record.")
    
    # ==================== TAB 3: IMPORT STAFF ====================
    with hr_tab3:
        st.subheader("📥 Import Staff Data")
        st.info("Upload an Excel or CSV file to import staff records. Personal No (National ID) and Name are required.")
        
        template_df = pd.DataFrame({
            'Personal No': ['12345678', '87654321'],
            'Name': ['John Doe', 'Jane Smith'],
            'Gender': ['Male', 'Female'],
            'Age': [35, 28],
            'Department': ['Administration', 'Finance'],
            'First Date of Appointment': ['2020-01-15', '2021-03-20'],
            'First Designation': ['Assistant Officer', 'Junior Accountant'],
            'First Appointment Job Group': ['JG H', 'JG G'],
            'Date of Current Designation': ['2023-01-15', '2024-03-20'],
            'Current Designation': ['Senior Officer', 'Accountant'],
            'Current Job Group': ['JG M', 'JG L'],
            'Academic Qualifications': ['MBA - University of Nairobi', 'BCom - Kenyatta University'],
            'Professional Qualifications': ['CPA(K), CISA', 'CPA Section 4']
        })
        
        col1, col2 = st.columns(2)
        with col1:
            csv_data = template_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV Template", csv_data, "staff_import_template.csv", "text/csv", use_container_width=True)
        with col2:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, sheet_name='Staff', index=False)
            st.download_button("📥 Download Excel Template", output.getvalue(), "staff_import_template.xlsx", 
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        
        st.markdown("---")
        
        uploaded_file = st.file_uploader("Choose Excel or CSV file", type=["xlsx", "xls", "csv"], key="hr_import")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    import_df = pd.read_csv(uploaded_file)
                else:
                    import_df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ File loaded! {len(import_df)} rows found")
                
                with st.expander("📊 Preview uploaded data"):
                    st.dataframe(import_df.head(10), use_container_width=True)
                
                column_mapping = {
                    'personal no': 'personal_no',
                    'personal number': 'personal_no',
                    'id number': 'personal_no',
                    'national id': 'personal_no',
                    'name': 'name',
                    'full name': 'name',
                    'employee name': 'name',
                    'gender': 'gender',
                    'age': 'age',
                    'department': 'department',
                    'first appointment date': 'first_appointment_date',
                    'appointment date': 'first_appointment_date',
                    'first designation': 'first_designation',
                    'first appointment job group': 'first_job_group',
                    'date of current designation': 'current_designation_date',
                    'current designation': 'current_designation',
                    'current job group': 'current_job_group',
                    'academic qualifications': 'academic_qualifications',
                    'academic': 'academic_qualifications',
                    'professional qualifications': 'professional_qualifications',
                    'professional': 'professional_qualifications'
                }
                
                import_df.columns = import_df.columns.str.lower().str.strip()
                for col in import_df.columns:
                    if col in column_mapping:
                        import_df = import_df.rename(columns={col: column_mapping[col]})
                
                if 'personal_no' not in import_df.columns or 'name' not in import_df.columns:
                    st.error("❌ Required columns 'Personal No' and 'Name' not found in the file!")
                    st.info("Please ensure your file has columns: Personal No (National ID) and Name")
                else:
                    preview_df = import_df[['personal_no', 'name']].copy()
                    st.write("**Preview of required fields:**")
                    st.dataframe(preview_df.head(10), use_container_width=True)
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("🚀 IMPORT STAFF", use_container_width=True, type="primary"):
                            inserted = 0
                            skipped = 0
                            errors = []
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for idx, row in import_df.iterrows():
                                try:
                                    personal_no = str(row['personal_no']).strip() if pd.notna(row['personal_no']) else ''
                                    name = str(row['name']).strip() if pd.notna(row['name']) else ''
                                    
                                    if not personal_no or personal_no == 'nan' or not name or name == 'nan':
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: Missing Personal No or Name")
                                        continue
                                    
                                    gender = str(row['gender']).strip() if 'gender' in import_df.columns and pd.notna(row['gender']) else ''
                                    age = int(row['age']) if 'age' in import_df.columns and pd.notna(row['age']) else 0
                                    department = str(row['department']).strip() if 'department' in import_df.columns and pd.notna(row['department']) else ''
                                    first_appointment_date = str(row['first_appointment_date']).strip() if 'first_appointment_date' in import_df.columns and pd.notna(row['first_appointment_date']) else ''
                                    first_designation = str(row['first_designation']).strip() if 'first_designation' in import_df.columns and pd.notna(row['first_designation']) else ''
                                    first_job_group = str(row['first_job_group']).strip() if 'first_job_group' in import_df.columns and pd.notna(row['first_job_group']) else ''
                                    current_designation_date = str(row['current_designation_date']).strip() if 'current_designation_date' in import_df.columns and pd.notna(row['current_designation_date']) else ''
                                    current_designation = str(row['current_designation']).strip() if 'current_designation' in import_df.columns and pd.notna(row['current_designation']) else ''
                                    current_job_group = str(row['current_job_group']).strip() if 'current_job_group' in import_df.columns and pd.notna(row['current_job_group']) else ''
                                    academic_qualifications = str(row['academic_qualifications']).strip() if 'academic_qualifications' in import_df.columns and pd.notna(row['academic_qualifications']) else ''
                                    professional_qualifications = str(row['professional_qualifications']).strip() if 'professional_qualifications' in import_df.columns and pd.notna(row['professional_qualifications']) else ''
                                    
                                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    username = st.session_state.user['username']
                                    
                                    if is_cloud:
                                        cursor.execute("SELECT personal_no FROM employees WHERE personal_no = %s", (personal_no,))
                                    else:
                                        cursor.execute("SELECT personal_no FROM employees WHERE personal_no = ?", (personal_no,))
                                    
                                    if cursor.fetchone():
                                        if is_cloud:
                                            cursor.execute("""
                                                UPDATE employees SET
                                                    name = %s, gender = %s, age = %s, department = %s,
                                                    first_appointment_date = %s, first_designation = %s,
                                                    first_job_group = %s, current_designation_date = %s,
                                                    current_designation = %s, current_job_group = %s,
                                                    academic_qualifications = %s, professional_qualifications = %s
                                                WHERE personal_no = %s
                                            """, (name, gender, age, department,
                                                  first_appointment_date if first_appointment_date else None,
                                                  first_designation, first_job_group,
                                                  current_designation_date if current_designation_date else None,
                                                  current_designation, current_job_group,
                                                  academic_qualifications, professional_qualifications, personal_no))
                                        else:
                                            cursor.execute("""
                                                UPDATE employees SET
                                                    name = ?, gender = ?, age = ?, department = ?,
                                                    first_appointment_date = ?, first_designation = ?,
                                                    first_job_group = ?, current_designation_date = ?,
                                                    current_designation = ?, current_job_group = ?,
                                                    academic_qualifications = ?, professional_qualifications = ?
                                                WHERE personal_no = ?
                                            """, (name, gender, age, department,
                                                  first_appointment_date if first_appointment_date else None,
                                                  first_designation, first_job_group,
                                                  current_designation_date if current_designation_date else None,
                                                  current_designation, current_job_group,
                                                  academic_qualifications, professional_qualifications, personal_no))
                                        st.info(f"Updated existing record: {personal_no} - {name}")
                                    else:
                                        if is_cloud:
                                            cursor.execute("""
                                                INSERT INTO employees (
                                                    personal_no, name, gender, age, department,
                                                    first_appointment_date, first_designation, first_job_group,
                                                    current_designation_date, current_designation, current_job_group,
                                                    academic_qualifications, professional_qualifications,
                                                    created_at, created_by
                                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                            """, (personal_no, name, gender, age, department,
                                                  first_appointment_date if first_appointment_date else None,
                                                  first_designation, first_job_group,
                                                  current_designation_date if current_designation_date else None,
                                                  current_designation, current_job_group,
                                                  academic_qualifications, professional_qualifications,
                                                  now, username))
                                        else:
                                            cursor.execute("""
                                                INSERT INTO employees (
                                                    personal_no, name, gender, age, department,
                                                    first_appointment_date, first_designation, first_job_group,
                                                    current_designation_date, current_designation, current_job_group,
                                                    academic_qualifications, professional_qualifications,
                                                    created_at, created_by
                                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                            """, (personal_no, name, gender, age, department,
                                                  first_appointment_date if first_appointment_date else None,
                                                  first_designation, first_job_group,
                                                  current_designation_date if current_designation_date else None,
                                                  current_designation, current_job_group,
                                                  academic_qualifications, professional_qualifications,
                                                  now, username))
                                        st.success(f"✅ New employee {name} added!")
                                    
                                    inserted += 1
                                    progress_bar.progress((idx + 1) / len(import_df))
                                    status_text.text(f"Processing: {idx+1}/{len(import_df)} | ✅ Inserted: {inserted} | ⚠️ Skipped: {skipped}")
                                    
                                except Exception as e:
                                    skipped += 1
                                    errors.append(f"Row {idx+2}: {str(e)[:100]}")
                            
                            conn.commit()
                            
                            st.success(f"✅ Import completed! {inserted} records processed.")
                            if skipped > 0:
                                st.warning(f"⚠️ Skipped {skipped} rows")
                                if errors:
                                    with st.expander(f"📋 View {len(errors)} errors"):
                                        for err in errors[:20]:
                                            st.write(f"- {err}")
                            
                            if inserted > 0:
                                st.balloons()
                                st.rerun()
                            
                            log_audit(
                                username=st.session_state.user['username'],
                                action="IMPORT_STAFF",
                                record_id=0,
                                details=f"Imported {inserted} staff records from file. Skipped: {skipped}",
                                status="Success"
                            )
                            st.success(f"✅ Import completed! {inserted} records processed.")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
                st.info("Please make sure your file matches the template format.")
    
    # ==================== TAB 4: PROMOTIONS ====================
    with hr_tab4:
        st.subheader("📈 Promotions Management")
        
        promo_subtab1, promo_subtab2 = st.tabs([
            "🏢 Common Establishment",
            "🎯 Internal Recruitment"
        ])
        
        with promo_subtab1:
            st.markdown("### 🏢 Common Establishment")
            st.info("Process promotions through the standard establishment workflow")
            
            try:
                employees_df = pd.read_sql("SELECT staff_no, name, current_designation, current_job_group FROM employees ORDER BY name", conn)
                if not employees_df.empty:
                    employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']} (Current: {row['current_designation']})" for _, row in employees_df.iterrows()]
                    selected_employee = st.selectbox("Select Staff", employee_options, key="hr_promo_employee")
                    
                    if selected_employee != "Select employee...":
                        staff_no = selected_employee.split(" - ")[0]
                        employee = employees_df[employees_df['staff_no'] == staff_no].iloc[0]
                        
                        with st.form("promotion_form"):
                            col1, col2 = st.columns(2)
                            with col1:
                                old_designation = st.text_input("Old Designation", value=employee['current_designation'], disabled=True)
                                new_designation = st.text_input("New Designation *", key="hr_promo_designation")
                                old_job_group = st.text_input("Old Job Group", value=employee['current_job_group'], disabled=True)
                                new_job_group = st.text_input("New Job Group", key="hr_promo_job_group")
                            with col2:
                                effective_date = st.date_input("Effective Date", key="hr_promo_date")
                                reason = st.text_area("Reason for Promotion", key="hr_promo_reason")
                            
                            st.markdown("### 📋 Approval Minutes")
                            col1, col2 = st.columns(2)
                            with col1:
                                chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="hr_promo_chrmac_min")
                                chrmac_date = st.date_input("Date of CHRMAC", key="hr_promo_chrmac_date")
                            with col2:
                                cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="hr_promo_cpsb_min")
                                cpsb_date = st.date_input("Date of CPSB", key="hr_promo_cpsb_date")
                            
                            if st.form_submit_button("Process Promotion", use_container_width=True, type="primary"):
                                if new_designation:
                                    if is_cloud:
                                        cursor.execute("""
                                            UPDATE employees 
                                            SET current_designation = %s, current_job_group = %s,
                                                current_designation_date = %s
                                            WHERE staff_no = %s
                                        """, (new_designation, new_job_group if new_job_group else employee['current_job_group'], 
                                              effective_date.strftime("%Y-%m-%d"), staff_no))
                                    else:
                                        cursor.execute("""
                                            UPDATE employees 
                                            SET current_designation = ?, current_job_group = ?,
                                                current_designation_date = ?
                                            WHERE staff_no = ?
                                        """, (new_designation, new_job_group if new_job_group else employee['current_job_group'], 
                                              effective_date.strftime("%Y-%m-%d"), staff_no))
                                    conn.commit()
                                    
                                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                                    cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                                    
                                    if is_cloud:
                                        cursor.execute("""
                                            INSERT INTO hr_promotions (
                                                staff_no, old_designation, new_designation, old_job_group, new_job_group,
                                                effective_date, reason, chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                                created_at, created_by
                                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """, (staff_no, employee['current_designation'], new_designation,
                                              employee['current_job_group'], new_job_group,
                                              effective_date.strftime("%Y-%m-%d"), reason,
                                              chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                              now, st.session_state.user['username']))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO hr_promotions (
                                                staff_no, old_designation, new_designation, old_job_group, new_job_group,
                                                effective_date, reason, chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                                created_at, created_by
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (staff_no, employee['current_designation'], new_designation,
                                              employee['current_job_group'], new_job_group,
                                              effective_date.strftime("%Y-%m-%d"), reason,
                                              chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                              now, st.session_state.user['username']))
                                    conn.commit()
                                    
                                    log_audit(
                                        st.session_state.user['username'],
                                        "PROMOTION",
                                        0,
                                        f"Promoted {employee['name']} from {old_designation} ({employee['current_job_group']}) to {new_designation} ({new_job_group})",
                                        "Success"
                                    )
                                    st.success(f"✅ Promotion processed for {employee['name']}!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.warning("Please enter the new designation")
                else:
                    st.warning("No employees found. Please add employees in Staff Registry first.")
            except Exception as e:
                st.info(f"Add employees to enable promotions. ({e})")
        
        with promo_subtab2:
            st.markdown("### 🎯 Internal Recruitment")
            st.info("Shortlist internal staff candidates for advertised positions")
            
            st.markdown("#### Step 1: Select Advertised Position")
            
            try:
                if is_cloud:
                    positions_df = pd.read_sql("""
                        SELECT id, position_title, position_code, department, vacancies 
                        FROM advertised_positions 
                        WHERE status = 'Open'
                        ORDER BY position_title
                    """, conn)
                else:
                    positions_df = pd.read_sql("""
                        SELECT id, position_title, position_code, department, vacancies 
                        FROM advertised_positions 
                        WHERE status = 'Open'
                        ORDER BY position_title
                    """, conn)
            except Exception as e:
                st.error(f"Error loading positions: {e}")
                positions_df = pd.DataFrame()
            
            if positions_df.empty:
                st.warning("⚠️ No open advertised positions found. Please create a position in Settings > Advertised Positions first.")
            else:
                position_options = ["Select a position..."] + [
                    f"{row['position_title']} ({row['position_code']})" 
                    for _, row in positions_df.iterrows()
                ]
                
                selected_position_display = st.selectbox(
                    "Search and select advertised position",
                    position_options,
                    key="internal_recruitment_position"
                )
                
                if selected_position_display != "Select a position...":
                    selected_code = selected_position_display.split(" (")[1].split(")")[0] if "(" in selected_position_display else ""
                    selected_position = positions_df[positions_df['position_code'] == selected_code]
                    
                    if not selected_position.empty:
                        selected_position_row = selected_position.iloc[0]
                        position_id = selected_position_row['id']
                        position_title = selected_position_row['position_title']
                        position_code = selected_position_row['position_code']
                        department = selected_position_row['department']
                        
                        st.info(f"📌 **Selected Position:** {position_title} | **Code:** {position_code} | **Department:** {department}")
                        
                        st.markdown("---")
                        st.markdown("#### Step 2: Select Staff")
                        
                        employees_df = pd.read_sql("SELECT staff_no, name, current_designation, current_job_group, department FROM employees ORDER BY name", conn)
                        
                        if not employees_df.empty:
                            staff_search = st.text_input(
                                "Search by Name or Staff No",
                                placeholder="Type name or staff number...",
                                key="internal_recruitment_staff_search"
                            )
                            
                            staff_df = employees_df.copy()
                            if staff_search:
                                staff_df = staff_df[
                                    staff_df['name'].str.contains(staff_search, case=False, na=False) |
                                    staff_df['staff_no'].str.contains(staff_search, case=False, na=False)
                                ]
                            
                            if not staff_df.empty:
                                staff_options = ["Select staff member..."] + [
                                    f"{row['staff_no']} - {row['name']} (Current: {row['current_designation']})" 
                                    for _, row in staff_df.iterrows()
                                ]
                                
                                selected_staff = st.selectbox(
                                    "Select staff member for internal recruitment",
                                    staff_options,
                                    key="internal_recruitment_staff"
                                )
                                
                                if selected_staff != "Select staff member...":
                                    staff_no = selected_staff.split(" - ")[0]
                                    staff_member = staff_df[staff_df['staff_no'] == staff_no].iloc[0]
                                    
                                    st.markdown("---")
                                    st.markdown("#### 👤 Staff Details")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.text_input("Staff No", value=staff_member['staff_no'], disabled=True)
                                        st.text_input("Name", value=staff_member['name'], disabled=True)
                                    with col2:
                                        st.text_input("Current Designation", value=staff_member['current_designation'], disabled=True)
                                        st.text_input("Current Job Group", value=staff_member['current_job_group'], disabled=True)
                                    with col3:
                                        st.text_input("Department", value=staff_member['department'], disabled=True)
                                        id_number = staff_member.get('personal_no', 'N/A')
                                        st.text_input("ID Number", value=id_number, disabled=True)
                                    
                                    if is_cloud:
                                        cursor.execute("""
                                            SELECT id FROM internal_recruitment_candidates 
                                            WHERE staff_no = %s AND position_id = %s
                                        """, (staff_no, position_id))
                                    else:
                                        cursor.execute("""
                                            SELECT id FROM internal_recruitment_candidates 
                                            WHERE staff_no = ? AND position_id = ?
                                        """, (staff_no, position_id))
                                    
                                    existing_record = cursor.fetchone()
                                    
                                    if existing_record:
                                        st.warning("⚠️ This staff member has already been shortlisted for this position")
                                    
                                    st.markdown("---")
                                    col1, col2, col3 = st.columns([1, 2, 1])
                                    with col2:
                                        if st.button("⭐ Shortlist Candidate", use_container_width=True, type="primary", key="internal_recruitment_shortlist_btn"):
                                            if not existing_record:
                                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                username = st.session_state.user['username']
                                                id_number = staff_member.get('personal_no', 'N/A')
                                                
                                                if is_cloud:
                                                    cursor.execute("""
                                                        INSERT INTO internal_recruitment_candidates (
                                                            staff_no, staff_name, id_number, position_id, position_title, position_code,
                                                            department, shortlist_date, status, shortlisted_by, recruitment_type,
                                                            created_at, updated_at
                                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                                    """, (
                                                        staff_no, staff_member['name'], id_number,
                                                        position_id, position_title, position_code,
                                                        department, now, 'Shortlisted', username,
                                                        'Internal', now, now
                                                    ))
                                                else:
                                                    cursor.execute("""
                                                        INSERT INTO internal_recruitment_candidates (
                                                            staff_no, staff_name, id_number, position_id, position_title, position_code,
                                                            department, shortlist_date, status, shortlisted_by, recruitment_type,
                                                            created_at, updated_at
                                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                    """, (
                                                        staff_no, staff_member['name'], id_number,
                                                        position_id, position_title, position_code,
                                                        department, now, 'Shortlisted', username,
                                                        'Internal', now, now
                                                    ))
                                                
                                                conn.commit()
                                                
                                                log_audit(
                                                    username,
                                                    "INTERNAL_RECRUITMENT_SHORTLIST",
                                                    0,
                                                    f"Shortlisted {staff_member['name']} for internal recruitment to {position_title}",
                                                    "Success"
                                                )
                                                
                                                st.success(f"✅ {staff_member['name']} has been shortlisted for {position_title}!")
                                                st.balloons()
                                                st.rerun()
                                            else:
                                                st.error("❌ This staff member is already shortlisted for this position")
                            else:
                                st.info("No staff members found matching your search criteria")
                        else:
                            st.warning("No employees found. Please add employees in Staff Registry first.")
                
                st.markdown("---")
                st.markdown("### 📋 Shortlisted Internal Candidates")
                
                try:
                    candidates_df = pd.read_sql("SELECT * FROM internal_recruitment_candidates ORDER BY shortlist_date DESC", conn)
                    
                    if candidates_df.empty:
                        st.info("No internal candidates have been shortlisted yet")
                    else:
                        st.success(f"✅ {len(candidates_df)} internal candidate(s) shortlisted")
                        st.dataframe(
                            candidates_df[['staff_name', 'id_number', 'position_title', 'position_code', 'status', 'shortlist_date']],
                            use_container_width=True
                        )
                        
                        csv_all = candidates_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Export All Internal Candidates (CSV)",
                            csv_all,
                            f"internal_candidates_all_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Error loading internal candidates: {e}")
    
    # ==================== TAB 5: REDESIGNATION ====================
    with hr_tab5:
        st.subheader("🔄 Redesignation Management")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name, department, current_designation FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']} (Dept: {row['department']})" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_redesign_employee")
                
                if selected_employee != "Select employee...":
                    staff_no = selected_employee.split(" - ")[0]
                    employee = employees_df[employees_df['staff_no'] == staff_no].iloc[0]
                    
                    with st.form("redesignation_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            old_department = st.text_input("Old Department", value=employee['department'], disabled=True)
                            new_department = st.selectbox("New Department", 
                                ["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Other"],
                                key="hr_redesign_dept")
                            old_designation = st.text_input("Old Designation", value=employee['current_designation'], disabled=True)
                            new_designation = st.text_input("New Designation", key="hr_redesign_designation")
                        with col2:
                            effective_date = st.date_input("Effective Date", key="hr_redesign_date")
                            reason = st.text_area("Reason for Redesignation", key="hr_redesign_reason")
                        
                        st.markdown("### 📋 Approval Minutes")
                        col1, col2 = st.columns(2)
                        with col1:
                            chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="hr_redesign_chrmac_min")
                            chrmac_date = st.date_input("Date of CHRMAC", key="hr_redesign_chrmac_date")
                        with col2:
                            cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="hr_redesign_cpsb_min")
                            cpsb_date = st.date_input("Date of CPSB", key="hr_redesign_cpsb_date")
                        
                        if st.form_submit_button("Process Redesignation", use_container_width=True, type="primary"):
                            if new_department or new_designation:
                                updates = []
                                params = []
                                if new_department:
                                    updates.append("department = %s" if is_cloud else "department = ?")
                                    params.append(new_department)
                                if new_designation:
                                    updates.append("current_designation = %s" if is_cloud else "current_designation = ?")
                                    params.append(new_designation)
                                params.append(staff_no)
                                
                                query = f"UPDATE employees SET {', '.join(updates)} WHERE staff_no = {'%s' if is_cloud else '?'}"
                                cursor.execute(query, tuple(params))
                                conn.commit()
                                
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                                cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                                
                                if is_cloud:
                                    cursor.execute("""
                                        INSERT INTO hr_redesignation (
                                            staff_no, old_department, new_department, old_designation, new_designation,
                                            effective_date, reason, chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (staff_no, employee['department'], new_department,
                                          employee['current_designation'], new_designation,
                                          effective_date.strftime("%Y-%m-%d"), reason,
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          now, st.session_state.user['username']))
                                else:
                                    cursor.execute("""
                                        INSERT INTO hr_redesignation (
                                            staff_no, old_department, new_department, old_designation, new_designation,
                                            effective_date, reason, chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (staff_no, employee['department'], new_department,
                                          employee['current_designation'], new_designation,
                                          effective_date.strftime("%Y-%m-%d"), reason,
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          now, st.session_state.user['username']))
                                conn.commit()
                                
                                log_audit(
                                    username=st.session_state.user['username'],
                                    action="REDESIGNATION",
                                    record_id=0,
                                    details=f"Redesignated {employee['name']} from {employee['department']} to {new_department}, Designation: {new_designation}",
                                    status="Success"
                                )
                                st.success(f"✅ Redesignation processed for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please select a new department or designation")
            else:
                st.warning("No employees found. Please add employees in Staff Registry first.")
        except Exception as e:
            st.info(f"Add employees to enable redesignation. ({e})")
    
    # ==================== TAB 6: CONTRACTS ====================
    with hr_tab6:
        st.subheader("📄 Contract Management")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']}" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_contract_employee")
                
                if selected_employee != "Select employee...":
                    staff_no = selected_employee.split(" - ")[0]
                    
                    with st.form("contract_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            start_date = st.date_input("Start Date", key="hr_contract_start")
                            contract_type = st.selectbox("Contract Type", ["Permanent", "Contract", "Temporary", "Internship", "Secondment"], key="hr_contract_type")
                        with col2:
                            end_date = st.date_input("End Date", key="hr_contract_end") if contract_type != "Permanent" else None
                            contract_docs = st.file_uploader("Upload Contract Document (PDF)", type=["pdf"], key="hr_contract_doc")
                        
                        st.markdown("### 📋 Approval Minutes")
                        col1, col2 = st.columns(2)
                        with col1:
                            chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="hr_contract_chrmac_min")
                            chrmac_date = st.date_input("Date of CHRMAC", key="hr_contract_chrmac_date")
                        with col2:
                            cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="hr_contract_cpsb_min")
                            cpsb_date = st.date_input("Date of CPSB", key="hr_contract_cpsb_date")
                        
                        if st.form_submit_button("Save Contract", use_container_width=True, type="primary"):
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None
                            chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                            cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                            
                            if is_cloud:
                                cursor.execute("""
                                    INSERT INTO employee_contracts (
                                        staff_no, contract_type, start_date, end_date, status,
                                        chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                        created_at, created_by
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (staff_no, contract_type, start_date.strftime("%Y-%m-%d"), end_date_str, 'Active',
                                      chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                      now, st.session_state.user['username']))
                            else:
                                cursor.execute("""
                                    INSERT INTO employee_contracts (
                                        staff_no, contract_type, start_date, end_date, status,
                                        chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                        created_at, created_by
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (staff_no, contract_type, start_date.strftime("%Y-%m-%d"), end_date_str, 'Active',
                                      chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                      now, st.session_state.user['username']))
                            conn.commit()
                            
                            log_audit(
                                username=st.session_state.user['username'],
                                action="CONTRACT",
                                record_id=0,
                                details=f"Saved {contract_type} contract for {selected_employee} from {start_date.strftime('%Y-%m-%d')} to {end_date_str if end_date_str else 'Permanent'}",
                                status="Success"
                            )
                            st.success(f"✅ Contract saved for {selected_employee}!")
                            st.rerun()
            else:
                st.warning("No employees found. Please add employees in Staff Registry first.")
        except Exception as e:
            st.info(f"Add employees to enable contract management. ({e})")
    
    # ==================== TAB 7: TRANSLATION OF TERMS ====================
    with hr_tab7:
        st.subheader("🔄 Translation of Terms")
        st.info("Record changes in designation, job group, or terms of service")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name, current_designation, current_job_group FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']}" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_translation_employee")
                
                if selected_employee != "Select employee...":
                    staff_no = selected_employee.split(" - ")[0]
                    employee = employees_df[employees_df['staff_no'] == staff_no].iloc[0]
                    
                    with st.form("translation_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            old_designation = st.text_input("Old Designation", value=employee['current_designation'], disabled=True)
                            new_designation = st.text_input("New Designation", key="hr_translation_new_designation")
                        with col2:
                            effective_date = st.date_input("Effective Date", key="hr_translation_date")
                            reason = st.text_area("Reason for Translation", key="hr_translation_reason")
                        
                        st.markdown("### 📋 Approval Minutes")
                        col1, col2 = st.columns(2)
                        with col1:
                            chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="hr_translation_chrmac_min")
                            chrmac_date = st.date_input("Date of CHRMAC", key="hr_translation_chrmac_date")
                        with col2:
                            cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="hr_translation_cpsb_min")
                            cpsb_date = st.date_input("Date of CPSB", key="hr_translation_cpsb_date")
                        
                        if st.form_submit_button("Process Translation", use_container_width=True, type="primary"):
                            if new_designation:
                                if is_cloud:
                                    cursor.execute("UPDATE employees SET current_designation = %s WHERE staff_no = %s", (new_designation, staff_no))
                                else:
                                    cursor.execute("UPDATE employees SET current_designation = ? WHERE staff_no = ?", (new_designation, staff_no))
                                conn.commit()
                                
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                                cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                                
                                if is_cloud:
                                    cursor.execute("""
                                        INSERT INTO hr_translation (
                                            staff_no, old_designation, new_designation, effective_date, reason,
                                            chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (staff_no, employee['current_designation'], new_designation,
                                          effective_date.strftime("%Y-%m-%d"), reason,
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          now, st.session_state.user['username']))
                                else:
                                    cursor.execute("""
                                        INSERT INTO hr_translation (
                                            staff_no, old_designation, new_designation, effective_date, reason,
                                            chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (staff_no, employee['current_designation'], new_designation,
                                          effective_date.strftime("%Y-%m-%d"), reason,
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          now, st.session_state.user['username']))
                                conn.commit()
                                
                                log_audit(
                                    username=st.session_state.user['username'],
                                    action="TRANSLATION",
                                    record_id=0,
                                    details=f"Translated {employee['name']} from {employee['current_designation']} to {new_designation} effective {effective_date.strftime('%Y-%m-%d')}",
                                    status="Success"
                                )
                                st.success(f"✅ Translation of terms processed for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please enter the new designation")
                    
                    st.markdown("---")
                    st.subheader("📋 Translation History")
                    history_df = pd.read_sql(f"SELECT * FROM hr_translation WHERE staff_no = '{staff_no}' ORDER BY effective_date DESC", conn)
                    if not history_df.empty:
                        st.dataframe(history_df[['old_designation', 'new_designation', 'effective_date', 'reason', 'chrmac_minutes', 'cpsb_minute', 'created_at']], use_container_width=True)
            else:
                st.warning("No employees found.")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # ==================== TAB 8: SALARY HARMONIZATION ====================
    with hr_tab8:
        st.subheader("💰 Salary Harmonization")
        st.info("Record salary grade and pay adjustments")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name, current_job_group FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']} (JG: {row['current_job_group']})" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_salary_employee")
                
                if selected_employee != "Select employee...":
                    staff_no = selected_employee.split(" - ")[0]
                    employee = employees_df[employees_df['staff_no'] == staff_no].iloc[0]
                    
                    with st.form("salary_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            old_salary_grade = st.text_input("Old Salary Grade", value=employee['current_job_group'], disabled=True)
                            new_salary_grade = st.text_input("New Salary Grade", key="hr_salary_new_grade")
                        with col2:
                            old_basic_pay = st.number_input("Old Basic Pay (KES)", min_value=0, value=0, step=1000, key="hr_salary_old_pay")
                            new_basic_pay = st.number_input("New Basic Pay (KES)", min_value=0, value=0, step=1000, key="hr_salary_new_pay")
                            effective_date = st.date_input("Effective Date", key="hr_salary_date")
                        
                        st.markdown("### 📋 Approval Minutes")
                        col1, col2 = st.columns(2)
                        with col1:
                            chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="hr_salary_chrmac_min")
                            chrmac_date = st.date_input("Date of CHRMAC", key="hr_salary_chrmac_date")
                        with col2:
                            cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="hr_salary_cpsb_min")
                            cpsb_date = st.date_input("Date of CPSB", key="hr_salary_cpsb_date")
                        
                        if st.form_submit_button("Process Salary Harmonization", use_container_width=True, type="primary"):
                            if new_salary_grade or new_basic_pay > 0:
                                if new_salary_grade:
                                    if is_cloud:
                                        cursor.execute("UPDATE employees SET current_job_group = %s WHERE staff_no = %s", (new_salary_grade, staff_no))
                                    else:
                                        cursor.execute("UPDATE employees SET current_job_group = ? WHERE staff_no = ?", (new_salary_grade, staff_no))
                                
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                                cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                                
                                if is_cloud:
                                    cursor.execute("""
                                        INSERT INTO hr_salary_harmonization (
                                            staff_no, old_salary_grade, new_salary_grade, old_basic_pay, new_basic_pay,
                                            effective_date, reason, chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (staff_no, employee['current_job_group'], new_salary_grade, old_basic_pay, new_basic_pay,
                                          effective_date.strftime("%Y-%m-%d"), "Salary harmonization",
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          now, st.session_state.user['username']))
                                else:
                                    cursor.execute("""
                                        INSERT INTO hr_salary_harmonization (
                                            staff_no, old_salary_grade, new_salary_grade, old_basic_pay, new_basic_pay,
                                            effective_date, reason, chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (staff_no, employee['current_job_group'], new_salary_grade, old_basic_pay, new_basic_pay,
                                          effective_date.strftime("%Y-%m-%d"), "Salary harmonization",
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          now, st.session_state.user['username']))
                                conn.commit()
                                
                                log_audit(
                                    username=st.session_state.user['username'],
                                    action="SALARY_HARMONIZATION",
                                    record_id=0,
                                    details=f"Salary harmonization for {employee['name']}: {old_salary_grade} to {new_salary_grade}, Pay: {old_basic_pay} to {new_basic_pay}",
                                    status="Success"
                                )
                                st.success(f"✅ Salary harmonization processed for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please enter new salary grade or new basic pay")
            else:
                st.warning("No employees found.")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # ==================== TAB 9: UNPAID LEAVE ====================
    with hr_tab9:
        st.subheader("🏖️ Unpaid Leave / Leave of Absence")
        st.info("Record unpaid leave requests for employees")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']}" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_leave_employee")
                
                if selected_employee != "Select employee...":
                    staff_no = selected_employee.split(" - ")[0]
                    
                    with st.form("leave_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            start_date = st.date_input("Start Date", key="hr_leave_start")
                            end_date = st.date_input("End Date", key="hr_leave_end")
                        with col2:
                            reason = st.text_area("Reason for Leave", key="hr_leave_reason")
                            status = st.selectbox("Status", ["Pending", "Approved", "Rejected", "Completed"], key="hr_leave_status")
                        
                        if start_date and end_date:
                            total_days = (end_date - start_date).days
                            st.info(f"📊 Total leave days: {total_days} days")
                        
                        st.markdown("### 📋 Approval Minutes")
                        col1, col2 = st.columns(2)
                        with col1:
                            chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="hr_leave_chrmac_min")
                            chrmac_date = st.date_input("Date of CHRMAC", key="hr_leave_chrmac_date")
                        with col2:
                            cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="hr_leave_cpsb_min")
                            cpsb_date = st.date_input("Date of CPSB", key="hr_leave_cpsb_date")
                        
                        if st.form_submit_button("Submit Leave Request", use_container_width=True, type="primary"):
                            if start_date and end_date and reason:
                                total_days = (end_date - start_date).days
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                                cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                                
                                if is_cloud:
                                    cursor.execute("""
                                        INSERT INTO hr_unpaid_leave (
                                            staff_no, start_date, end_date, total_days, reason, status,
                                            chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (staff_no, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), 
                                          total_days, reason, status,
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          now, st.session_state.user['username']))
                                else:
                                    cursor.execute("""
                                        INSERT INTO hr_unpaid_leave (
                                            staff_no, start_date, end_date, total_days, reason, status,
                                            chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (staff_no, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), 
                                          total_days, reason, status,
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          now, st.session_state.user['username']))
                                conn.commit()
                                
                                log_audit(
                                    username=st.session_state.user['username'],
                                    action="LEAVE_REQUEST",
                                    record_id=0,
                                    details=f"Submitted {status} leave request for {employee['name']} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({total_days} days)",
                                    status="Success"
                                )
                                st.success(f"✅ Leave request submitted for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please fill in all required fields")
                    
                    st.markdown("---")
                    st.subheader("📋 Leave History")
                    history_df = pd.read_sql(f"SELECT * FROM hr_unpaid_leave WHERE staff_no = '{staff_no}' ORDER BY start_date DESC", conn)
                    if not history_df.empty:
                        st.dataframe(history_df[['start_date', 'end_date', 'total_days', 'reason', 'status', 'chrmac_minutes', 'cpsb_minute', 'created_at']], use_container_width=True)
            else:
                st.warning("No employees found.")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # ==================== TAB 10: CONFIRMATION ====================
    with hr_tab10:
        st.subheader("✅ Confirmation in Appointment")
        st.info("Process employee confirmation after probation period")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name, first_appointment_date FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']} (Appointed: {row['first_appointment_date']})" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_confirmation_employee")
                
                if selected_employee != "Select employee...":
                    staff_no = selected_employee.split(" - ")[0]
                    employee = employees_df[employees_df['staff_no'] == staff_no].iloc[0]
                    
                    with st.form("confirmation_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            confirmation_date = st.date_input("Confirmation Date", key="hr_confirmation_date")
                            probation_period = st.number_input("Probation Period (Months)", min_value=0, max_value=24, value=6, key="hr_probation_period")
                        with col2:
                            performance_rating = st.selectbox("Performance Rating", ["Excellent", "Very Good", "Good", "Satisfactory", "Needs Improvement", "Unsatisfactory"], key="hr_performance_rating")
                            recommendation = st.selectbox("Recommendation", ["Confirm", "Extend Probation", "Terminate"], key="hr_recommendation")
                        
                        status = st.selectbox("Status", ["Pending", "Approved", "Rejected"], key="hr_confirmation_status")
                        
                        st.markdown("### 📋 Approval Minutes")
                        col1, col2 = st.columns(2)
                        with col1:
                            chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="hr_confirmation_chrmac_min")
                            chrmac_date = st.date_input("Date of CHRMAC", key="hr_confirmation_chrmac_date")
                        with col2:
                            cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="hr_confirmation_cpsb_min")
                            cpsb_date = st.date_input("Date of CPSB", key="hr_confirmation_cpsb_date")
                        
                        if st.form_submit_button("Process Confirmation", use_container_width=True, type="primary"):
                            if confirmation_date:
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                                cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                                
                                if is_cloud:
                                    cursor.execute("""
                                        INSERT INTO hr_confirmation (
                                            staff_no, confirmation_date, probation_period_months, performance_rating,
                                            recommendation, status, chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            approved_by, created_at, created_by
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (staff_no, confirmation_date.strftime("%Y-%m-%d"), probation_period,
                                          performance_rating, recommendation, status,
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          st.session_state.user['username'], now, st.session_state.user['username']))
                                else:
                                    cursor.execute("""
                                        INSERT INTO hr_confirmation (
                                            staff_no, confirmation_date, probation_period_months, performance_rating,
                                            recommendation, status, chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            approved_by, created_at, created_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (staff_no, confirmation_date.strftime("%Y-%m-%d"), probation_period,
                                          performance_rating, recommendation, status,
                                          chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                          st.session_state.user['username'], now, st.session_state.user['username']))
                                conn.commit()
                                
                                if status == "Approved" and recommendation == "Confirm":
                                    if is_cloud:
                                        cursor.execute("UPDATE employees SET status = 'Confirmed' WHERE staff_no = %s", (staff_no,))
                                    else:
                                        cursor.execute("UPDATE employees SET status = 'Confirmed' WHERE staff_no = ?", (staff_no,))
                                    conn.commit()
                                
                                log_audit(
                                    username=st.session_state.user['username'],
                                    action="CONFIRMATION",
                                    record_id=0,
                                    details=f"Confirmation for {employee['name']}: {recommendation} - {status} (Rating: {performance_rating})",
                                    status="Success"
                                )
                                st.success(f"✅ Confirmation processed for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please select confirmation date")
                    
                    st.markdown("---")
                    st.subheader("📋 Confirmation History")
                    history_df = pd.read_sql(f"SELECT * FROM hr_confirmation WHERE staff_no = '{staff_no}' ORDER BY confirmation_date DESC", conn)
                    if not history_df.empty:
                        st.dataframe(history_df[['confirmation_date', 'probation_period_months', 'performance_rating', 'recommendation', 'status', 'chrmac_minutes', 'cpsb_minute', 'created_at']], use_container_width=True)
            else:
                st.warning("No employees found.")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # ==================== TAB 11: DISCIPLINE CASES ====================
    with hr_tab11:
        st.subheader("⚖️ Discipline Cases")
        st.info("Track and manage employee disciplinary cases")
        
        with st.form("discipline_case_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                employees_list = pd.read_sql("SELECT staff_no, name FROM employees ORDER BY name", conn)
                if not employees_list.empty:
                    employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']}" for _, row in employees_list.iterrows()]
                    selected_employee = st.selectbox("Select Staff", employee_options, key="discipline_employee")
                else:
                    selected_employee = "Select employee..."
                    st.warning("No employees found. Please add employees in Staff Registry first.")
                
                case_type = st.selectbox("Offense Category", 
                    ["Select Offense...",
                     "Absenteeism", 
                     "Misconduct", 
                     "Gross Misconduct", 
                     "Insubordination", 
                     "Corruption", 
                     "Theft",
                     "Forgery of documents",
                     "Sexual harassment",
                     "Drunkenness",
                     "Conviction of a criminal offence",
                     "Misappropriation of public funds",
                     "Harassment or discrimination",
                     "Other"], 
                    key="case_type")
                
                incident_date = st.date_input("Incident Date", key="incident_date")
                hearing_date = st.date_input("Hearing Date", value=None, key="hearing_date")
            
            with col2:
                case_number = st.text_input("Case Number", placeholder="e.g., DISC/2024/001", key="case_number")
                status = st.selectbox("Status", 
                    ["Under Investigation", "Hearing Scheduled", "Decision Pending", "Closed", "Appealed"], 
                    key="discipline_status")
                decision_date = st.date_input("Decision Date", value=None, key="decision_date")
                closed_date = st.date_input("Closed Date", value=None, key="closed_date")
            
            description = st.text_area("Case Description", height=100, key="case_description")
            penalty = st.text_area("Penalty/Action Taken", height=80, key="penalty")
            action_taken = st.text_area("Action Taken", height=80, key="action_taken", placeholder="Describe the action taken...")
            
            st.markdown("---")
            st.markdown("### 📋 Disciplinary Process")
            
            st.markdown("#### 📝 DHRMAC Recommendation")
            col1, col2 = st.columns(2)
            with col1:
                dhrmac_recommendation = st.text_area("DHRMAC Recommendation", height=80, key="dhrmac_recommendation")
            with col2:
                dhrmac_date = st.date_input("DHRMAC Date", value=None, key="dhrmac_date")
            
            st.markdown("#### 📝 CHRMAC Recommendation")
            col1, col2 = st.columns(2)
            with col1:
                chrmac_recommendation = st.text_area("CHRMAC Recommendation", height=80, key="chrmac_recommendation")
            with col2:
                chrmac_date = st.date_input("CHRMAC Date", value=None, key="chrmac_date")
            
            st.markdown("#### 🏛️ CPSB Decision")
            col1, col2 = st.columns(2)
            with col1:
                cpsb_decision = st.text_area("CPSB Decision", height=80, key="cpsb_decision")
            with col2:
                cpsb_decision_date = st.date_input("CPSB Decision Date", value=None, key="cpsb_decision_date")
            
            if st.form_submit_button("Record Case", use_container_width=True, type="primary"):
                if selected_employee != "Select employee..." and case_number and description and case_type != "Select Offense...":
                    staff_no = selected_employee.split(" - ")[0]
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    incident_date_str = incident_date.strftime("%Y-%m-%d") if incident_date else None
                    hearing_date_str = hearing_date.strftime("%Y-%m-%d") if hearing_date else None
                    decision_date_str = decision_date.strftime("%Y-%m-%d") if decision_date else None
                    closed_date_str = closed_date.strftime("%Y-%m-%d") if closed_date else None
                    dhrmac_date_str = dhrmac_date.strftime("%Y-%m-%d") if dhrmac_date else None
                    chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                    cpsb_decision_date_str = cpsb_decision_date.strftime("%Y-%m-%d") if cpsb_decision_date else None
                    
                    if is_cloud:
                        cursor.execute("""
                            INSERT INTO hr_discipline (
                                staff_no, case_number, case_type, incident_date, description, penalty, status,
                                hearing_date, decision_date, closed_date, action_taken,
                                dhrmac_recommendation, dhrmac_date,
                                chrmac_recommendation, chrmac_date,
                                cpsb_decision, cpsb_decision_date,
                                created_at, created_by
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            staff_no, case_number, case_type, incident_date_str, description, penalty, status,
                            hearing_date_str, decision_date_str, closed_date_str, action_taken,
                            dhrmac_recommendation, dhrmac_date_str,
                            chrmac_recommendation, chrmac_date_str,
                            cpsb_decision, cpsb_decision_date_str,
                            now, st.session_state.user['username']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO hr_discipline (
                                staff_no, case_number, case_type, incident_date, description, penalty, status,
                                hearing_date, decision_date, closed_date, action_taken,
                                dhrmac_recommendation, dhrmac_date,
                                chrmac_recommendation, chrmac_date,
                                cpsb_decision, cpsb_decision_date,
                                created_at, created_by
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            staff_no, case_number, case_type, incident_date_str, description, penalty, status,
                            hearing_date_str, decision_date_str, closed_date_str, action_taken,
                            dhrmac_recommendation, dhrmac_date_str,
                            chrmac_recommendation, chrmac_date_str,
                            cpsb_decision, cpsb_decision_date_str,
                            now, st.session_state.user['username']
                        ))
                    conn.commit()
                    
                    log_audit(
                        username=st.session_state.user['username'],
                        action="DISCIPLINE_CASE",
                        record_id=0,
                        details=f"Recorded discipline case #{case_number} for {employee_name}: {case_type} - Status: {status}",
                        status="Success"
                    )
                    st.success(f"✅ Discipline case recorded!")
                    st.balloons()
                    st.rerun()
                else:
                    if case_type == "Select Offense...":
                        st.warning("Please select an offense category")
                    else:
                        st.warning("Please select employee, enter case number and description")
        
        st.markdown("---")
        st.subheader("📋 Discipline Cases History")
        
        try:
            cases_df = pd.read_sql("""
                SELECT d.*, e.name as employee_name 
                FROM hr_discipline d
                LEFT JOIN employees e ON d.staff_no = e.staff_no
                ORDER BY d.id DESC
            """, conn)
            
            if not cases_df.empty:
                display_cols = ['case_number', 'employee_name', 'case_type', 'incident_date', 
                               'status', 'hearing_date', 'decision_date', 'closed_date',
                               'dhrmac_recommendation', 'dhrmac_date', 'chrmac_recommendation', 
                               'chrmac_date', 'cpsb_decision', 'cpsb_decision_date', 'penalty', 'action_taken']
                available_cols = [c for c in display_cols if c in cases_df.columns]
                st.dataframe(cases_df[available_cols], use_container_width=True)
                
                csv_discipline = cases_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Discipline Cases (CSV)",
                    csv_discipline,
                    f"discipline_cases_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.info("No discipline cases recorded yet.")
        except Exception as e:
            st.info(f"Discipline cases will appear here once recorded.")
    
    # ==================== TAB 12: ACTING CAPACITY ====================
    with hr_tab12:
        st.subheader("🎭 Appointment in Acting Capacity")
        st.info("Manage acting appointments for employees (6 months renewable once)")
        
        try:
            if is_cloud:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS hr_acting_appointments (
                        id SERIAL PRIMARY KEY,
                        staff_no TEXT,
                        employee_name TEXT,
                        current_position TEXT,
                        current_job_group TEXT,
                        acting_position TEXT,
                        acting_job_group TEXT,
                        appointment_date TEXT,
                        expiry_date TEXT,
                        duration_months INTEGER DEFAULT 6,
                        renewal_count INTEGER DEFAULT 0,
                        max_renewals INTEGER DEFAULT 1,
                        reason TEXT,
                        status TEXT DEFAULT 'Active',
                        chrmac_minutes TEXT,
                        chrmac_date TEXT,
                        cpsb_minute TEXT,
                        cpsb_date TEXT,
                        created_at TEXT,
                        created_by TEXT,
                        updated_at TEXT
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS hr_acting_appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        staff_no TEXT,
                        employee_name TEXT,
                        current_position TEXT,
                        current_job_group TEXT,
                        acting_position TEXT,
                        acting_job_group TEXT,
                        appointment_date TEXT,
                        expiry_date TEXT,
                        duration_months INTEGER DEFAULT 6,
                        renewal_count INTEGER DEFAULT 0,
                        max_renewals INTEGER DEFAULT 1,
                        reason TEXT,
                        status TEXT DEFAULT 'Active',
                        chrmac_minutes TEXT,
                        chrmac_date TEXT,
                        cpsb_minute TEXT,
                        cpsb_date TEXT,
                        created_at TEXT,
                        created_by TEXT,
                        updated_at TEXT
                    )
                """)
            conn.commit()
        except Exception as e:
            st.error(f"Error creating table: {e}")
        
        acting_tab1, acting_tab2 = st.tabs(["📝 New Acting Appointment", "📋 Active Acting Appointments"])
        
        with acting_tab1:
            st.markdown("### 📝 Create Acting Appointment")
            st.info("Appoint an employee to act in a higher capacity for 6 months (renewable once)")
            
            employees_list = pd.read_sql("SELECT staff_no, name, current_designation, current_job_group FROM employees ORDER BY name", conn)
            
            if employees_list.empty:
                st.warning("No employees found. Please add employees in Staff Registry first.")
            else:
                with st.form("acting_appointment_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']}" for _, row in employees_list.iterrows()]
                        selected_employee = st.selectbox("Select Employee", employee_options, key="acting_employee")
                        
                        staff_no = None
                        employee = None
                        
                        if selected_employee != "Select employee...":
                            staff_no = selected_employee.split(" - ")[0]
                            employee = employees_list[employees_list['staff_no'] == staff_no].iloc[0]
                            
                            st.text_input("Current Position", value=employee['current_designation'] if employee['current_designation'] else "N/A", disabled=True, key="current_pos")
                            st.text_input("Current Job Group", value=employee['current_job_group'] if employee['current_job_group'] else "N/A", disabled=True, key="current_jg")
                        
                        acting_position = st.text_input("Acting Position Title *", placeholder="e.g., Senior Human Resource Officer", key="acting_position")
                        acting_job_group = st.text_input("Acting Job Group *", placeholder="e.g., JG 'P'", key="acting_job_group")
                    
                    with col2:
                        appointment_date = st.date_input("Appointment Date", value=datetime.now(), key="acting_appointment_date")
                        
                        expiry_date_calc = appointment_date + relativedelta(months=6)
                        st.info(f"📅 **Expiry Date:** {expiry_date_calc.strftime('%d/%m/%Y')} (6 months from appointment)")
                        
                        st.markdown("---")
                        st.markdown("#### Renewal Information")
                        st.caption("Acting appointments are for 6 months and can be renewed once")
                        
                        active_count = 0
                        if selected_employee != "Select employee..." and staff_no:
                            cursor.execute("""
                                SELECT COUNT(*) FROM hr_acting_appointments 
                                WHERE staff_no = %s AND status = 'Active'
                            """, (staff_no,))
                            active_count = cursor.fetchone()[0]
                            
                            if active_count > 0:
                                st.warning("⚠️ This employee already has an active acting appointment. Only one active appointment allowed.")
                    
                    st.markdown("---")
                    st.markdown("### 📋 Reason for Acting Appointment")
                    reason = st.text_area("Reason", height=100, placeholder="e.g., Employee proceeding on leave, Position vacant, Special project, etc.", key="acting_reason")
                    
                    st.markdown("### 📋 Approval Minutes")
                    col1, col2 = st.columns(2)
                    with col1:
                        chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="acting_chrmac_min")
                        chrmac_date = st.date_input("Date of CHRMAC", value=None, key="acting_chrmac_date")
                    with col2:
                        cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="acting_cpsb_min")
                        cpsb_date = st.date_input("Date of CPSB", value=None, key="acting_cpsb_date")
                    
                    submitted = st.form_submit_button("📌 Appoint in Acting Capacity", use_container_width=True, type="primary")
                    
                    if submitted:
                        if selected_employee != "Select employee..." and acting_position and reason and staff_no:
                            if active_count > 0:
                                st.error("❌ Employee already has an active acting appointment. Please end the current appointment first.")
                            else:
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                expiry_date = (appointment_date + relativedelta(months=6)).strftime("%Y-%m-%d")
                                chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                                cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                                
                                if is_cloud:
                                    cursor.execute("""
                                        INSERT INTO hr_acting_appointments (
                                            staff_no, employee_name, current_position, current_job_group,
                                            acting_position, acting_job_group, appointment_date, expiry_date,
                                            duration_months, renewal_count, max_renewals, reason, status,
                                            chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (
                                        staff_no, employee['name'], employee['current_designation'], employee['current_job_group'],
                                        acting_position, acting_job_group, appointment_date.strftime("%Y-%m-%d"), expiry_date,
                                        6, 0, 1, reason, 'Active',
                                        chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                        now, st.session_state.user['username']
                                    ))
                                else:
                                    cursor.execute("""
                                        INSERT INTO hr_acting_appointments (
                                            staff_no, employee_name, current_position, current_job_group,
                                            acting_position, acting_job_group, appointment_date, expiry_date,
                                            duration_months, renewal_count, max_renewals, reason, status,
                                            chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                            created_at, created_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        staff_no, employee['name'], employee['current_designation'], employee['current_job_group'],
                                        acting_position, acting_job_group, appointment_date.strftime("%Y-%m-%d"), expiry_date,
                                        6, 0, 1, reason, 'Active',
                                        chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                                        now, st.session_state.user['username']
                                    ))
                                conn.commit()
                                
                                log_audit(
                                    username=st.session_state.user['username'],
                                    action="ACTING_APPOINTMENT",
                                    record_id=0,
                                    details=f"Appointed {employee['name']} to act as {acting_position} ({acting_job_group}) from {appointment_date.strftime('%Y-%m-%d')} to {expiry_date}",
                                    status="Success"
                                )
                                st.success(f"✅ {employee['name']} appointed to act as {acting_position}!")
                                st.balloons()
                                st.rerun()
                        else:
                            if selected_employee == "Select employee...":
                                st.warning("Please select an employee")
                            elif not acting_position:
                                st.warning("Please enter the acting position title")
                            elif not reason:
                                st.warning("Please provide a reason for the acting appointment")
    
    # ==================== TAB 13: HR REPORTS ====================
    with hr_tab13:
        st.subheader("📋 HR Reports & Analytics")
        st.markdown("Generate comprehensive reports from all HR modules")
        
        report_tab1, report_tab2, report_tab3, report_tab4, report_tab5, report_tab6, report_tab7, report_tab8, report_tab9, report_tab10 = st.tabs([
            "📊 Staff Reports",
            "📈 Promotion Reports",
            "🔄 Redesignation Reports",
            "📄 Translation Reports",
            "💰 Salary Harmonization Reports",
            "✅ Confirmation Reports",
            "⚖️ Discipline Reports",
            "📄 Contract Reports",
            "🏖️ Leave Reports",
            "📑 Consolidated Reports"
        ])
        
        def export_data(df, report_name):
            if df.empty:
                st.warning("No data available for export")
                return
            
            col1, col2, col3 = st.columns(3)
            with col1:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    f"📥 Download {report_name} (CSV)",
                    csv,
                    f"{report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            with col2:
                try:
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name=report_name[:31], index=False)
                    st.download_button(
                        f"📥 Download {report_name} (Excel)",
                        output.getvalue(),
                        f"{report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except Exception as e:
                    st.info("Excel export requires openpyxl")
            
            with col3:
                st.info(f"📊 {len(df)} records available")
        
        with report_tab1:
            st.markdown("### 👥 Staff Reports")
            
            try:
                staff_report_df = pd.read_sql("SELECT * FROM employees ORDER BY name", conn)
                
                if staff_report_df.empty:
                    st.info("No staff records found")
                else:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        dept_filter = st.multiselect("Filter by Department", 
                            options=sorted(staff_report_df['department'].dropna().unique()) if 'department' in staff_report_df.columns else [],
                            default=[],
                            key="staff_dept_filter")
                    with col2:
                        gender_filter = st.multiselect("Filter by Gender",
                            options=sorted(staff_report_df['gender'].dropna().unique()) if 'gender' in staff_report_df.columns else [],
                            default=[],
                            key="staff_gender_filter")
                    with col3:
                        terms_filter = st.multiselect("Terms of Service",
                            options=sorted(staff_report_df['terms_of_service'].dropna().unique()) if 'terms_of_service' in staff_report_df.columns else [],
                            default=[],
                            key="staff_terms_filter")
                    with col4:
                        age_range = st.slider("Age Range", 18, 100, (18, 100), key="staff_age_range")
                    
                    filtered_report = staff_report_df.copy()
                    if dept_filter and 'department' in filtered_report.columns:
                        filtered_report = filtered_report[filtered_report['department'].isin(dept_filter)]
                    if gender_filter and 'gender' in filtered_report.columns:
                        filtered_report = filtered_report[filtered_report['gender'].isin(gender_filter)]
                    if terms_filter and 'terms_of_service' in filtered_report.columns:
                        filtered_report = filtered_report[filtered_report['terms_of_service'].isin(terms_filter)]
                    if 'age' in filtered_report.columns:
                        filtered_report = filtered_report[(filtered_report['age'] >= age_range[0]) & (filtered_report['age'] <= age_range[1])]
                    
                    st.info(f"📊 Showing {len(filtered_report)} of {len(staff_report_df)} staff records")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Staff", len(staff_report_df))
                    with col2:
                        male_count = len(staff_report_df[staff_report_df['gender'] == 'Male']) if 'gender' in staff_report_df.columns else 0
                        st.metric("Male Staff", male_count)
                    with col3:
                        female_count = len(staff_report_df[staff_report_df['gender'] == 'Female']) if 'gender' in staff_report_df.columns else 0
                        st.metric("Female Staff", female_count)
                    with col4:
                        avg_age = staff_report_df['age'].mean() if 'age' in staff_report_df.columns else 0
                        st.metric("Average Age", f"{avg_age:.1f}")
                    
                    st.markdown("#### Staff List")
                    display_cols = ['personal_no', 'name', 'gender', 'age', 'department', 'current_designation', 'current_job_group', 'terms_of_service']
                    available_cols = [c for c in display_cols if c in filtered_report.columns]
                    st.dataframe(filtered_report[available_cols], use_container_width=True)
                    
                    export_data(filtered_report, "Staff_Report")
                    
            except Exception as e:
                st.error(f"Error loading staff data: {e}")
        
        with report_tab2:
            st.markdown("### 📈 Promotion Reports")
            
            try:
                promotions_report_df = pd.read_sql("""
                    SELECT p.*, e.name as employee_name, e.department 
                    FROM hr_promotions p
                    LEFT JOIN employees e ON p.staff_no = e.staff_no
                    ORDER BY p.effective_date DESC
                """, conn)
                
                if promotions_report_df.empty:
                    st.info("No promotion records found")
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        promo_dept_filter = st.multiselect("Department",
                            options=sorted(promotions_report_df['department'].dropna().unique()) if 'department' in promotions_report_df.columns else [],
                            default=[],
                            key="promo_dept_filter")
                    with col2:
                        date_range = st.date_input("Date Range", 
                            value=(datetime.now() - timedelta(days=365), datetime.now()),
                            key="promo_date_range")
                    with col3:
                        min_score_filter = st.number_input("Min Years Since Last Promotion", min_value=0, max_value=20, value=0, key="promo_years_filter")
                    
                    filtered_promo = promotions_report_df.copy()
                    if promo_dept_filter and 'department' in filtered_promo.columns:
                        filtered_promo = filtered_promo[filtered_promo['department'].isin(promo_dept_filter)]
                    if len(date_range) == 2:
                        filtered_promo['effective_date'] = pd.to_datetime(filtered_promo['effective_date'])
                        filtered_promo = filtered_promo[
                            (filtered_promo['effective_date'] >= pd.to_datetime(date_range[0])) & 
                            (filtered_promo['effective_date'] <= pd.to_datetime(date_range[1]))
                        ]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Promotions", len(promotions_report_df))
                    with col2:
                        unique_employees = promotions_report_df['staff_no'].nunique()
                        st.metric("Employees Promoted", unique_employees)
                    with col3:
                        recent_promos = len(filtered_promo)
                        st.metric("In Selected Period", recent_promos)
                    with col4:
                        avg_promos_per_emp = len(promotions_report_df) / unique_employees if unique_employees > 0 else 0
                        st.metric("Avg Promotions/Employee", f"{avg_promos_per_emp:.1f}")
                    
                    if 'department' in filtered_promo.columns and not filtered_promo.empty:
                        dept_promo_counts = filtered_promo['department'].value_counts().reset_index()
                        dept_promo_counts.columns = ['Department', 'Promotion Count']
                        fig_dept_promo = px.bar(dept_promo_counts, x='Department', y='Promotion Count',
                                                title="Promotions by Department",
                                                color='Promotion Count',
                                                color_continuous_scale='Greens')
                        fig_dept_promo.update_layout(height=400)
                        st.plotly_chart(fig_dept_promo, use_container_width=True)
                    
                    st.markdown("#### Promotion Records")
                    display_cols = ['employee_name', 'department', 'old_designation', 'new_designation', 
                                   'old_job_group', 'new_job_group', 'effective_date', 'reason']
                    available_cols = [c for c in display_cols if c in filtered_promo.columns]
                    st.dataframe(filtered_promo[available_cols], use_container_width=True)
                    
                    export_data(filtered_promo, "Promotions_Report")
                    
            except Exception as e:
                st.error(f"Error loading promotion data: {e}")
        
        with report_tab3:
            st.markdown("### 🔄 Redesignation Reports")
            
            try:
                redesignation_report_df = pd.read_sql("""
                    SELECT r.*, e.name as employee_name, e.department 
                    FROM hr_redesignation r
                    LEFT JOIN employees e ON r.staff_no = e.staff_no
                    ORDER BY r.effective_date DESC
                """, conn)
                
                if redesignation_report_df.empty:
                    st.info("No redesignation records found")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        redesign_dept_filter = st.multiselect("Department",
                            options=sorted(redesignation_report_df['department'].dropna().unique()) if 'department' in redesignation_report_df.columns else [],
                            default=[],
                            key="redesign_dept_filter")
                    with col2:
                        date_range_redesign = st.date_input("Date Range", 
                            value=(datetime.now() - timedelta(days=365), datetime.now()),
                            key="redesign_date_range")
                    
                    filtered_redesign = redesignation_report_df.copy()
                    if redesign_dept_filter and 'department' in filtered_redesign.columns:
                        filtered_redesign = filtered_redesign[filtered_redesign['department'].isin(redesign_dept_filter)]
                    if len(date_range_redesign) == 2:
                        filtered_redesign['effective_date'] = pd.to_datetime(filtered_redesign['effective_date'])
                        filtered_redesign = filtered_redesign[
                            (filtered_redesign['effective_date'] >= pd.to_datetime(date_range_redesign[0])) & 
                            (filtered_redesign['effective_date'] <= pd.to_datetime(date_range_redesign[1]))
                        ]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Redesignations", len(redesignation_report_df))
                    with col2:
                        unique_employees = redesignation_report_df['staff_no'].nunique()
                        st.metric("Employees Affected", unique_employees)
                    with col3:
                        recent_redesign = len(filtered_redesign)
                        st.metric("In Selected Period", recent_redesign)
                    with col4:
                        st.metric("Avg per Employee", f"{len(redesignation_report_df)/unique_employees:.1f}" if unique_employees > 0 else "0")
                    
                    st.markdown("#### Redesignation Records")
                    display_cols = ['employee_name', 'department', 'old_department', 'new_department', 
                                   'old_designation', 'new_designation', 'effective_date', 'reason']
                    available_cols = [c for c in display_cols if c in filtered_redesign.columns]
                    st.dataframe(filtered_redesign[available_cols], use_container_width=True)
                    
                    export_data(filtered_redesign, "Redesignation_Report")
                    
            except Exception as e:
                st.error(f"Error loading redesignation data: {e}")
        
        with report_tab4:
            st.markdown("### 🔄 Translation of Terms Reports")
            
            try:
                translation_report_df = pd.read_sql("""
                    SELECT t.*, e.name as employee_name, e.department 
                    FROM hr_translation t
                    LEFT JOIN employees e ON t.staff_no = e.staff_no
                    ORDER BY t.effective_date DESC
                """, conn)
                
                if translation_report_df.empty:
                    st.info("No translation of terms records found")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        trans_dept_filter = st.multiselect("Department",
                            options=sorted(translation_report_df['department'].dropna().unique()) if 'department' in translation_report_df.columns else [],
                            default=[],
                            key="trans_dept_filter")
                    with col2:
                        date_range_trans = st.date_input("Date Range", 
                            value=(datetime.now() - timedelta(days=365), datetime.now()),
                            key="trans_date_range")
                    
                    filtered_trans = translation_report_df.copy()
                    if trans_dept_filter and 'department' in filtered_trans.columns:
                        filtered_trans = filtered_trans[filtered_trans['department'].isin(trans_dept_filter)]
                    if len(date_range_trans) == 2:
                        filtered_trans['effective_date'] = pd.to_datetime(filtered_trans['effective_date'])
                        filtered_trans = filtered_trans[
                            (filtered_trans['effective_date'] >= pd.to_datetime(date_range_trans[0])) & 
                            (filtered_trans['effective_date'] <= pd.to_datetime(date_range_trans[1]))
                        ]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Translations", len(translation_report_df))
                    with col2:
                        unique_employees = translation_report_df['staff_no'].nunique()
                        st.metric("Employees Affected", unique_employees)
                    with col3:
                        recent_trans = len(filtered_trans)
                        st.metric("In Selected Period", recent_trans)
                    
                    st.markdown("#### Translation of Terms Records")
                    display_cols = ['employee_name', 'department', 'old_designation', 'new_designation', 'effective_date', 'reason']
                    available_cols = [c for c in display_cols if c in filtered_trans.columns]
                    st.dataframe(filtered_trans[available_cols], use_container_width=True)
                    
                    export_data(filtered_trans, "Translation_Report")
                    
            except Exception as e:
                st.error(f"Error loading translation data: {e}")
        
        with report_tab5:
            st.markdown("### 💰 Salary Harmonization Reports")
            
            try:
                salary_report_df = pd.read_sql("""
                    SELECT s.*, e.name as employee_name, e.department 
                    FROM hr_salary_harmonization s
                    LEFT JOIN employees e ON s.staff_no = e.staff_no
                    ORDER BY s.effective_date DESC
                """, conn)
                
                if salary_report_df.empty:
                    st.info("No salary harmonization records found")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        salary_dept_filter = st.multiselect("Department",
                            options=sorted(salary_report_df['department'].dropna().unique()) if 'department' in salary_report_df.columns else [],
                            default=[],
                            key="salary_dept_filter")
                    with col2:
                        date_range_salary = st.date_input("Date Range", 
                            value=(datetime.now() - timedelta(days=365), datetime.now()),
                            key="salary_date_range")
                    
                    filtered_salary = salary_report_df.copy()
                    if salary_dept_filter and 'department' in filtered_salary.columns:
                        filtered_salary = filtered_salary[filtered_salary['department'].isin(salary_dept_filter)]
                    if len(date_range_salary) == 2:
                        filtered_salary['effective_date'] = pd.to_datetime(filtered_salary['effective_date'])
                        filtered_salary = filtered_salary[
                            (filtered_salary['effective_date'] >= pd.to_datetime(date_range_salary[0])) & 
                            (filtered_salary['effective_date'] <= pd.to_datetime(date_range_salary[1]))
                        ]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Harmonizations", len(salary_report_df))
                    with col2:
                        unique_employees = salary_report_df['staff_no'].nunique()
                        st.metric("Employees Affected", unique_employees)
                    with col3:
                        total_pay_increase = (salary_report_df['new_basic_pay'] - salary_report_df['old_basic_pay']).sum() if 'new_basic_pay' in salary_report_df.columns else 0
                        st.metric("Total Pay Increase (KES)", f"{total_pay_increase:,.0f}")
                    with col4:
                        recent_salary = len(filtered_salary)
                        st.metric("In Selected Period", recent_salary)
                    
                    st.markdown("#### Salary Harmonization Records")
                    display_cols = ['employee_name', 'department', 'old_salary_grade', 'new_salary_grade', 
                                   'old_basic_pay', 'new_basic_pay', 'effective_date']
                    available_cols = [c for c in display_cols if c in filtered_salary.columns]
                    st.dataframe(filtered_salary[available_cols], use_container_width=True)
                    
                    export_data(filtered_salary, "Salary_Harmonization_Report")
                    
            except Exception as e:
                st.error(f"Error loading salary harmonization data: {e}")
        
        with report_tab6:
            st.markdown("### ✅ Confirmation Reports")
            
            try:
                confirmation_report_df = pd.read_sql("""
                    SELECT c.*, e.name as employee_name, e.department 
                    FROM hr_confirmation c
                    LEFT JOIN employees e ON c.staff_no = e.staff_no
                    ORDER BY c.confirmation_date DESC
                """, conn)
                
                if confirmation_report_df.empty:
                    st.info("No confirmation records found")
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        conf_status_filter = st.multiselect("Status",
                            options=sorted(confirmation_report_df['status'].dropna().unique()) if 'status' in confirmation_report_df.columns else [],
                            default=[],
                            key="conf_status_filter")
                    with col2:
                        conf_rating_filter = st.multiselect("Performance Rating",
                            options=sorted(confirmation_report_df['performance_rating'].dropna().unique()) if 'performance_rating' in confirmation_report_df.columns else [],
                            default=[],
                            key="conf_rating_filter")
                    with col3:
                        conf_recommend_filter = st.multiselect("Recommendation",
                            options=sorted(confirmation_report_df['recommendation'].dropna().unique()) if 'recommendation' in confirmation_report_df.columns else [],
                            default=[],
                            key="conf_recommend_filter")
                    
                    filtered_conf = confirmation_report_df.copy()
                    if conf_status_filter and 'status' in filtered_conf.columns:
                        filtered_conf = filtered_conf[filtered_conf['status'].isin(conf_status_filter)]
                    if conf_rating_filter and 'performance_rating' in filtered_conf.columns:
                        filtered_conf = filtered_conf[filtered_conf['performance_rating'].isin(conf_rating_filter)]
                    if conf_recommend_filter and 'recommendation' in filtered_conf.columns:
                        filtered_conf = filtered_conf[filtered_conf['recommendation'].isin(conf_recommend_filter)]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Confirmations", len(confirmation_report_df))
                    with col2:
                        approved_count = len(confirmation_report_df[confirmation_report_df['status'] == 'Approved']) if 'status' in confirmation_report_df.columns else 0
                        st.metric("Approved", approved_count)
                    with col3:
                        pending_count = len(confirmation_report_df[confirmation_report_df['status'] == 'Pending']) if 'status' in confirmation_report_df.columns else 0
                        st.metric("Pending", pending_count)
                    with col4:
                        confirmed_count = len(confirmation_report_df[confirmation_report_df['recommendation'] == 'Confirm']) if 'recommendation' in confirmation_report_df.columns else 0
                        st.metric("Recommended to Confirm", confirmed_count)
                    
                    st.markdown("#### Confirmation Records")
                    display_cols = ['employee_name', 'department', 'confirmation_date', 'probation_period_months', 
                                   'performance_rating', 'recommendation', 'status']
                    available_cols = [c for c in display_cols if c in filtered_conf.columns]
                    st.dataframe(filtered_conf[available_cols], use_container_width=True)
                    
                    export_data(filtered_conf, "Confirmation_Report")
                    
            except Exception as e:
                st.error(f"Error loading confirmation data: {e}")
        
        with report_tab7:
            st.markdown("### ⚖️ Discipline Reports")
            
            try:
                discipline_report_df = pd.read_sql("""
                    SELECT d.*, e.name as employee_name 
                    FROM hr_discipline d
                    LEFT JOIN employees e ON d.staff_no = e.staff_no
                    ORDER BY d.incident_date DESC
                """, conn)
                
                if discipline_report_df.empty:
                    st.info("No discipline records found")
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        case_type_filter = st.multiselect("Case Type",
                            options=sorted(discipline_report_df['case_type'].dropna().unique()) if 'case_type' in discipline_report_df.columns else [],
                            default=[],
                            key="discipline_case_type_filter")
                    with col2:
                        status_filter = st.multiselect("Status",
                            options=sorted(discipline_report_df['status'].dropna().unique()) if 'status' in discipline_report_df.columns else [],
                            default=[],
                            key="discipline_status_filter")
                    with col3:
                        employee_filter = st.multiselect("Employee",
                            options=sorted(discipline_report_df['employee_name'].dropna().unique()) if 'employee_name' in discipline_report_df.columns else [],
                            default=[],
                            key="discipline_employee_filter")
                    
                    filtered_disc = discipline_report_df.copy()
                    if case_type_filter and 'case_type' in filtered_disc.columns:
                        filtered_disc = filtered_disc[filtered_disc['case_type'].isin(case_type_filter)]
                    if status_filter and 'status' in filtered_disc.columns:
                        filtered_disc = filtered_disc[filtered_disc['status'].isin(status_filter)]
                    if employee_filter and 'employee_name' in filtered_disc.columns:
                        filtered_disc = filtered_disc[filtered_disc['employee_name'].isin(employee_filter)]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Cases", len(discipline_report_df))
                    with col2:
                        open_cases = len(discipline_report_df[discipline_report_df['status'] != 'Closed']) if 'status' in discipline_report_df.columns else 0
                        st.metric("Open Cases", open_cases)
                    with col3:
                        closed_cases = len(discipline_report_df[discipline_report_df['status'] == 'Closed']) if 'status' in discipline_report_df.columns else 0
                        st.metric("Closed Cases", closed_cases)
                    with col4:
                        active_employees = discipline_report_df['staff_no'].nunique()
                        st.metric("Employees Involved", active_employees)
                    
                    if 'case_type' in filtered_disc.columns and not filtered_disc.empty:
                        case_type_counts = filtered_disc['case_type'].value_counts().reset_index()
                        case_type_counts.columns = ['Case Type', 'Count']
                        fig_case = px.pie(case_type_counts, values='Count', names='Case Type',
                                         title="Case Type Distribution", hole=0.3)
                        fig_case.update_layout(height=400)
                        st.plotly_chart(fig_case, use_container_width=True, key="discipline_case_type_pie")
                    
                    st.markdown("#### Discipline Cases")
                    display_cols = ['case_number', 'employee_name', 'case_type', 'incident_date', 
                                   'status', 'hearing_date', 'decision_date', 'penalty']
                    available_cols = [c for c in display_cols if c in filtered_disc.columns]
                    st.dataframe(filtered_disc[available_cols], use_container_width=True)
                    
                    export_data(filtered_disc, "Discipline_Report")
                    
            except Exception as e:
                st.error(f"Error loading discipline data: {e}")
        
        with report_tab8:
            st.markdown("### 📄 Contract Reports")
            
            try:
                contracts_report_df = pd.read_sql("""
                    SELECT c.*, e.name as employee_name, e.department 
                    FROM employee_contracts c
                    LEFT JOIN employees e ON c.staff_no = e.staff_no
                    ORDER BY c.start_date DESC
                """, conn)
                
                if contracts_report_df.empty:
                    st.info("No contract records found")
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        contract_type_filter = st.multiselect("Contract Type",
                            options=sorted(contracts_report_df['contract_type'].dropna().unique()) if 'contract_type' in contracts_report_df.columns else [],
                            default=[],
                            key="contract_type_filter")
                    with col2:
                        status_filter_contract = st.multiselect("Status",
                            options=sorted(contracts_report_df['status'].dropna().unique()) if 'status' in contracts_report_df.columns else [],
                            default=[],
                            key="status_filter_contract")
                    with col3:
                        show_expiring = st.checkbox("Show Expiring Contracts (30 days)", key="show_expiring")
                    
                    filtered_contracts = contracts_report_df.copy()
                    if contract_type_filter and 'contract_type' in filtered_contracts.columns:
                        filtered_contracts = filtered_contracts[filtered_contracts['contract_type'].isin(contract_type_filter)]
                    if status_filter_contract and 'status' in filtered_contracts.columns:
                        filtered_contracts = filtered_contracts[filtered_contracts['status'].isin(status_filter_contract)]
                    if show_expiring and 'end_date' in filtered_contracts.columns:
                        filtered_contracts['end_date_dt'] = pd.to_datetime(filtered_contracts['end_date'])
                        today = datetime.now()
                        expiring_soon = (filtered_contracts['end_date_dt'] - today).dt.days
                        filtered_contracts = filtered_contracts[(expiring_soon >= 0) & (expiring_soon <= 30)]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Contracts", len(contracts_report_df))
                    with col2:
                        active_contracts = len(contracts_report_df[contracts_report_df['status'] == 'Active']) if 'status' in contracts_report_df.columns else 0
                        st.metric("Active Contracts", active_contracts)
                    with col3:
                        expired_contracts = len(contracts_report_df[contracts_report_df['status'] == 'Expired']) if 'status' in contracts_report_df.columns else 0
                        st.metric("Expired Contracts", expired_contracts)
                    with col4:
                        permanent_contracts = len(contracts_report_df[contracts_report_df['contract_type'] == 'Permanent']) if 'contract_type' in contracts_report_df.columns else 0
                        st.metric("Permanent Staff", permanent_contracts)
                    
                    st.markdown("#### Contract Records")
                    display_cols = ['employee_name', 'department', 'contract_type', 'start_date', 'end_date', 'status']
                    available_cols = [c for c in display_cols if c in filtered_contracts.columns]
                    st.dataframe(filtered_contracts[available_cols], use_container_width=True)
                    
                    export_data(filtered_contracts, "Contracts_Report")
                    
            except Exception as e:
                st.error(f"Error loading contract data: {e}")
        
        with report_tab9:
            st.markdown("### 🏖️ Leave Reports")
            
            try:
                leave_report_df = pd.read_sql("""
                    SELECT l.*, e.name as employee_name, e.department 
                    FROM hr_unpaid_leave l
                    LEFT JOIN employees e ON l.staff_no = e.staff_no
                    ORDER BY l.start_date DESC
                """, conn)
                
                if leave_report_df.empty:
                    st.info("No leave records found")
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        status_filter_leave = st.multiselect("Leave Status",
                            options=sorted(leave_report_df['status'].dropna().unique()) if 'status' in leave_report_df.columns else [],
                            default=[],
                            key="status_filter_leave")
                    with col2:
                        date_range_leave = st.date_input("Leave Date Range",
                            value=(datetime.now() - timedelta(days=365), datetime.now()),
                            key="leave_date_range")
                    with col3:
                        dept_filter_leave = st.multiselect("Department",
                            options=sorted(leave_report_df['department'].dropna().unique()) if 'department' in leave_report_df.columns else [],
                            default=[],
                            key="dept_filter_leave")
                    
                    filtered_leave = leave_report_df.copy()
                    if status_filter_leave and 'status' in filtered_leave.columns:
                        filtered_leave = filtered_leave[filtered_leave['status'].isin(status_filter_leave)]
                    if dept_filter_leave and 'department' in filtered_leave.columns:
                        filtered_leave = filtered_leave[filtered_leave['department'].isin(dept_filter_leave)]
                    if len(date_range_leave) == 2:
                        filtered_leave['start_date'] = pd.to_datetime(filtered_leave['start_date'])
                        filtered_leave = filtered_leave[
                            (filtered_leave['start_date'] >= pd.to_datetime(date_range_leave[0])) & 
                            (filtered_leave['start_date'] <= pd.to_datetime(date_range_leave[1]))
                        ]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Leave Requests", len(leave_report_df))
                    with col2:
                        approved_leave = len(leave_report_df[leave_report_df['status'] == 'Approved']) if 'status' in leave_report_df.columns else 0
                        st.metric("Approved", approved_leave)
                    with col3:
                        pending_leave = len(leave_report_df[leave_report_df['status'] == 'Pending']) if 'status' in leave_report_df.columns else 0
                        st.metric("Pending", pending_leave)
                    with col4:
                        total_days = filtered_leave['total_days'].sum() if 'total_days' in filtered_leave.columns else 0
                        st.metric("Total Leave Days", f"{total_days:,}")
                    
                    st.markdown("#### Leave Records")
                    display_cols = ['employee_name', 'department', 'start_date', 'end_date', 'total_days', 'reason', 'status']
                    available_cols = [c for c in display_cols if c in filtered_leave.columns]
                    st.dataframe(filtered_leave[available_cols], use_container_width=True)
                    
                    export_data(filtered_leave, "Leave_Report")
                    
            except Exception as e:
                st.error(f"Error loading leave data: {e}")
        
        with report_tab10:
            st.markdown("### 📑 Consolidated HR Reports")
            st.info("Generate comprehensive HR summary reports from all modules")
            
            try:
                employees_summary = pd.read_sql("SELECT * FROM employees", conn) if table_exists else pd.DataFrame()
                promotions_summary = pd.read_sql("SELECT * FROM hr_promotions", conn) if table_exists else pd.DataFrame()
                redesignation_summary = pd.read_sql("SELECT * FROM hr_redesignation", conn) if table_exists else pd.DataFrame()
                translation_summary = pd.read_sql("SELECT * FROM hr_translation", conn) if table_exists else pd.DataFrame()
                salary_summary = pd.read_sql("SELECT * FROM hr_salary_harmonization", conn) if table_exists else pd.DataFrame()
                confirmation_summary = pd.read_sql("SELECT * FROM hr_confirmation", conn) if table_exists else pd.DataFrame()
                discipline_summary = pd.read_sql("SELECT * FROM hr_discipline", conn) if table_exists else pd.DataFrame()
                contracts_summary = pd.read_sql("SELECT * FROM employee_contracts", conn) if table_exists else pd.DataFrame()
                leave_summary = pd.read_sql("SELECT * FROM hr_unpaid_leave", conn) if table_exists else pd.DataFrame()
                
                summary_data = {
                    'Category': [
                        '👥 TOTAL EMPLOYEES',
                        '📈 TOTAL PROMOTIONS',
                        '🔄 TOTAL REDESIGNATIONS',
                        '📄 TOTAL TRANSLATIONS',
                        '💰 TOTAL SALARY HARMONIZATIONS',
                        '✅ TOTAL CONFIRMATIONS',
                        '⚖️ TOTAL DISCIPLINE CASES',
                        '📄 TOTAL CONTRACTS',
                        '🏖️ TOTAL LEAVE REQUESTS'
                    ],
                    'Count': [
                        len(employees_summary),
                        len(promotions_summary),
                        len(redesignation_summary),
                        len(translation_summary),
                        len(salary_summary),
                        len(confirmation_summary),
                        len(discipline_summary),
                        len(contracts_summary),
                        len(leave_summary)
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                
                st.markdown("#### HR Summary Dashboard - All Modules")
                st.dataframe(summary_df, use_container_width=True)
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Department Breakdown")
                    if 'department' in employees_summary.columns and not employees_summary.empty:
                        dept_breakdown = employees_summary['department'].value_counts().reset_index()
                        dept_breakdown.columns = ['Department', 'Count']
                        fig_dept_summary = px.bar(dept_breakdown, x='Department', y='Count',
                                                  title="Employee Distribution by Department",
                                                  color='Count', color_continuous_scale='Blues')
                        fig_dept_summary.update_layout(height=400)
                        st.plotly_chart(fig_dept_summary, use_container_width=True)
                    else:
                        st.info("No department data available")
                
                with col2:
                    st.markdown("#### Gender Distribution")
                    if 'gender' in employees_summary.columns and not employees_summary.empty:
                        male_count = len(employees_summary[employees_summary['gender'] == 'Male'])
                        female_count = len(employees_summary[employees_summary['gender'] == 'Female'])
                        gender_data = pd.DataFrame({
                            'Gender': ['Male', 'Female'],
                            'Count': [male_count, female_count]
                        })
                        fig_gender = px.pie(gender_data, values='Count', names='Gender',
                                           title="Gender Distribution", hole=0.4)
                        fig_gender.update_layout(height=400)
                        st.plotly_chart(fig_gender, use_container_width=True)
                    else:
                        st.info("No gender data available")
                
                st.markdown("---")
                
                st.markdown("#### Export Options")
                
                report_format = st.radio("Select Report Format", ["CSV", "Excel", "PDF (Print)"], horizontal=True, key="consolidated_format")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📊 Generate Consolidated Report", use_container_width=True, type="primary"):
                        if report_format == "CSV":
                            csv = summary_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "📥 Download Consolidated Report (CSV)",
                                csv,
                                f"consolidated_hr_report_{datetime.now().strftime('%Y%m%d')}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        elif report_format == "Excel":
                            from io import BytesIO
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                                if not employees_summary.empty:
                                    employees_summary.to_excel(writer, sheet_name='Employees', index=False)
                                if not promotions_summary.empty:
                                    promotions_summary.to_excel(writer, sheet_name='Promotions', index=False)
                                if not redesignation_summary.empty:
                                    redesignation_summary.to_excel(writer, sheet_name='Redesignations', index=False)
                                if not translation_summary.empty:
                                    translation_summary.to_excel(writer, sheet_name='Translations', index=False)
                                if not salary_summary.empty:
                                    salary_summary.to_excel(writer, sheet_name='Salary_Harmonization', index=False)
                                if not confirmation_summary.empty:
                                    confirmation_summary.to_excel(writer, sheet_name='Confirmations', index=False)
                                if not discipline_summary.empty:
                                    discipline_summary.to_excel(writer, sheet_name='Discipline', index=False)
                                if not contracts_summary.empty:
                                    contracts_summary.to_excel(writer, sheet_name='Contracts', index=False)
                                if not leave_summary.empty:
                                    leave_summary.to_excel(writer, sheet_name='Leave', index=False)
                            st.download_button(
                                "📥 Download Consolidated Report (Excel)",
                                output.getvalue(),
                                f"consolidated_hr_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            st.info("Click Print from your browser (Ctrl+P or Cmd+P) to save as PDF")
                
                with col2:
                    if st.button("🖨️ Print Report", use_container_width=True):
                        st.markdown("""
                        <script>window.print();</script>
                        """, unsafe_allow_html=True)
                        st.info("Press Ctrl+P (Windows) or Cmd+P (Mac) to print/save as PDF")
                
                st.markdown("---")
                st.markdown("#### Quick Export - All Modules")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📋 Export Staff Data", use_container_width=True):
                        export_data(employees_summary, "Staff_Data")
                    if st.button("📈 Export Promotions", use_container_width=True):
                        export_data(promotions_summary, "Promotions_Data")
                    if st.button("🔄 Export Redesignations", use_container_width=True):
                        export_data(redesignation_summary, "Redesignations_Data")
                
                with col2:
                    if st.button("📄 Export Translations", use_container_width=True):
                        export_data(translation_summary, "Translations_Data")
                    if st.button("💰 Export Salary Harmonization", use_container_width=True):
                        export_data(salary_summary, "Salary_Harmonization_Data")
                    if st.button("✅ Export Confirmations", use_container_width=True):
                        export_data(confirmation_summary, "Confirmations_Data")
                
                with col3:
                    if st.button("⚖️ Export Discipline Cases", use_container_width=True):
                        export_data(discipline_summary, "Discipline_Data")
                    if st.button("📄 Export Contracts", use_container_width=True):
                        export_data(contracts_summary, "Contracts_Data")
                    if st.button("🏖️ Export Leave Records", use_container_width=True):
                        export_data(leave_summary, "Leave_Data")
                
            except Exception as e:
                st.error(f"Error generating consolidated report: {e}")
    
    # ==================== TAB 14: STAFF ESTABLISHMENT ====================
    with hr_tab14:
        st.subheader("📊 Staff Establishment")
        st.markdown("Manage staff establishment by department, division, and designation")
        
        try:
            if is_cloud:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS staff_establishment (
                        id SERIAL PRIMARY KEY,
                        department TEXT,
                        division TEXT,
                        designation TEXT,
                        job_group TEXT,
                        required_count INTEGER DEFAULT 0,
                        in_post_count INTEGER DEFAULT 0,
                        variance INTEGER DEFAULT 0,
                        justification TEXT,
                        status TEXT DEFAULT 'Active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT,
                        updated_by TEXT
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS staff_establishment (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        department TEXT,
                        division TEXT,
                        designation TEXT,
                        job_group TEXT,
                        required_count INTEGER DEFAULT 0,
                        in_post_count INTEGER DEFAULT 0,
                        variance INTEGER DEFAULT 0,
                        justification TEXT,
                        status TEXT DEFAULT 'Active',
                        created_at TEXT,
                        updated_at TEXT,
                        created_by TEXT,
                        updated_by TEXT
                    )
                """)
            conn.commit()
        except Exception as e:
            st.error(f"Error creating table: {e}")
        
        est_tab1, est_tab2, est_tab3 = st.tabs([
            "📊 Establishment View",
            "📥 Import Establishment",
            "✏️ Update Matrix"
        ])
        
        with est_tab1:
            st.markdown("### 📊 Current Staff Establishment")
            
            est_df = pd.read_sql("SELECT * FROM staff_establishment ORDER BY department, division, designation", conn)
            
            if est_df.empty:
                st.info("No establishment data found. Please import using the 'Import Establishment' tab.")
            else:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    departments = ["All Departments"] + sorted(est_df['department'].dropna().unique().tolist())
                    dept_filter = st.selectbox("Filter by Department", departments, key="est_dept_filter")
                
                with col2:
                    divisions = ["All Divisions"] + sorted(est_df['division'].dropna().unique().tolist())
                    div_filter = st.selectbox("Filter by Division", divisions, key="est_div_filter")
                
                with col3:
                    job_groups = ["All Job Groups"] + sorted(est_df['job_group'].dropna().unique().tolist())
                    jg_filter = st.selectbox("Filter by Job Group", job_groups, key="est_jg_filter")
                
                with col4:
                    status_filter = st.selectbox("Filter by Status", ["All", "Active", "Archived"], key="est_status_filter")
                
                filtered_df = est_df.copy()
                if dept_filter != "All Departments":
                    filtered_df = filtered_df[filtered_df['department'] == dept_filter]
                if div_filter != "All Divisions":
                    filtered_df = filtered_df[filtered_df['division'] == div_filter]
                if jg_filter != "All Job Groups":
                    filtered_df = filtered_df[filtered_df['job_group'] == jg_filter]
                if status_filter != "All":
                    filtered_df = filtered_df[filtered_df['status'] == status_filter]
                
                st.markdown("---")
                st.markdown("### 📈 Summary Statistics")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                total_positions = len(filtered_df)
                total_required = filtered_df['required_count'].sum()
                total_in_post = filtered_df['in_post_count'].sum()
                total_variance = total_required - total_in_post
                fill_rate = (total_in_post / total_required * 100) if total_required > 0 else 0
                
                with col1:
                    st.metric("📊 Total Positions", total_positions)
                with col2:
                    st.metric("🎯 Required", f"{total_required:,}")
                with col3:
                    st.metric("👥 In-Post", f"{total_in_post:,}")
                with col4:
                    st.metric("⚠️ Variance", f"{total_variance:,}", delta=f"{-total_variance}" if total_variance > 0 else None)
                with col5:
                    st.metric("📈 Fill Rate", f"{fill_rate:.1f}%")
                
                st.markdown("---")
                
                st.markdown("### 📋 Establishment Matrix")
                
                display_df = filtered_df[['department', 'division', 'designation', 'job_group', 
                                          'required_count', 'in_post_count', 'variance', 'justification']].copy()
                display_df.columns = ['Department', 'Division', 'Designation', 'Job Group', 
                                      'Required', 'In-Post', 'Variance', 'Justification']
                
                def color_variance(val):
                    if val > 0:
                        return 'color: red; font-weight: bold'
                    elif val == 0:
                        return 'color: green; font-weight: bold'
                    return ''
                
                styled_df = display_df.style.applymap(color_variance, subset=['Variance'])
                
                st.dataframe(styled_df, use_container_width=True, height=500)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    csv = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Export Establishment Data (CSV)",
                        csv,
                        f"staff_establishment_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
        
        with est_tab2:
            st.markdown("### 📥 Import Staff Establishment")
            st.info("Upload an Excel or CSV file with the staff establishment data")
            
            template_df = pd.DataFrame({
                'department': ['Roads', 'Energy', 'Public Works'],
                'division': ['Roads Division', 'Energy Division', 'Public Works Division'],
                'designation': ['Director - Roads', 'Deputy Director', 'Chief Architect'],
                'job_group': ['R', 'Q', 'P'],
                'required_count': [1, 1, 2],
                'in_post_count': [0, 1, 1],
                'justification': ['To head the directorate', 'To head energy division', 'Senior position']
            })
            
            col1, col2 = st.columns(2)
            with col1:
                csv_template = template_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download CSV Template",
                    csv_template,
                    "establishment_template.csv",
                    "text/csv",
                    use_container_width=True
                )
            with col2:
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    template_df.to_excel(writer, sheet_name='Establishment', index=False)
                st.download_button(
                    "📥 Download Excel Template",
                    output.getvalue(),
                    "establishment_template.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.markdown("### 📂 Upload Your File")
            
            uploaded_file = st.file_uploader("Choose Excel or CSV file", type=["xlsx", "xls", "csv"], key="est_upload")
            
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        import_df = pd.read_csv(uploaded_file)
                    else:
                        import_df = pd.read_excel(uploaded_file)
                    
                    st.success(f"✅ File loaded! Found {len(import_df)} rows")
                    
                    with st.expander("📊 Preview data to import", expanded=True):
                        st.dataframe(import_df.head(20), use_container_width=True)
                    
                    required_cols = ['department', 'designation', 'required_count']
                    missing_cols = [col for col in required_cols if col not in import_df.columns]
                    
                    if missing_cols:
                        st.error(f"Missing required columns: {', '.join(missing_cols)}")
                        st.info("Please ensure your file has: department, designation, required_count")
                    else:
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            if st.button("🚀 IMPORT ESTABLISHMENT", use_container_width=True, type="primary"):
                                with st.spinner("Importing data..."):
                                    c = conn.cursor()
                                    inserted = 0
                                    updated = 0
                                    errors = []
                                    
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    for idx, row in import_df.iterrows():
                                        try:
                                            department = str(row['department']).strip() if pd.notna(row.get('department')) else ''
                                            division = str(row['division']).strip() if pd.notna(row.get('division')) else ''
                                            designation = str(row['designation']).strip() if pd.notna(row.get('designation')) else ''
                                            job_group = str(row['job_group']).strip() if pd.notna(row.get('job_group')) else ''
                                            required_count = int(row['required_count']) if pd.notna(row.get('required_count')) else 0
                                            in_post_count = int(row['in_post_count']) if pd.notna(row.get('in_post_count')) else 0
                                            justification = str(row['justification']).strip() if pd.notna(row.get('justification')) else ''
                                            
                                            if not department or not designation:
                                                errors.append(f"Row {idx+2}: Missing department or designation")
                                                continue
                                            
                                            variance = required_count - in_post_count
                                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            username = st.session_state.user['username']
                                            
                                            if is_cloud:
                                                c.execute("""
                                                    SELECT id FROM staff_establishment 
                                                    WHERE department = %s AND designation = %s
                                                """, (department, designation))
                                            else:
                                                c.execute("""
                                                    SELECT id FROM staff_establishment 
                                                    WHERE department = ? AND designation = ?
                                                """, (department, designation))
                                            
                                            existing = c.fetchone()
                                            
                                            if existing:
                                                if is_cloud:
                                                    c.execute("""
                                                        UPDATE staff_establishment SET
                                                            division = %s, job_group = %s, required_count = %s,
                                                            in_post_count = %s, variance = %s, justification = %s,
                                                            updated_at = %s, updated_by = %s
                                                        WHERE department = %s AND designation = %s
                                                    """, (division, job_group, required_count, in_post_count,
                                                          variance, justification, now, username, department, designation))
                                                else:
                                                    c.execute("""
                                                        UPDATE staff_establishment SET
                                                            division = ?, job_group = ?, required_count = ?,
                                                            in_post_count = ?, variance = ?, justification = ?,
                                                            updated_at = ?, updated_by = ?
                                                        WHERE department = ? AND designation = ?
                                                    """, (division, job_group, required_count, in_post_count,
                                                          variance, justification, now, username, department, designation))
                                                updated += 1
                                            else:
                                                if is_cloud:
                                                    c.execute("""
                                                        INSERT INTO staff_establishment (
                                                            department, division, designation, job_group,
                                                            required_count, in_post_count, variance, justification,
                                                            created_at, created_by, status
                                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                                    """, (department, division, designation, job_group,
                                                          required_count, in_post_count, variance, justification,
                                                          now, username, 'Active'))
                                                else:
                                                    c.execute("""
                                                        INSERT INTO staff_establishment (
                                                            department, division, designation, job_group,
                                                            required_count, in_post_count, variance, justification,
                                                            created_at, created_by, status
                                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                    """, (department, division, designation, job_group,
                                                          required_count, in_post_count, variance, justification,
                                                          now, username, 'Active'))
                                                inserted += 1
                                            
                                            progress_bar.progress((idx + 1) / len(import_df))
                                            status_text.text(f"Processing: {idx+1}/{len(import_df)} | ✅ Inserted: {inserted} | 🔄 Updated: {updated}")
                                            
                                        except Exception as e:
                                            errors.append(f"Row {idx+2}: {str(e)[:100]}")
                                    
                                    conn.commit()
                                    
                                    st.success(f"✅ Import completed! Inserted: {inserted}, Updated: {updated}")
                                    if errors:
                                        with st.expander(f"⚠️ {len(errors)} errors"):
                                            for err in errors[:20]:
                                                st.write(f"- {err}")
                                    
                                    st.rerun()
                                    
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
        
        with est_tab3:
            st.markdown("### ✏️ Update Implementation Matrix")
            st.info("Update the current in-post counts to track recruitment progress")
            
            update_df = pd.read_sql("SELECT * FROM staff_establishment WHERE status = 'Active' ORDER BY department, division, designation", conn)
            
            if update_df.empty:
                st.info("No active establishment data found. Please import first.")
            else:
                departments = ["All Departments"] + sorted(update_df['department'].dropna().unique().tolist())
                selected_dept = st.selectbox("Select Department", departments, key="update_dept")
                
                if selected_dept != "All Departments":
                    filtered_update = update_df[update_df['department'] == selected_dept]
                else:
                    filtered_update = update_df
                
                st.markdown("---")
                st.markdown("### 📝 Update In-Post Counts")
                
                edited_data = []
                
                for idx, row in filtered_update.iterrows():
                    with st.container():
                        col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"**{row['designation']}**")
                            st.caption(f"Dept: {row['department']} | Div: {row['division']}")
                        with col2:
                            st.markdown(f"JG: {row['job_group']}")
                        with col3:
                            st.metric("Required", int(row['required_count']))
                        with col4:
                            new_in_post = st.number_input(
                                "In-Post",
                                min_value=0,
                                max_value=int(row['required_count']) + 10,
                                value=int(row['in_post_count']),
                                step=1,
                                key=f"inpost_{row['id']}",
                                label_visibility="collapsed"
                            )
                        with col5:
                            variance = int(row['required_count']) - new_in_post
                            if variance > 0:
                                st.metric("Variance", variance, delta=f"-{variance}", delta_color="inverse")
                            else:
                                st.metric("Variance", variance, delta_color="off")
                        with col6:
                            status_color = "🟢" if variance == 0 else "🟡" if variance <= 3 else "🔴"
                            status_text_status = "Filled" if variance == 0 else "Partial" if variance <= 3 else "Urgent"
                            st.markdown(f"{status_color} {status_text_status}")
                        
                        edited_data.append({
                            'id': row['id'],
                            'new_in_post': new_in_post,
                            'variance': variance
                        })
                        
                        st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("💾 SAVE UPDATES", use_container_width=True, type="primary"):
                        try:
                            c = conn.cursor()
                            saved = 0
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            username = st.session_state.user['username']
                            
                            for item in edited_data:
                                if is_cloud:
                                    c.execute("""
                                        UPDATE staff_establishment 
                                        SET in_post_count = %s, variance = %s, updated_at = %s, updated_by = %s
                                        WHERE id = %s
                                    """, (item['new_in_post'], item['variance'], now, username, item['id']))
                                else:
                                    c.execute("""
                                        UPDATE staff_establishment 
                                        SET in_post_count = ?, variance = ?, updated_at = ?, updated_by = ?
                                        WHERE id = ?
                                    """, (item['new_in_post'], item['variance'], now, username, item['id']))
                                saved += 1
                            
                            conn.commit()
                            
                            log_audit(st.session_state.user['username'], "UPDATE_ESTABLISHMENT", 0, 
                                     f"Updated {saved} establishment records", "Success")
                            
                            st.success(f"✅ Successfully updated {saved} records!")
                            st.balloons()
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error saving updates: {e}")
                
                st.markdown("---")
                st.markdown("### 📊 Recruitment Summary")
                
                summary_data = []
                for item in edited_data:
                    row = filtered_update[filtered_update['id'] == item['id']].iloc[0]
                    summary_data.append({
                        'Department': row['department'],
                        'Division': row['division'],
                        'Designation': row['designation'],
                        'Job Group': row['job_group'],
                        'Required': int(row['required_count']),
                        'Current In-Post': item['new_in_post'],
                        'To Recruit': item['variance'],
                        'Status': 'Filled' if item['variance'] == 0 else 'Partial' if item['variance'] <= 3 else 'Urgent'
                    })
                
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, use_container_width=True)
                
                csv_summary = summary_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Recruitment Summary (CSV)",
                    csv_summary,
                    f"recruitment_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
    
    # ==================== TAB 15: MONTHLY STAFF RETURNS ====================
    with hr_tab15:
        st.subheader("📋 Monthly Staff Returns")
        st.markdown("Submit and track monthly staff returns by department")
        
        try:
            if is_cloud:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS monthly_staff_returns (
                        id SERIAL PRIMARY KEY,
                        department TEXT,
                        report_month TEXT,
                        upload_date TIMESTAMP,
                        file_name TEXT,
                        staff_data JSONB,
                        total_staff INTEGER,
                        submitted_by TEXT,
                        status TEXT DEFAULT 'Submitted',
                        remarks TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS monthly_staff_returns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        department TEXT,
                        report_month TEXT,
                        upload_date TEXT,
                        file_name TEXT,
                        staff_data TEXT,
                        total_staff INTEGER,
                        submitted_by TEXT,
                        status TEXT DEFAULT 'Submitted',
                        remarks TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
            conn.commit()
        except Exception as e:
            st.error(f"Error creating table: {e}")
        
        departments = [
            "Finance", "Planning", "Procurement", "Roads", "Public Works",
            "Transport", "Energy", "Agriculture", "Health", "Education",
            "ICT", "Human Resource", "Administration", "Lands", "Trade and Tourism",
            "Water", "Environment", "Gender", "Youth", "Cooperative"
        ]
        
        current_month_num = datetime.now().month
        
        returns_tab1, returns_tab2 = st.tabs([
            "📝 Upload Monthly Return",
            "📊 View All Returns (Admin Only)"
        ])
        
        with returns_tab1:
            st.markdown("### 📝 Submit Monthly Staff Return")
            st.info("Upload your departmental staff list for the selected month")
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_dept = st.selectbox("Select Department", departments, key="return_dept")
                months = ["January", "February", "March", "April", "May", "June", 
                         "July", "August", "September", "October", "November", "December"]
                selected_month = st.selectbox("Select Report Month", months, index=current_month_num - 1, key="return_month")
                selected_year = st.number_input("Select Year", min_value=2020, max_value=2030, value=datetime.now().year, key="return_year")
            
            with col2:
                st.markdown("### 📂 Upload File")
                st.caption("Supported formats: Excel (.xlsx, .xls) or CSV")
                
                template_df = pd.DataFrame({
                    'S/NO': [1, 2, 3],
                    'NAME': ['John Doe', 'Jane Smith', 'Peter Mwangi'],
                    'P/NO': ['12345678', '87654321', '11223344'],
                    'AGE': [35, 28, 42],
                    'DESIGNATION': ['Accountant', 'HR Officer', 'Economist'],
                    'J.G': ['K', 'J', 'M'],
                    'STATION': ['Headquarters', 'Headquarters', 'Sub-County Office']
                })
                
                col_a, col_b = st.columns(2)
                with col_a:
                    csv_template = template_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download CSV Template",
                        csv_template,
                        f"staff_return_template_{selected_dept}_{selected_month}_{selected_year}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                with col_b:
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        template_df.to_excel(writer, sheet_name='Staff Return', index=False)
                    st.download_button(
                        "📥 Download Excel Template",
                        output.getvalue(),
                        f"staff_return_template_{selected_dept}_{selected_month}_{selected_year}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            
            month_year_key = f"{selected_month}_{selected_year}"
            
            if is_cloud:
                cursor.execute("""
                    SELECT id, upload_date, submitted_by, total_staff 
                    FROM monthly_staff_returns 
                    WHERE department = %s AND report_month = %s
                """, (selected_dept, month_year_key))
            else:
                cursor.execute("""
                    SELECT id, upload_date, submitted_by, total_staff 
                    FROM monthly_staff_returns 
                    WHERE department = ? AND report_month = ?
                """, (selected_dept, month_year_key))
            
            existing_return = cursor.fetchone()
            
            if existing_return:
                st.warning(f"⚠️ A return for {selected_dept} - {selected_month} {selected_year} already exists!")
                st.info(f"Submitted on: {existing_return[1]} by {existing_return[2]} | Staff count: {existing_return[3]}")
            
            st.markdown("---")
            
            uploaded_file = st.file_uploader(
                "Choose Excel or CSV file",
                type=["xlsx", "xls", "csv"],
                key="monthly_return_upload"
            )
            
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    st.success(f"✅ File loaded! Found {len(df)} rows")
                    
                    df.columns = df.columns.str.upper().str.strip()
                    required_cols = ['NAME', 'P/NO', 'DESIGNATION']
                    missing_cols = [col for col in required_cols if col not in df.columns]
                    
                    if missing_cols:
                        st.error(f"Missing required columns: {', '.join(missing_cols)}")
                    else:
                        with st.expander("📊 Preview data to import", expanded=True):
                            st.dataframe(df.head(20), use_container_width=True)
                        
                        st.markdown("### 📊 Summary Statistics")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Total Staff", len(df))
                        with col2:
                            unique_stations = df['STATION'].nunique() if 'STATION' in df.columns else 0
                            st.metric("Stations", unique_stations)
                        with col3:
                            if 'J.G' in df.columns:
                                st.metric("Job Groups", len(df['J.G'].value_counts()))
                            else:
                                st.metric("Job Groups", "N/A")
                        with col4:
                            avg_age = df['AGE'].mean() if 'AGE' in df.columns else 0
                            st.metric("Average Age", f"{avg_age:.0f}" if avg_age > 0 else "N/A")
                        
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            if st.button("✅ SUBMIT MONTHLY RETURN", use_container_width=True, type="primary"):
                                with st.spinner("Submitting..."):
                                    try:
                                        staff_json = df.to_json(orient='records')
                                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        username = st.session_state.user['username']
                                        
                                        if existing_return:
                                            if is_cloud:
                                                cursor.execute("""
                                                    UPDATE monthly_staff_returns 
                                                    SET staff_data = %s, total_staff = %s, 
                                                        file_name = %s, updated_at = %s, submitted_by = %s,
                                                        remarks = 'Updated by user'
                                                    WHERE department = %s AND report_month = %s
                                                """, (staff_json, len(df), uploaded_file.name, now, username,
                                                      selected_dept, month_year_key))
                                            else:
                                                cursor.execute("""
                                                    UPDATE monthly_staff_returns 
                                                    SET staff_data = ?, total_staff = ?, 
                                                        file_name = ?, updated_at = ?, submitted_by = ?,
                                                        remarks = 'Updated by user'
                                                    WHERE department = ? AND report_month = ?
                                                """, (staff_json, len(df), uploaded_file.name, now, username,
                                                      selected_dept, month_year_key))
                                            st.success(f"✅ Monthly return UPDATED!")
                                        else:
                                            if is_cloud:
                                                cursor.execute("""
                                                    INSERT INTO monthly_staff_returns (
                                                        department, report_month, upload_date, file_name,
                                                        staff_data, total_staff, submitted_by, created_at, status
                                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                                """, (selected_dept, month_year_key, now, uploaded_file.name,
                                                      staff_json, len(df), username, now, 'Submitted'))
                                            else:
                                                cursor.execute("""
                                                    INSERT INTO monthly_staff_returns (
                                                        department, report_month, upload_date, file_name,
                                                        staff_data, total_staff, submitted_by, created_at, status
                                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                """, (selected_dept, month_year_key, now, uploaded_file.name,
                                                      staff_json, len(df), username, now, 'Submitted'))
                                            st.success(f"✅ Monthly return SUBMITTED!")
                                        
                                        conn.commit()
                                        st.balloons()
                                        st.rerun()
                                        
                                    except Exception as e:
                                        st.error(f"Error submitting: {e}")
                    
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
        
        with returns_tab2:
            st.markdown("### 📊 All Monthly Returns")
            
            if st.session_state.user.get("role") not in ["Admin", "Super Admin"]:
                st.error("⛔ Access Denied. Admin or Super Admin privileges required.")
            else:
                returns_df = pd.read_sql("SELECT * FROM monthly_staff_returns ORDER BY id DESC", conn)
                
                if returns_df.empty:
                    st.info("No monthly returns have been submitted yet.")
                else:
                    returns_df['Display Month'] = returns_df['report_month'].apply(lambda x: x.split('_')[0] if x and '_' in x else x)
                    returns_df['Display Year'] = returns_df['report_month'].apply(lambda x: x.split('_')[1] if x and '_' in x and len(x.split('_')) > 1 else '')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        dept_options = ["All Departments"] + sorted(returns_df['department'].unique().tolist())
                        filter_dept = st.selectbox("Filter by Department", dept_options, key="return_filter_dept")
                    with col2:
                        month_options = ["All Months"] + sorted(returns_df['Display Month'].unique().tolist())
                        filter_month_display = st.selectbox("Filter by Month", month_options, key="return_filter_month")
                    
                    filtered_returns = returns_df.copy()
                    if filter_dept != "All Departments":
                        filtered_returns = filtered_returns[filtered_returns['department'] == filter_dept]
                    if filter_month_display != "All Months":
                        filtered_returns = filtered_returns[filtered_returns['Display Month'] == filter_month_display]
                    
                    st.markdown("---")
                    st.markdown("### 📊 Summary Statistics")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    total_staff_sum = filtered_returns['total_staff'].sum()
                    
                    with col1:
                        st.metric("📋 Total Returns", len(filtered_returns))
                    with col2:
                        st.metric("🏢 Departments", filtered_returns['department'].nunique())
                    with col3:
                        st.metric("📅 Months", filtered_returns['Display Month'].nunique())
                    with col4:
                        st.metric("👥 Total Staff", f"{total_staff_sum:,}")
                    
                    st.markdown("---")
                    st.markdown("### 📋 Returns List")
                    
                    display_df = filtered_returns[['department', 'Display Month', 'Display Year', 'upload_date', 
                                                    'total_staff', 'submitted_by', 'file_name']].copy()
                    display_df.columns = ['Department', 'Month', 'Year', 'Upload Date', 'Staff Count', 'Submitted By', 'File Name']
                    st.dataframe(display_df, use_container_width=True)
                    
                    st.markdown("### 📥 Download Options")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if not filtered_returns.empty:
                            selected_return_id = st.selectbox(
                                "Select Return to Download",
                                filtered_returns['id'].tolist(),
                                format_func=lambda x: f"{filtered_returns[filtered_returns['id']==x]['department'].iloc[0]} - {filtered_returns[filtered_returns['id']==x]['Display Month'].iloc[0]} {filtered_returns[filtered_returns['id']==x]['Display Year'].iloc[0]}",
                                key="download_select"
                            )
                            
                            if selected_return_id:
                                selected = filtered_returns[filtered_returns['id'] == selected_return_id].iloc[0]
                                import json
                                staff_data = json.loads(selected['staff_data'])
                                staff_df = pd.DataFrame(staff_data)
                                
                                csv_data = staff_df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    f"📥 Download {selected['department']} - {selected['Display Month']} {selected['Display Year']} (CSV)",
                                    csv_data,
                                    f"staff_return_{selected['department']}_{selected['Display Month']}_{selected['Display Year']}.csv",
                                    "text/csv",
                                    use_container_width=True
                                )
                    
                    with col2:
                        if st.button("📊 Generate Consolidated Report", use_container_width=True):
                            all_staff = []
                            for _, row in filtered_returns.iterrows():
                                import json
                                staff_data = json.loads(row['staff_data'])
                                df_temp = pd.DataFrame(staff_data)
                                df_temp['Department'] = row['department']
                                df_temp['Report Month'] = row['Display Month']
                                df_temp['Report Year'] = row['Display Year']
                                all_staff.append(df_temp)
                            
                            if all_staff:
                                consolidated_df = pd.concat(all_staff, ignore_index=True)
                                
                                summary_data = {
                                    'Metric': ['Total Departments', 'Total Returns', 'Total Staff', 'Generated On', 'Generated By'],
                                    'Value': [
                                        filtered_returns['department'].nunique(),
                                        len(filtered_returns),
                                        len(consolidated_df),
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        st.session_state.user['username']
                                    ]
                                }
                                summary_df = pd.DataFrame(summary_data)
                                
                                from io import BytesIO
                                output = BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    consolidated_df.to_excel(writer, sheet_name='Staff Returns', index=False)
                                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                                
                                st.download_button(
                                    "📥 Download Consolidated Report (Excel)",
                                    output.getvalue(),
                                    f"consolidated_staff_returns_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                            else:
                                st.warning("No data to consolidate")
    
    # ==================== TAB 16: WHATSAPP HR ASSISTANT ====================
    with hr_tab16:
        st.subheader("💬 HR Assistant Chat")
        st.markdown("Chat with our AI-powered HR assistant for instant help")
        
        if 'chat_messages' not in st.session_state:
            st.session_state.chat_messages = [
                {"role": "assistant", "content": "Hello! 👋 Welcome to the Embu County HR Assistant.\n\nHow can I help you today?\n\n1️⃣ Job Vacancies & Applications\n2️⃣ HR Policies (Leave, Promotion, Conduct)\n3️⃣ Portal Support\n4️⃣ Application Status\n\nPlease reply with a number or type your question."}
            ]
        
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.markdown(f'<div style="background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; padding: 10px 15px; border-radius: 18px; border-bottom-right-radius: 4px; max-width: 75%; margin: 5px 0 5px auto; word-wrap: break-word; width: fit-fit-content;">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="background: linear-gradient(135deg, #1e3a5f, #0f2b42); color: #e2e8f0; padding: 10px 15px; border-radius: 18px; border-bottom-left-radius: 4px; max-width: 75%; margin: 5px 0; word-wrap: break-word; border: 1px solid rgba(59,130,246,0.3); width: fit-content;">{msg["content"]}</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input("", placeholder="Type your message here...", key="chat_input", label_visibility="collapsed")
        with col2:
            send_button = st.button("📤 Send", use_container_width=True)
        
        if send_button and user_input:
            st.session_state.chat_messages.append({"role": "user", "content": user_input})
            
            assistant = WhatsAppHRAssistant()
            response = assistant.process_message("app_user", user_input)
            
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
            
            st.rerun()
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_messages = [
                    {"role": "assistant", "content": "Hello! 👋 Welcome to the Embu County HR Assistant.\n\nHow can I help you today?\n\n1️⃣ Job Vacancies & Applications\n2️⃣ HR Policies (Leave, Promotion, Conduct)\n3️⃣ Portal Support\n4️⃣ Application Status\n\nPlease reply with a number or type your question."}
                ]
                st.rerun()
        
        st.caption("💡 Tip: You can ask about vacancies, leave policies, promotions, password reset, and more!")

# =========================================================
# PROFESSIONAL ENTERPRISE THEME
# EMBU COUNTY PUBLIC SERVICE BOARD HR SYSTEM
# =========================================================

def apply_theme():
    st.markdown("""
    <style>
    /* ALL CSS INSIDE HERE ONLY */
    .stApp {
        background: #050816;
    }
    
    .block-container{
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 95% !important;
    }
    
    /* Remove header whitespace */
    header {
        display: none !important;
    }
    
    footer {
        display: none !important;
    }
    
    /* HIDE THE NATIVE STREAMLIT SIDEBAR TOGGLE BUTTON */
    button[kind="header"] {
        display: none !important;
    }
    
    [data-testid="baseButton-header"] {
        display: none !important;
    }
    
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    
    /* Hide the hamburger menu and all header buttons */
    .stApp header button {
        display: none !important;
    }
    
    .css-1lsbmgv, .css-1lsbmgv button {
        display: none !important;
    }
    
    .st-emotion-cache-1lsbmgv {
        display: none !important;
    }
    
    /* Hide the sidebar resize handle */
    .st-emotion-cache-16idsys {
        display: none !important;
    }
    
    .main-title{
        font-size: 42px;
        font-weight: 800;
        color: white;
    }
    
    .sub-title{
        color: #94a3b8;
        margin-bottom: 30px;
    }
    
    .card{
        background: linear-gradient(135deg, #13294d, #0b1730);
        padding: 25px;
        border-radius: 22px;
        border: 1px solid rgba(59,130,246,0.15);
        box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }
    
    .metric-title{
        color: #94a3b8;
        font-size: 14px;
        text-transform: uppercase;
    }
    
    .metric-value{
        color: white;
        font-size: 44px;
        font-weight: 800;
    }
    
    .metric-sub{
        color: #22c55e;
        font-size: 15px;
    }
    
    .section-card{
        background: linear-gradient(135deg, #11264a, #0b1730);
        padding: 25px;
        border-radius: 22px;
        border: 1px solid rgba(59,130,246,0.15);
        margin-top: 20px;
    }
    
    .chart-title{
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 20px;
        color: white;
    }
    
    /* Fix selectbox styling */
    .stSelectbox > div {
        background-color: #0a1225 !important;
        border: 1px solid rgba(59,130,246,0.3) !important;
        border-radius: 12px !important;
    }
    
    .stSelectbox label {
        color: #94a3b8 !important;
    }
    
    /* Fix slider styling */
    .stSlider label {
        color: #94a3b8 !important;
    }
    
    /* Improve text visibility for main content */
    p, li, span, div:not(.metric-value):not(.chart-title) {
        color: #cbd5e1 !important;
    }
    
    /* Metric cards text */
    .stMetric label {
        color: #94a3b8 !important;
    }
    
    .stMetric .metric-value {
        color: white !important;
    }
    
    /* Dataframe / table styling */
    .stDataFrame {
        background-color: #0a1225 !important;
    }
    
    /* Info, warning, success boxes */
    .stAlert {
        background-color: #0a1225 !important;
        border-left: 4px solid #3b82f6 !important;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0a1225;
        border-radius: 12px;
        padding: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: white !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1225 0%, #050816 100%) !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #cbd5e1 !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox label {
        color: #94a3b8 !important;
    }
    
    /* Buttons */
    .stButton button {
        background: linear-gradient(90deg, #3b82f6, #2563eb) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
    }
    
    .stButton button:hover {
        background: linear-gradient(90deg, #2563eb, #1d4ed8) !important;
    }
    
    /* Input fields */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background-color: #0a1225 !important;
        border: 1px solid rgba(59,130,246,0.3) !important;
        color: white !important;
    }
    
    /* Date input */
    .stDateInput input {
        background-color: #0a1225 !important;
        border: 1px solid rgba(59,130,246,0.3) !important;
        color: white !important;
    }
    
    /* Multi-select */
    .stMultiSelect [data-baseweb="select"] {
        background-color: #0a1225 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #0a1225 !important;
        color: white !important;
        border-radius: 10px !important;
    }
    
    /* ============================================= */
    /* FLOATING CHAT BUTTON - FIXED VERSION */
    /* ============================================= */
    .chat-float {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #25d366, #128c7e);
        color: white;
        border-radius: 50px;
        padding: 12px 20px;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 1000;
        text-decoration: none;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.3s ease;
        border: none;
        cursor: pointer;
        font-family: inherit;
    }
    
    .chat-float:hover {
        transform: scale(1.05);
        background: linear-gradient(135deg, #128c7e, #075e54);
        box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    
    /* Mobile responsive */
    @media only screen and (max-width: 600px) {
        .chat-float {
            padding: 8px 15px;
            font-size: 12px;
            bottom: 15px;
            right: 15px;
        }
    }
    
    /* Pulse animation for attention */
    @keyframes pulse {
        0% {
            box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.4);
        }
        70% {
            box-shadow: 0 0 0 15px rgba(37, 211, 102, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(37, 211, 102, 0);
        }
    }
    
    .chat-float {
        animation: pulse 2s infinite;
    }
    </style>
    
    <div class="chat-float" id="chatFloatBtn">
        <span style="font-size: 18px;">💬</span> 
        <span>HR Assistant</span>
    </div>
    
    <script>
    // Hide any remaining toggle buttons
    setTimeout(function() {
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            const text = button.innerText || button.textContent;
            if (text === '<<<' || text === '>' || text === '<' || text === '☰') {
                button.style.display = 'none';
            }
        });
    }, 100);
    
    // Function to open the HR Assistant tab when chat button is clicked
    function openHRAssistant() {
        // First, make sure sidebar is open
        const sidebarBtn = document.querySelector('[data-testid="stSidebarCollapseButton"]');
        if (sidebarBtn) {
            sidebarBtn.click();
        }
        // Wait for sidebar animation, then find and click the HR Assistant tab
        setTimeout(function() {
            const tabs = document.querySelectorAll('[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {
                if (tabs[i].innerText.includes('HR Assistant') || tabs[i].innerText.includes('💬')) {
                    tabs[i].click();
                    break;
                }
            }
        }, 400);
    }
    
    // Attach click event after page loads
    const chatBtn = document.getElementById('chatFloatBtn');
    if (chatBtn) {
        chatBtn.onclick = openHRAssistant;
    }
    </script>
    """, unsafe_allow_html=True)
# =========================================================
# PROFESSIONAL LOGIN PAGE WITH EMAIL OTP
# =========================================================

def login():
    # Define email function INSIDE login to avoid scope issues
    import smtplib
    import random
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    def generate_otp():
        """Generate a 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    def send_otp_email(recipient_email, otp, username, purpose="verification"):
        """Send OTP verification code to user's email"""
        try:
            smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = st.secrets.get("SMTP_PORT", 587)
            sender_email = st.secrets.get("SMTP_USER")
            sender_password = st.secrets.get("SMTP_PASSWORD")
            
            if not sender_email or not sender_password:
                print("Email credentials not configured")
                return False
            
            if purpose == "verification":
                subject = "🔐 Verify Your Account - Embu County PSB"
                body = f"""
Dear {username},

Welcome to the Embu County Public Service Board HR System!

Your account has been created. To activate your account, please use the following One-Time Password (OTP):

🔑 {otp}

This OTP will expire in 15 minutes.

Once verified, you will be prompted to create your own password.

If you did not request this account, please ignore this email.

Regards,
Embu County Public Service Board
"""
            else:  # password reset
                subject = "🔐 Password Reset OTP - Embu County PSB"
                body = f"""
Dear {username},

You requested to reset your password for the Embu County Public Service Board HR System.

Your One-Time Password (OTP) is: {otp}

This OTP will expire in 10 minutes.

If you did not request this, please ignore this email.

Regards,
Embu County Public Service Board
"""
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Error sending OTP: {e}")
            return False
    
    st.markdown("""
    <style>
    /* Hide Streamlit default UI */
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    header {visibility:hidden;}
    
    .stApp {
        background: #0a0f1a !important;
    }
    
    .main .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
    }
    
    /* Left panel styling */
    .left-panel {
        background: linear-gradient(rgba(8,15,35,0.85), rgba(8,15,35,0.9)),
                    url('https://raw.githubusercontent.com/namukennedymwaniki-create/Embu-County-Publi-Service-Board/main/county_building.jpg');
        background-size: cover;
        background-position: center;
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 40px;
        border-radius: 0;
    }
    
    .logo {
        font-size: 70px;
        margin-bottom: 20px;
    }
    
    .title {
        font-size: 32px;
        font-weight: 700;
        color: white;
        line-height: 1.3;
    }
    
    .title span {
        color: #4f7cff;
    }
    
    .subtitle {
        font-size: 14px;
        color: #94a3b8;
        margin-top: 20px;
    }
    
    /* Right panel styling */
    .right-panel {
        background: linear-gradient(135deg, #0f1730, #0a1225);
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 40px;
    }
    
    .form-title {
        font-size: 32px;
        font-weight: 700;
        color: white;
        text-align: center;
        margin-bottom: 8px;
    }
    
    .form-sub {
        font-size: 14px;
        color: #94a3b8;
        text-align: center;
        margin-bottom: 40px;
    }
    
    /* Input styling */
    .stTextInput input {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        color: white !important;
        font-size: 14px !important;
    }
    
    .stTextInput input:focus {
        border-color: #4f7cff !important;
    }
    
    /* Button styling */
    .stButton button {
        background: linear-gradient(90deg, #4f7cff, #7c3aed) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(79,124,255,0.4);
    }
    
    /* Checkbox styling */
    .stCheckbox label {
        color: #94a3b8 !important;
    }
    
    /* Divider */
    .divider {
        text-align: center;
        color: #64748b;
        font-size: 12px;
        margin: 25px 0 20px 0;
        position: relative;
    }
    
    .divider::before,
    .divider::after {
        content: '';
        position: absolute;
        top: 50%;
        width: 42%;
        height: 1px;
        background: rgba(255,255,255,0.1);
    }
    
    .divider::before {
        left: 0;
    }
    
    .divider::after {
        right: 0;
    }
    
    /* Social buttons row */
    .social-row {
        display: flex;
        gap: 12px;
        margin-top: 10px;
    }
    
    .social-btn {
        flex: 1;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        font-size: 13px;
        color: #cbd5e1;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .social-btn:hover {
        background: rgba(255,255,255,0.1);
        border-color: #4f7cff;
    }
    
    .forgot-password {
        text-align: right;
        margin-top: 8px;
    }
    
    .forgot-password button {
        background: none !important;
        color: #4f7cff !important;
        font-size: 12px !important;
        padding: 0 !important;
        text-decoration: none;
        box-shadow: none !important;
    }
    
    .forgot-password button:hover {
        text-decoration: underline;
        transform: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state for forgot password
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    if 'reset_stage' not in st.session_state:
        st.session_state.reset_stage = 1
    if 'reset_email' not in st.session_state:
        st.session_state.reset_email = None
    if 'reset_username' not in st.session_state:
        st.session_state.reset_username = None
    
    # =====================================================
    # OTP VERIFICATION FLOW (First-time login)
    # =====================================================
    if st.session_state.get('show_otp_verification', False):
        st.markdown("""
        <div class="right-panel" style="height: 100vh; display: flex; flex-direction: column; justify-content: center; padding: 40px;">
            <div class="form-title">🔐 Verify Your Account</div>
            <div class="form-sub">Enter the OTP sent to your email to verify your account</div>
        """, unsafe_allow_html=True)
        
        # Show email being verified
        st.info(f"📧 Verification code sent to your email")
        
        entered_otp = st.text_input("", placeholder="Enter 6-digit OTP", type="password", label_visibility="collapsed", key="verify_otp_input")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Verify OTP", use_container_width=True):
                if entered_otp:
                    conn = get_conn()
                    cursor = conn.cursor()
                    is_cloud = st.secrets.get("DATABASE_URL") is not None
                    
                    try:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        user_id = st.session_state.pending_verification_user
                        
                        if is_cloud:
                            cursor.execute("""
                                SELECT username, verification_otp, verification_otp_expiry 
                                FROM users 
                                WHERE id = %s
                            """, (user_id,))
                        else:
                            cursor.execute("""
                                SELECT username, verification_otp, verification_otp_expiry 
                                FROM users 
                                WHERE id = ?
                            """, (user_id,))
                        
                        user_data = cursor.fetchone()
                        
                        if user_data:
                            stored_otp = user_data[1]
                            otp_expiry = user_data[2]
                            
                            if stored_otp == entered_otp and otp_expiry > current_time:
                                # OTP verified - mark user as verified
                                if is_cloud:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET is_verified = TRUE, verification_otp = NULL, verification_otp_expiry = NULL 
                                        WHERE id = %s
                                    """, (user_id,))
                                else:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET is_verified = TRUE, verification_otp = NULL, verification_otp_expiry = NULL 
                                        WHERE id = ?
                                    """, (user_id,))
                                conn.commit()
                                
                                st.success("✅ Account verified successfully!")
                                st.info("Please set your new password below.")
                                
                                # Show password reset form
                                st.session_state.show_password_reset = True
                                st.session_state.reset_username = user_data[0]
                                st.session_state.show_otp_verification = False
                                st.rerun()
                            else:
                                st.error("❌ Invalid or expired OTP")
                        else:
                            st.error("User not found")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        conn.close()
                else:
                    st.warning("⚠️ Please enter the OTP")
        
        with col2:
            if st.button("Resend OTP", use_container_width=True):
                # Resend OTP
                conn = get_conn()
                cursor = conn.cursor()
                is_cloud = st.secrets.get("DATABASE_URL") is not None
                
                try:
                    user_id = st.session_state.pending_verification_user
                    
                    if is_cloud:
                        cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
                    else:
                        cursor.execute("SELECT username, email FROM users WHERE id = ?", (user_id,))
                    
                    user_data = cursor.fetchone()
                    
                    if user_data:
                        import random
                        new_otp = str(random.randint(100000, 999999))
                        new_expiry = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
                        
                        if is_cloud:
                            cursor.execute("""
                                UPDATE users 
                                SET verification_otp = %s, verification_otp_expiry = %s 
                                WHERE id = %s
                            """, (new_otp, new_expiry, user_id))
                        else:
                            cursor.execute("""
                                UPDATE users 
                                SET verification_otp = ?, verification_otp_expiry = ? 
                                WHERE id = ?
                            """, (new_otp, new_expiry, user_id))
                        conn.commit()
                        
                        send_otp_email(user_data[1], new_otp, user_data[0], purpose="verification")
                        st.success("✅ New OTP sent to your email!")
                except Exception as e:
                    st.error(f"Error resending OTP: {e}")
                finally:
                    conn.close()
        
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # =====================================================
    # PASSWORD RESET FLOW (After verification)
    # =====================================================
    if st.session_state.get('show_password_reset', False):
        st.markdown("""
        <div class="right-panel" style="height: 100vh; display: flex; flex-direction: column; justify-content: center; padding: 40px;">
            <div class="form-title">🔐 Create New Password</div>
            <div class="form-sub">Set your new password to complete account setup</div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("first_time_password_form"):
                new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password")
                
                submitted = st.form_submit_button("Create Password", use_container_width=True, type="primary")
                
                if submitted:
                    if not new_password:
                        st.error("❌ Password cannot be empty")
                    elif len(new_password) < 4:
                        st.error("❌ Password must be at least 4 characters")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match")
                    else:
                        conn = get_conn()
                        cursor = conn.cursor()
                        is_cloud = st.secrets.get("DATABASE_URL") is not None
                        
                        hashed_password = hash_password(new_password)
                        username = st.session_state.reset_username
                        
                        if is_cloud:
                            cursor.execute("""
                                UPDATE users 
                                SET password = %s, temp_password = NULL 
                                WHERE username = %s
                            """, (hashed_password, username))
                        else:
                            cursor.execute("""
                                UPDATE users 
                                SET password = ?, temp_password = NULL 
                                WHERE username = ?
                            """, (hashed_password, username))
                        
                        conn.commit()
                        conn.close()
                        
                        log_audit(username, "PASSWORD_SET", 0, "First-time password set after verification", "Success")
                        
                        st.success("✅ Password created successfully!")
                        st.info("You can now login with your new password.")
                        
                        st.session_state.show_password_reset = False
                        st.session_state.reset_username = None
                        st.session_state.pending_verification_user = None
                        
                        st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Create two columns for the layout
    left_col, right_col = st.columns([1, 1], gap="large")
    
    # ==================== LEFT COLUMN ====================
    with left_col:
        st.markdown("""
        <div class="left-panel">
            <div class="logo">🏛️</div>
            <div class="title">
                Embu County<br>
                <span>Public Service Board</span>
            </div>
            <div class="subtitle">
                Empowering Excellence<br>
                Serving the Community
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ==================== RIGHT COLUMN ====================
    with right_col:
        # Check if showing forgot password form
        if st.session_state.show_forgot_password:
            
            # STAGE 1: Enter email
            if st.session_state.reset_stage == 1:
                st.markdown("""
                <div class="right-panel">
                    <div class="form-title">🔐 Reset Password</div>
                    <div class="form-sub">Enter your email address to receive a verification code</div>
                </div>
                """, unsafe_allow_html=True)
                
                reset_email = st.text_input("", placeholder="Email Address", label_visibility="collapsed", key="reset_email_input")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Send Verification Code", use_container_width=True):
                        if reset_email and '@' in reset_email:
                            conn = get_conn()
                            cursor = conn.cursor()
                            is_cloud = st.secrets.get("DATABASE_URL") is not None
                            
                            try:
                                # Find user by email
                                if is_cloud:
                                    cursor.execute("SELECT username, email FROM users WHERE email = %s", (reset_email,))
                                else:
                                    cursor.execute("SELECT username, email FROM users WHERE email = ?", (reset_email,))
                                
                                user = cursor.fetchone()
                                
                                if user:
                                    username = user[0]
                                    email = user[1]
                                    
                                    # Generate OTP
                                    otp = generate_otp()
                                    expiry = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    # Store OTP in database
                                    if is_cloud:
                                        cursor.execute("""
                                            UPDATE users 
                                            SET reset_code = %s, reset_code_expiry = %s, reset_attempts = 0
                                            WHERE username = %s
                                        """, (otp, expiry, username))
                                    else:
                                        cursor.execute("""
                                            UPDATE users 
                                            SET reset_code = ?, reset_code_expiry = ?, reset_attempts = 0
                                            WHERE username = ?
                                        """, (otp, expiry, username))
                                    conn.commit()
                                                                    # Try to send email
                                    email_sent = send_otp_email(email, otp, username, purpose="reset")
                                    
                                    if email_sent:
                                        st.success(f"✅ Verification code sent to {email}")
                                    else:
                                        st.warning("⚠️ Email not configured. For testing, use this OTP:")
                                        st.code(otp, language="text")
                                    
                                    st.session_state.reset_email = email
                                    st.session_state.reset_username = username
                                    st.session_state.reset_stage = 2
                                    st.rerun()
                                else:
                                    st.error("❌ No account found with that email address")
                            except Exception as e:
                                st.error(f"Error: {e}")
                            finally:
                                conn.close()
                        else:
                            st.warning("⚠️ Please enter a valid email address")
                
                with col2:
                    if st.button("← Back to Login", use_container_width=True):
                        st.session_state.show_forgot_password = False
                        st.session_state.reset_stage = 1
                        st.rerun()
            
            # STAGE 2: Verify OTP
            elif st.session_state.reset_stage == 2:
                st.markdown(f"""
                <div class="right-panel">
                    <div class="form-title">🔐 Verify Code</div>
                    <div class="form-sub">Enter the 6-digit code sent to {st.session_state.reset_email}</div>
                </div>
                """, unsafe_allow_html=True)
                
                entered_otp = st.text_input("", placeholder="Enter 6-digit code", type="password", label_visibility="collapsed", key="otp_input")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Verify Code", use_container_width=True):
                        if entered_otp:
                            conn = get_conn()
                            cursor = conn.cursor()
                            is_cloud = st.secrets.get("DATABASE_URL") is not None
                            
                            try:
                                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                if is_cloud:
                                    cursor.execute("""
                                        SELECT username FROM users 
                                        WHERE username = %s AND reset_code = %s AND reset_code_expiry > %s
                                    """, (st.session_state.reset_username, entered_otp, current_time))
                                else:
                                    cursor.execute("""
                                        SELECT username FROM users 
                                        WHERE username = ? AND reset_code = ? AND reset_code_expiry > ?
                                    """, (st.session_state.reset_username, entered_otp, current_time))
                                
                                user = cursor.fetchone()
                                
                                if user:
                                    st.success("✅ Code verified! Enter your new password.")
                                    st.session_state.reset_stage = 3
                                    st.rerun()
                                else:
                                    st.error("❌ Invalid or expired verification code")
                            except Exception as e:
                                st.error(f"Error: {e}")
                            finally:
                                conn.close()
                        else:
                            st.warning("⚠️ Please enter the verification code")
                
                with col2:
                    if st.button("← Back", use_container_width=True):
                        st.session_state.reset_stage = 1
                        st.rerun()
            
            # STAGE 3: Set new password
            elif st.session_state.reset_stage == 3:
                st.markdown("""
                <div class="right-panel">
                    <div class="form-title">🔐 Create New Password</div>
                    <div class="form-sub">Enter your new password below</div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    with st.form("reset_password_form"):
                        new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password")
                        
                        submitted = st.form_submit_button("Reset Password", use_container_width=True, type="primary")
                        
                        if submitted:
                            if not new_password:
                                st.error("❌ Password cannot be empty")
                            elif len(new_password) < 4:
                                st.error("❌ Password must be at least 4 characters")
                            elif new_password != confirm_password:
                                st.error("❌ Passwords do not match")
                            else:
                                conn = get_conn()
                                cursor = conn.cursor()
                                is_cloud = st.secrets.get("DATABASE_URL") is not None
                                
                                hashed_password = hash_password(new_password)
                                
                                if is_cloud:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET password = %s, reset_code = NULL, reset_code_expiry = NULL, reset_attempts = 0
                                        WHERE username = %s
                                    """, (hashed_password, st.session_state.reset_username))
                                else:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET password = ?, reset_code = NULL, reset_code_expiry = NULL, reset_attempts = 0
                                        WHERE username = ?
                                    """, (hashed_password, st.session_state.reset_username))
                                
                                conn.commit()
                                conn.close()
                                
                                log_audit(st.session_state.reset_username, "PASSWORD_RESET", 0, "Password reset via email OTP", "Success")
                                
                                st.success("✅ Password reset successfully!")
                                st.info("You can now login with your new password.")
                                
                                # Reset session state
                                st.session_state.show_forgot_password = False
                                st.session_state.reset_stage = 1
                                st.session_state.reset_email = None
                                st.session_state.reset_username = None
                                
                                # Use st.rerun() instead of button inside form
                                st.rerun()
        
        else:
            # Normal login form
            st.markdown("""
            <div class="right-panel">
                <div class="form-title">Welcome Back</div>
                <div class="form-sub">Sign in with your username, email, or phone number</div>
            </div>
            """, unsafe_allow_html=True)
            
            identifier = st.text_input("", placeholder="Username, Email, or Phone Number", label_visibility="collapsed", key="login_identifier")
            password = st.text_input("", placeholder="Password", type="password", label_visibility="collapsed", key="login_password")
            
            # Remember me and forgot password row
            col_a, col_b = st.columns([1, 1])
            with col_a:
                remember = st.checkbox("Remember me", value=False)
            with col_b:
                if st.button("Forgot Password?", key="forgot_pwd_btn"):
                    st.session_state.show_forgot_password = True
                    st.session_state.reset_stage = 1
                    st.rerun()
            
            # Login button
            login_btn = st.button("Login", use_container_width=True, type="primary")
            
            # Divider
            st.markdown('<div class="divider"><span>or continue with</span></div>', unsafe_allow_html=True)
            
            # Social buttons
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.button("🔗 LinkedIn", use_container_width=True, key="linkedin_btn")
            with col_s2:
                st.button("📧 Gmail", use_container_width=True, key="gmail_btn")
            with col_s3:
                st.button("📧 Yahoo", use_container_width=True, key="yahoo_btn")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # =========================================================
            # UPDATED LOGIN LOGIC WITH OTP SUPPORT
            # =========================================================
            if login_btn:
                if not identifier or not password:
                    st.error("⚠️ Please enter both identifier and password")
                else:
                    # Call the updated login_user function
                    result = login_user(identifier, password)
                    
                    if result:
                        user, login_type = result
                        
                        # Check if user is verified (for new users)
                        is_verified = user[6] if len(user) > 6 else True
                        
                        # If user logged in with OTP and not verified, redirect to verification
                        if not is_verified and login_type == "otp_login":
                            st.session_state.pending_verification_user = user[0]
                            st.session_state.pending_verification_username = user[1]
                            st.session_state.show_otp_verification = True
                            st.rerun()
                        else:
                            # Normal login flow
                            st.session_state.user = {
                                "id": user[0],
                                "username": user[1],
                                "role": user[3],
                                "email": user[4] if len(user) > 4 else None,
                                "phone": user[5] if len(user) > 5 else None
                            }
                            log_audit(user[1], "LOGIN", user[0], "User logged in")
                            st.success("✅ Login successful!")
                            st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please check your username/email/phone and password.")
# =========================================================
# UNIFIED AUDIT LOG FUNCTION (Best of Both)
# =========================================================
def log_audit(username, action, record_id, details, status="Success", before_value=None, after_value=None):
    """Enhanced audit logging with column creation and comprehensive data capture"""
    try:
        conn = get_conn()
        c = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Ensure table has all required columns
        if is_cloud:
            # PostgreSQL syntax
            try:
                c.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS status TEXT")
                c.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS ip_address TEXT")
                c.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_agent TEXT")
                c.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS session_id TEXT")
                c.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS before_value TEXT")
                c.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS after_value TEXT")
                conn.commit()
            except Exception as col_error:
                print(f"Column addition warning: {col_error}")
        else:
            # SQLite syntax
            c.execute("PRAGMA table_info(audit_log)")
            existing_cols = [col[1] for col in c.fetchall()]
            new_cols = ['status', 'ip_address', 'user_agent', 'session_id', 'before_value', 'after_value']
            for col in new_cols:
                if col not in existing_cols:
                    try:
                        c.execute(f"ALTER TABLE audit_log ADD COLUMN {col} TEXT")
                        conn.commit()
                    except Exception as col_error:
                        print(f"Column addition warning: {col_error}")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get additional info
        ip_address = "Not captured"
        user_agent = "Not captured"
        session_id = str(st.session_state.get('session_id', 'unknown'))
        
        # Insert with all columns
        if is_cloud:
            c.execute("""
                INSERT INTO audit_log (
                    username, action, record_id, details, timestamp, 
                    status, ip_address, user_agent, session_id, before_value, after_value
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, action, record_id, details, now, status, ip_address, user_agent, session_id, before_value, after_value))
        else:
            c.execute("""
                INSERT INTO audit_log (
                    username, action, record_id, details, timestamp,
                    status, ip_address, user_agent, session_id, before_value, after_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, action, record_id, details, now, status, ip_address, user_agent, session_id, before_value, after_value))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")


# =========================================================
# SIDEBAR
# =========================================================
# =========================================================
# PROFESSIONAL SIDEBAR WITH TOGGLE BUTTONS
# =========================================================

# =========================================================
# PROFESSIONAL SIDEBAR WITH TOGGLE BUTTONS
# =========================================================

def sidebar():
    """Professional sidebar with role-based menu"""
    
    # Initialize sidebar state
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False
    
    # If sidebar is collapsed, return None
    if st.session_state.sidebar_collapsed:
        return None
    
    with st.sidebar:
        # =====================================================
        # CACHED DATABASE STATS (Only for OPEN positions)
        # =====================================================
        @st.cache_data(ttl=60)
        def get_stats():
            conn = get_conn()
            c = conn.cursor()
            is_cloud = st.secrets.get("DATABASE_URL") is not None
            
            # First, get list of open position titles
            try:
                if is_cloud:
                    c.execute("""
                        SELECT position_title 
                        FROM advertised_positions 
                        WHERE status = 'Open'
                    """)
                else:
                    c.execute("""
                        SELECT position_title 
                        FROM advertised_positions 
                        WHERE status = 'Open'
                    """)
                open_positions = [row[0] for row in c.fetchall()]
            except:
                open_positions = []
            
            # If there are open positions, filter stats by them
            if open_positions:
                # Create placeholders for SQL IN clause
                placeholders = ','.join(['%s'] * len(open_positions)) if is_cloud else ','.join(['?'] * len(open_positions))
                
                # Get counts only for open positions
                query = f"""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN application_status='Shortlisted' THEN 1 ELSE 0 END) as shortlisted,
                        SUM(CASE WHEN interview_score IS NOT NULL AND interview_score > 0 THEN 1 ELSE 0 END) as interviewed,
                        SUM(CASE WHEN application_status='Recommended' THEN 1 ELSE 0 END) as successful
                    FROM staff
                    WHERE position_applied IN ({placeholders})
                """
                c.execute(query, open_positions)
                result = c.fetchone()
                total = result[0] if result[0] else 0
                shortlisted = result[1] if result[1] else 0
                interviewed = result[2] if result[2] else 0
                successful = result[3] if result[3] else 0
            else:
                # No open positions, return zeros
                total = 0
                shortlisted = 0
                interviewed = 0
                successful = 0
            
            conn.close()
            return total, shortlisted, interviewed, successful
        
        total_applicants, shortlisted_count, interviewed_count, successful_count = get_stats()

        # =====================================================
        # COLLAPSE BUTTON
        # =====================================================
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("◀", help="Collapse sidebar", use_container_width=True):
                st.session_state.sidebar_collapsed = True
                st.rerun()
        
        # =====================================================
        # SIDEBAR HEADER
        # =====================================================
        st.markdown("""
        <div style="
            text-align: center;
            padding: 20px 12px;
            margin-bottom: 24px;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-radius: 16px;
            border: 1px solid rgba(59,130,246,0.2);
        ">
            <div style="
                width: 48px;
                height: 48px;
                background: linear-gradient(135deg, #3b82f6, #2563eb);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 12px auto;
            ">
                <span style="font-size: 24px;">🏛️</span>
            </div>
            <div style="font-size: 16px; font-weight: 700; color: white; letter-spacing: 0.5px;">
                EMBU COUNTY
            </div>
            <div style="font-size: 12px; font-weight: 600; color: #3b82f6; margin-top: 4px;">
                Public Service Board
            </div>
            <div style="font-size: 10px; color: #64748b; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.05);">
                Human Resource System
            </div>
        </div>
        """, unsafe_allow_html=True)

        # =====================================================
        # USER PROFILE CARD
        # =====================================================
        if "user" in st.session_state and st.session_state.user:
            username = st.session_state.user.get('username', 'User')
            user_role = st.session_state.user.get('role', 'User')
            
            # Role color coding
            role_colors = {
                "Super Admin": "#8b5cf6",  # Purple
                "Admin": "#3b82f6",         # Blue
                "User": "#10b981"           # Green
            }
            role_color = role_colors.get(user_role, "#10b981")
            
            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.08);
                padding: 14px;
                border-radius: 14px;
                margin-bottom: 16px;
                border: 1px solid rgba(255,255,255,0.06);
            ">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="
                        width: 48px;
                        height: 48px;
                        border-radius: 50%;
                        background: linear-gradient(135deg, #3b82f6, #2563eb);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 20px;
                        font-weight: bold;
                        color: white;
                    ">
                        👤
                    </div>
                    <div>
                        <div style="font-size: 15px; font-weight: 700; color: white;">
                            {username}
                        </div>
                        <div style="margin-top: 4px;">
                            <span style="
                                background: {role_color};
                                padding: 4px 10px;
                                border-radius: 20px;
                                font-size: 11px;
                                color: white;
                                font-weight: 600;
                            ">
                                {user_role}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # =====================================================
        # SIDEBAR STATS (Only for OPEN positions)
        # =====================================================
        st.markdown(f"""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:18px;">
            <div style="background:rgba(255,255,255,0.08); padding:12px; border-radius:12px; text-align:center;">
                <div style="font-size:11px; color:#cbd5e1;">Total (Open)</div>
                <div style="font-size:20px; font-weight:700; color:white; margin-top:4px;">{total_applicants}</div>
            </div>
            <div style="background:rgba(255,255,255,0.08); padding:12px; border-radius:12px; text-align:center;">
                <div style="font-size:11px; color:#cbd5e1;">Shortlisted</div>
                <div style="font-size:20px; font-weight:700; color:#3b82f6; margin-top:4px;">{shortlisted_count}</div>
            </div>
            <div style="background:rgba(255,255,255,0.08); padding:12px; border-radius:12px; text-align:center;">
                <div style="font-size:11px; color:#cbd5e1;">Interviewed</div>
                <div style="font-size:20px; font-weight:700; color:#8b5cf6; margin-top:4px;">{interviewed_count}</div>
            </div>
            <div style="background:rgba(255,255,255,0.08); padding:12px; border-radius:12px; text-align:center;">
                <div style="font-size:11px; color:#cbd5e1;">Successful</div>
                <div style="font-size:20px; font-weight:700; color:#10b981; margin-top:4px;">{successful_count}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # =====================================================
        # NAVIGATION MENU (Role-Based)
        # =====================================================
        menu_options = get_user_menu()
        
        # Menu descriptions for each item
        menu_descriptions = {
            "📊 Dashboard": "Overview & KPIs",
            "👥 Applicant Profile": "View applicant profiles",
            "📝 Applicant Registration": "Register applicants",
            "✏️ Edit Application": "Modify applications",
            "⭐ Shortlist Management": "Manage shortlisted candidates",
            "📊 Scoresheet": "Panelist scoring",
            "👔 HR Functions": "HR operations",
            "📥 Import Excel": "Bulk uploads",
            "📋 Records": "All records",
            "📈 Reports": "Analytics & reports",
            "⭐ Review": "Review and evaluate applicants",  # NEW
            "📤 Export Center": "Export data",
            "✅ Data Quality": "Validate records",
            "🔒 Audit Trail": "Track system activity",
            "💾 Backup & Restore": "Database management",
            "🧪 Test Data": "Generate sample data",
            "⚙️ Settings": "System configuration",
            "👤 Users": "User management"
        }

        menu = st.radio(
            "Navigation",
            menu_options,
            label_visibility="collapsed"
        )

        # =====================================================
        # MENU DESCRIPTION
        # =====================================================
        current_description = menu_descriptions.get(menu, "Select an option")
        st.markdown(f"""
        <div style="
            background:rgba(255,255,255,0.06);
            padding:10px;
            border-radius:10px;
            margin-top:10px;
            margin-bottom:16px;
            font-size:12px;
            color:#cbd5e1;
        ">
            {current_description}
        </div>
        """, unsafe_allow_html=True)

        # =====================================================
        # SYSTEM STATUS
        # =====================================================
        st.markdown("""
        <div style="
            background:rgba(16,185,129,0.12);
            border:1px solid rgba(16,185,129,0.2);
            padding:12px;
            border-radius:12px;
            margin-bottom:18px;
        ">
            <div style="display:flex; align-items:center; gap:8px; color:#10b981; font-size:13px; font-weight:600;">
                🟢 System Online
            </div>
            <div style="margin-top:6px; color:#cbd5e1; font-size:11px;">
                All services operational
            </div>
        </div>
        """, unsafe_allow_html=True)

        # =====================================================
        # LOGOUT BUTTON
        # =====================================================
        if st.button("🚪 Logout", use_container_width=True):
            if "user" in st.session_state and st.session_state.user:
                try:
                    log_audit(
                        st.session_state.user.get('username', 'Unknown'),
                        "LOGOUT",
                        0,
                        "User logged out"
                    )
                except:
                    pass
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # =====================================================
        # FOOTER
        # =====================================================
        st.markdown("""
        <div style="
            text-align:center;
            margin-top:22px;
            padding-top:12px;
            border-top:1px solid rgba(255,255,255,0.08);
            font-size:11px;
            color:#94a3b8;
        ">
            ECPSB HR System v2.0<br>
            Embu County Government
        </div>
        """, unsafe_allow_html=True)

    return menu


# =========================================================
# FLOATING TOGGLE BUTTON (Mobile-Friendly)
# =========================================================
# =========================================================
# SIDEBAR TOGGLE BUTTON (Mobile-Friendly)
# =========================================================
# =========================================================
# SIMPLE SIDEBAR TOGGLE BUTTON (No duplicate key issues)
# =========================================================
# =========================================================
# SIDEBAR TOGGLE BUTTON (Mobile-Friendly)
# =========================================================
def sidebar_toggle_button():
    """Create a floating toggle button in the main dashboard area"""
    
    # Initialize sidebar state if not exists
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False
    
    # Custom CSS for floating toggle button
    st.markdown("""
    <style>
    /* Floating toggle button container */
    .toggle-container {
        position: fixed;
        top: 70px;
        left: 10px;
        z-index: 999;
    }
    
    /* Floating button styling */
    .toggle-btn {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 10px 18px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .toggle-btn:hover {
        transform: translateX(3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }
    
    /* For mobile devices */
    @media only screen and (max-width: 600px) {
        .toggle-btn {
            padding: 8px 14px;
            font-size: 14px;
        }
        .toggle-container {
            top: 65px;
            left: 5px;
        }
    }
    
    /* When sidebar is collapsed, adjust button */
    .toggle-btn-collapsed {
        background: linear-gradient(135deg, #10b981, #059669);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Determine button label
    if st.session_state.sidebar_collapsed:
        button_label = "☰ MENU"
    else:
        button_label = "◀ HIDE"
    
    # Create columns for button placement - NO STATIC KEY
    col1, col2, col3 = st.columns([0.5, 8, 1])
    with col1:
        # REMOVE the key parameter - let Streamlit auto-generate
        if st.button(button_label, use_container_width=True):
            st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed
            st.rerun()
    
    # Add a small indicator when sidebar is collapsed
    if st.session_state.sidebar_collapsed:
        st.markdown("""
        <div style="
            position: fixed;
            top: 70px;
            left: 80px;
            background: rgba(59,130,246,0.9);
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 10px;
            z-index: 999;
        ">
            Click ☰ to open menu
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# ALTERNATIVE: HAMBURGER MENU BUTTON (More Modern)
# =========================================================
def hamburger_menu_button():
    """Create a modern hamburger menu button"""
    
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False
    
    # Custom CSS for hamburger menu
    st.markdown("""
    <style>
    .hamburger-btn {
        position: fixed;
        top: 15px;
        left: 15px;
        z-index: 1000;
        background: linear-gradient(135deg, #1e3a5f, #0f2b42);
        border: none;
        border-radius: 12px;
        padding: 10px 14px;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    
    .hamburger-btn:hover {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        transform: scale(1.05);
    }
    
    .hamburger-line {
        width: 25px;
        height: 3px;
        background-color: white;
        margin: 4px 0;
        border-radius: 3px;
        transition: 0.3s;
    }
    
    /* Mobile adjustments */
    @media only screen and (max-width: 600px) {
        .hamburger-btn {
            top: 10px;
            left: 10px;
            padding: 8px 12px;
        }
        .hamburger-line {
            width: 20px;
            height: 2px;
            margin: 3px 0;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display hamburger icon
    st.markdown("""
    <div class="hamburger-btn" onclick="this.style.transform='scale(0.95)'; setTimeout(() => this.style.transform='', 200);">
        <div class="hamburger-line"></div>
        <div class="hamburger-line"></div>
        <div class="hamburger-line"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create invisible button to capture click - REMOVED STATIC KEY
    col1, col2, col3 = st.columns([0.3, 8, 1])
    with col1:
        # NO key parameter here!
        if st.button("", use_container_width=True):
            st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed
            st.rerun()


def sidebar_toggle_button():
    """Create a floating toggle button in the main dashboard area"""
    
    # Initialize sidebar state if not exists
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False
    
    # Custom CSS for floating toggle button
    st.markdown("""
    <style>
    /* Floating toggle button container */
    .toggle-container {
        position: fixed;
        top: 70px;
        left: 10px;
        z-index: 999;
    }
    
    /* Floating button styling */
    .toggle-btn {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 10px 18px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .toggle-btn:hover {
        transform: translateX(3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }
    
    /* For mobile devices */
    @media only screen and (max-width: 600px) {
        .toggle-btn {
            padding: 8px 14px;
            font-size: 14px;
        }
        .toggle-container {
            top: 65px;
            left: 5px;
        }
    }
    
    /* When sidebar is collapsed, adjust button */
    .toggle-btn-collapsed {
        background: linear-gradient(135deg, #10b981, #059669);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Determine button label
    if st.session_state.sidebar_collapsed:
        button_label = "☰ MENU"
    else:
        button_label = "◀ HIDE"
    
    # Create columns for button placement - REMOVED STATIC KEY
    col1, col2, col3 = st.columns([0.5, 8, 1])
    with col1:
        # NO key parameter here!
        if st.button(button_label, use_container_width=True):
            st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed
            st.rerun()
    
    # Add a small indicator when sidebar is collapsed
    if st.session_state.sidebar_collapsed:
        st.markdown("""
        <div style="
            position: fixed;
            top: 70px;
            left: 80px;
            background: rgba(59,130,246,0.9);
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 10px;
            z-index: 999;
        ">
            Click ☰ to open menu
        </div>
        """, unsafe_allow_html=True)
# =========================================================
# DASHBOARD
# =========================================================
def dashboard():
    # Display the main dashboard with KPIs, filters, and charts
   
    # ======================================================
    # 1. CUSTOM CSS (For styling the main area)
    # ======================================================
    st.markdown("""
    <style>
        .main-title {
            font-size: 2rem;
            font-weight: 700;
            color: #1e3a5f;
            margin-bottom: 0.25rem;
        }
        .sub-title {
            font-size: 0.9rem;
            color: #6c757d;
            margin-bottom: 1rem;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }
        .metric-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #1e3a5f;
            margin: 0.5rem 0;
        }
        .metric-sub {
            font-size: 0.75rem;
            color: #adb5bd;
        }
        .section-card {
            background: white;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .chart-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1e3a5f;
            margin-bottom: 1rem;
            border-left: 4px solid #3b82f6;
            padding-left: 0.75rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ======================================================
    # 2. GET ADVERTISED POSITIONS FOR FILTER (ONLY OPEN POSITIONS)
    # ======================================================
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Initialize position_display_name with default value
    position_display_name = "All Open Positions"
    position_filter = "1=1"
    
    try:
        # Fetch ONLY OPEN positions
        if is_cloud:
            positions_df = pd.read_sql("""
                SELECT id, position_title, position_code, status 
                FROM advertised_positions 
                WHERE status = 'Open'
                ORDER BY id DESC
            """, conn)
        else:
            positions_df = pd.read_sql("""
                SELECT id, position_title, position_code, status 
                FROM advertised_positions 
                WHERE status = 'Open'
                ORDER BY id DESC
            """, conn)
    except:
        positions_df = pd.DataFrame()
    
    # ======================================================
    # 3. HEADER (Placed BEFORE position selector)
    # ======================================================
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown('<div class="main-title">Embu County Public Service Board</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sub-title">Real-time overview of Recruitment Process | <strong>{position_display_name}</strong></div>', unsafe_allow_html=True)
    
    with col2:
        if st.button("📤 Export Report", use_container_width=True):
            if 'df' in locals() and not df.empty:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV", 
                    data=csv, 
                    file_name=f"dashboard_export_{datetime.now().strftime('%Y%m%d')}.csv", 
                    mime="text/csv",
                    key="download_btn"
                )
            else:
                st.warning("No data to export")
    
    # ======================================================
    # 4. POSITION SELECTOR (Only shows OPEN positions)
    # ======================================================
    st.markdown("### 📢 Select Position to View")
    
    # Create a mapping of display text to position_code and position_title
    position_mapping = {}
    for _, row in positions_df.iterrows():
        display_text = f"{row['position_title']} ({row['position_code']})"
        position_mapping[display_text] = {
            'code': row['position_code'],
            'title': row['position_title']
        }
    
    if not positions_df.empty:
        position_options = ["All Open Positions"] + list(position_mapping.keys())
        selected_position_display = st.selectbox("Filter by Position", position_options, key="dashboard_position_filter")
        
        if selected_position_display != "All Open Positions":
            # Use position_code for filtering (more reliable)
            selected_code = position_mapping[selected_position_display]['code']
            selected_title = position_mapping[selected_position_display]['title']
            
            # Try to match by position_code first, then by title
            position_filter = f"advertisement_ref = '{selected_code}' OR position_applied = '{selected_title}'"
            position_display_name = selected_title
        else:
            # Filter to ONLY open positions using position codes
            open_codes = [row['position_code'] for _, row in positions_df.iterrows()]
            if open_codes:
                codes_str = "', '".join(open_codes)
                position_filter = f"advertisement_ref IN ('{codes_str}') OR position_applied IN (SELECT position_title FROM advertised_positions WHERE status = 'Open')"
            else:
                position_filter = "1=0"
            position_display_name = "All Open Positions"
    else:
        position_filter = "1=0"
        position_display_name = "All Open Positions"
        st.warning("⚠️ No open advertised positions found. Please create open positions in Settings > Advertised Positions.")
    
    # ======================================================
    # 5. FETCH DATA (Filtered by selected open position)
    # ======================================================
    def get_data(position_filter):
        """Fetch staff data from database filtered by position"""
        try:
            conn_local = get_conn()
            df = pd.read_sql(f"SELECT * FROM staff WHERE {position_filter}", conn_local)
            conn_local.close()
            return df
        except Exception as e:
            return pd.DataFrame(columns=['application_status', 'subcounty', 'gender', 'yob', 'created_at', 'disability', 'ethnicity', 'interview_score', 'position_applied'])
    
    df = get_data(position_filter)
    
    # Calculate stats based on filtered data
    total_applicants = len(df)
    pending = len(df[df['application_status'] == 'Pending']) if 'application_status' in df.columns else 0
    shortlisted = len(df[df['application_status'] == 'Shortlisted']) if 'application_status' in df.columns else 0
    interviewed = len(df[df['interview_score'].notna() & (df['interview_score'] > 0)]) if 'interview_score' in df.columns else 0
    successful = len(df[df['application_status'] == 'Recommended']) if 'application_status' in df.columns else 0
    hired = len(df[df['application_status'] == 'Hired']) if 'application_status' in df.columns else 0
    
    # ======================================================
    # 6. KPI CARDS (Filtered by selected open position)
    # ======================================================
    cards = st.columns(4)
    
    kpi_data = [
        ("📊 ALL APPLICANTS", str(total_applicants), f"Total Applications for {position_display_name}"),
        ("⭐ SHORTLISTED", str(shortlisted), "Selected for Interview"),
        ("🎤 INTERVIEWED", str(interviewed), "Completed Scoring"),
        ("🏆 SUCCESSFUL", str(successful), "Recommended"),
    ]
    
    for col, (title, value, subtitle) in zip(cards, kpi_data):
        with col:
            st.markdown(f"""
            <div class="card">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-sub">{subtitle}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # ======================================================
    # 7. FILTER SECTION (Additional filters)
    # ======================================================
    st.markdown("""
    <div class="section-card">
        <div class="chart-title">🔍 Additional Filters</div>
    </div>
    """, unsafe_allow_html=True)
    
    f1, f2, f3 = st.columns(3)
    
    with f1:
        subcounties = ['All Sub-Counties']
        if 'subcounty' in df.columns and not df.empty:
            subcounties += sorted(df['subcounty'].dropna().unique().tolist())
        subcounty_filter = st.selectbox("Sub-County", subcounties, key="sub_county_filter")
    
    with f2:
        gender_filter = st.selectbox("Gender", ["All Genders", "Male", "Female"], key="gender_filter")
    
    with f3:
        if 'yob' in df.columns and not df.empty and not df['yob'].isna().all():
            min_year = int(df['yob'].min())
            max_year = int(df['yob'].max())
            year_range = st.slider("Year of Birth", min_year, max_year, (min_year, max_year), key="year_filter")
        else:
            year_range = (1960, 2000)
            st.slider("Year of Birth", 1960, 2000, (1960, 2000), key="year_filter_dummy")
    
    # Apply additional filters
    filtered_df = df.copy()
    if 'subcounty' in filtered_df.columns and subcounty_filter != 'All Sub-Counties':
        filtered_df = filtered_df[filtered_df['subcounty'] == subcounty_filter]
    if 'gender' in filtered_df.columns and gender_filter != 'All Genders':
        filtered_df = filtered_df[filtered_df['gender'] == gender_filter]
    if 'yob' in filtered_df.columns:
        filtered_df = filtered_df[(filtered_df['yob'] >= year_range[0]) & (filtered_df['yob'] <= year_range[1])]
    
    # ======================================================
    # 8. CHARTS (Filtered data)
    # ======================================================
    c1, c2 = st.columns(2)
    
    # Bar Chart - Sub-County Distribution
    with c1:
        st.markdown("""
        <div class="section-card">
            <div class="chart-title">📍 Applicants by Sub-County</div>
        """, unsafe_allow_html=True)
        
        if 'subcounty' in filtered_df.columns and not filtered_df.empty:
            subcounty_counts = filtered_df['subcounty'].value_counts().head(10)
            if not subcounty_counts.empty:
                fig = go.Figure(go.Bar(
                    x=subcounty_counts.values,
                    y=subcounty_counts.index,
                    orientation='h',
                    marker_color='#3b82f6',
                    text=subcounty_counts.values,
                    textposition='outside'
                ))
                fig.update_layout(
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                    font_color="#333",
                    height=400,
                    xaxis_title="Number of Applicants",
                    yaxis_title="Sub-County",
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sub-county data available for selected filters")
        else:
            st.info("No sub-county data available")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Pie Chart - Gender Distribution
    with c2:
        st.markdown("""
        <div class="section-card">
            <div class="chart-title">⚧ Gender Distribution</div>
        """, unsafe_allow_html=True)
        
        if 'gender' in filtered_df.columns and not filtered_df.empty:
            male_count = len(filtered_df[filtered_df['gender'] == 'Male'])
            female_count = len(filtered_df[filtered_df['gender'] == 'Female'])
            if male_count > 0 or female_count > 0:
                fig2 = go.Figure(data=[go.Pie(
                    labels=["Male", "Female"],
                    values=[male_count, female_count],
                    hole=0.5,
                    marker_colors=['#3b82f6', '#ef4444'],
                    textinfo='label+percent'
                )])
                fig2.update_layout(
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                    font_color="#333",
                    height=400,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No gender data available for selected filters")
        else:
            st.info("No gender data available")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # ======================================================
    # 9. Successful Candidates Analysis (Filtered by position)
    # ======================================================
    
    # Get successful candidates (Recommended) from filtered data
    successful_df = filtered_df[filtered_df['application_status'] == 'Recommended'] if 'application_status' in filtered_df.columns else pd.DataFrame()
    
    if not successful_df.empty:
        st.markdown("### 🏆 Successful Candidates Analysis")
        
        col1, col2 = st.columns(2)
        
        # Disability Pie Chart
        with col1:
            st.markdown("""
            <div class="section-card">
                <div class="chart-title">♿ People Living with Disability</div>
            """, unsafe_allow_html=True)
            
            if 'disability' in successful_df.columns:
                disability_count = len(successful_df[successful_df['disability'].notna() & 
                                                     (successful_df['disability'] != '') & 
                                                     (successful_df['disability'] != 'None') &
                                                     (successful_df['disability'].str.lower() != 'none')])
                no_disability_count = len(successful_df) - disability_count
                
                if disability_count > 0 or no_disability_count > 0:
                    disability_percentage = (disability_count / len(successful_df)) * 100
                    
                    fig_disability = go.Figure(data=[go.Pie(
                        labels=["With Disability", "Without Disability"],
                        values=[disability_count, no_disability_count],
                        hole=0.4,
                        marker_colors=['#f59e0b', '#10b981'],
                        textinfo='label+percent'
                    )])
                    
                    fig_disability.update_layout(
                        title=f"Total Successful: {len(successful_df)} candidates",
                        paper_bgcolor="white",
                        plot_bgcolor="white",
                        font_color="#333",
                        height=400
                    )
                    
                    st.plotly_chart(fig_disability, use_container_width=True)
                    
                    st.info(f"📊 {disability_count} out of {len(successful_df)} successful candidates are Persons with Disabilities ({disability_percentage:.1f}%)")
                else:
                    st.info("No disability data available for successful candidates")
            else:
                st.info("Disability data not available")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Ethnicity Pie Chart
        with col2:
            st.markdown("""
            <div class="section-card">
                <div class="chart-title">🌍 Ethnicity Distribution</div>
            """, unsafe_allow_html=True)
            
            if 'ethnicity' in successful_df.columns:
                ethnicity_data = successful_df['ethnicity'].dropna()
                ethnicity_data = ethnicity_data[ethnicity_data != '']
                ethnicity_data = ethnicity_data[ethnicity_data.str.lower() != 'select ethnicity']
                
                if not ethnicity_data.empty:
                    ethnicity_counts = ethnicity_data.value_counts()
                    
                    fig_ethnicity = go.Figure(data=[go.Pie(
                        labels=ethnicity_counts.index,
                        values=ethnicity_counts.values,
                        hole=0.3,
                        textinfo='label+percent',
                        marker=dict(line=dict(color='white', width=2))
                    )])
                    
                    fig_ethnicity.update_layout(
                        title=f"Ethnicity Breakdown (Total: {len(successful_df)} candidates)",
                        paper_bgcolor="white",
                        plot_bgcolor="white",
                        font_color="#333",
                        height=400
                    )
                    
                    st.plotly_chart(fig_ethnicity, use_container_width=True)
                else:
                    st.info("No ethnicity data available for successful candidates")
            else:
                st.info("Ethnicity data not available")
            
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        if total_applicants > 0:
            st.info("🏆 No successful candidates (Recommended) yet for this position. Complete the scoring process to see analysis.")
    
    # ======================================================
    # 10. LOWER SECTION
    # ======================================================
    b1, b2 = st.columns(2)
    
    with b1:
        st.markdown("""
        <div class="section-card">
            <div class="chart-title">📅 Age Distribution</div>
        """, unsafe_allow_html=True)
        
        if 'yob' in filtered_df.columns and not filtered_df.empty and not filtered_df['yob'].isna().all():
            current_year = datetime.now().year
            filtered_df['age'] = current_year - filtered_df['yob']
            age_data = filtered_df['age'].dropna()
            if not age_data.empty:
                fig3 = go.Figure(data=[go.Histogram(
                    x=age_data,
                    nbinsx=15,
                    marker_color='#3b82f6',
                    opacity=0.7
                )])
                fig3.update_layout(
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                    font_color="#333",
                    height=400,
                    xaxis_title="Age (Years)",
                    yaxis_title="Number of Applicants",
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No age data available for selected filters")
        else:
            st.info("No age data available")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with b2:
        st.markdown("""
        <div class="section-card">
            <div class="chart-title">📈 Application Trend</div>
        """, unsafe_allow_html=True)
        
        if 'created_at' in filtered_df.columns and not filtered_df.empty:
            filtered_df['created_date'] = pd.to_datetime(filtered_df['created_at']).dt.date
            growth_data = filtered_df.groupby('created_date').size().reset_index(name='count')
            growth_data = growth_data.sort_values('created_date')
            if not growth_data.empty:
                fig4 = go.Figure()
                fig4.add_trace(go.Scatter(
                    x=growth_data['created_date'],
                    y=growth_data['count'],
                    mode='lines+markers',
                    line=dict(color='#3b82f6', width=3),
                    marker=dict(size=8, color='#60a5fa'),
                    fill='tozeroy',
                    fillcolor='rgba(59,130,246,0.1)'
                ))
                fig4.update_layout(
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                    font_color="#333",
                    height=400,
                    xaxis_title="Application Date",
                    yaxis_title="Number of Applications",
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No application trend data available for selected filters")
        else:
            st.info("No application trend data available")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # ======================================================
    # 11. Applications by Position (if All Open Positions selected)
    # ======================================================
    if 'selected_position_display' in locals() and selected_position_display == "All Open Positions" and not df.empty and 'position_applied' in df.columns:
        st.markdown("""
        <div class="section-card">
            <div class="chart-title">📊 Applications by Position</div>
        """, unsafe_allow_html=True)
        
        # Only show applications for OPEN positions
        open_position_titles = positions_df['position_title'].tolist()
        df_open_only = df[df['position_applied'].isin(open_position_titles)]
        
        if not df_open_only.empty:
            position_counts = df_open_only['position_applied'].value_counts().reset_index()
            position_counts.columns = ['Position', 'Count']
            
            fig_positions = px.bar(position_counts, x='Position', y='Count', 
                                   title="Applications per Open Position",
                                   color='Count',
                                   color_continuous_scale='Blues')
            fig_positions.update_layout(height=400)
            st.plotly_chart(fig_positions, use_container_width=True)
        else:
            st.info("No applications found for open positions")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    conn.close()
# =========================================================
# APPLICANT PROFILE
# =========================================================
def applicant_profile():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">applicant Profile</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">View detailed staff information</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    df = pd.read_sql("SELECT id, name, id_number, subcounty, ward FROM staff ORDER BY name", conn)
    conn.close()
    
    if df.empty:
        st.warning("No staff records found.")
        return
    
    # Staff selector
    staff_names = df['name'].tolist()
    selected_staff = st.selectbox("Select Staff Member", staff_names)
    
    # Get full details
    conn = get_conn()
    staff_data = pd.read_sql(f"SELECT * FROM staff WHERE name = '{selected_staff}'", conn)
    conn.close()
    
    if not staff_data.empty:
        staff = staff_data.iloc[0]
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                <div style="font-size: 4rem;">👤</div>
                <h3>{staff['name']}</h3>
                <p><strong>Staff ID:</strong> {staff['id']}</p>
                <p><strong>ID Number:</strong> {staff['id_number']}</p>
                <p><strong>Status:</strong> <span style="color: #28a745;">✅ Active</span></p>
                <p><strong>Record Created:</strong><br>{staff['created_at']}</p>
                <p><strong>Created By:</strong> {staff['created_by']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                <h3>📋 Personal Information</h3>
                <table style="width: 100%;">
            """, unsafe_allow_html=True)
            
            details = {
                "Gender": staff['gender'],
                "Year of Birth": staff['yob'],
                "Age": datetime.now().year - staff['yob'] if staff['yob'] else "N/A",
                "Ethnicity": staff['ethnicity'] or "Not specified",
                "Disability": staff['disability'] or "None",
                "Contact": staff['contact'] or "Not provided",
                "KCSE Year": staff['kcse'] or "Not specified",
                "Qualifications": staff['qualifications'] or "Not specified",
                "Sub-County": staff['subcounty'] or "Not specified",
                "Ward": staff['ward'] or "Not specified",
                "Experience": staff['experience'] or "Not specified",
                "Remarks": staff['remarks'] or "None"
            }
            
            for key, value in details.items():
                st.markdown(f"""
                <tr>
                    <td style='padding: 10px; border-bottom: 1px solid #e0e0e0;'><strong>{key}:</strong></td>
                    <td style='padding: 10px; border-bottom: 1px solid #e0e0e0;'>{value}</td>
                </tr>
                """, unsafe_allow_html=True)
            
            st.markdown("</table></div>", unsafe_allow_html=True)
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✏️ Edit Profile", use_container_width=True):
                st.info("Edit feature coming soon")
        with col2:
            if st.button("📄 Generate Report", use_container_width=True):
                st.info("Report generation feature coming soon")
        with col3:
            if st.button("📞 Contact Info", use_container_width=True):
                if staff['contact']:
                    st.success(f"📱 Contact: {staff['contact']}")
                else:
                    st.warning("No contact information available")

# =========================================================
# APPLICANT REGISTRATION (RECRUITMENT)
# =========================================================
    
# =====================================================
# APPLICANT REGISTRATION (RECRUITMENT) - FIXED VERSION
# =====================================================
def data_entry():
    """Complete 7-tab application form"""
    
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">📝 Job Application Form</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Dear Applicant, kindly complete the application form here.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # =====================================================
    # INITIALIZE VARIABLES AT THE START
    # =====================================================
    found_position = None
    selected_position = None
    position_applied = ""
    advertisement_ref = ""
    department = ""
    application_date = datetime.now()
    source_of_info = "Select Source"
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # =====================================================
    # FETCH ADVERTISED POSITIONS FROM DATABASE
    # =====================================================
    conn = get_conn()
    advertised_positions_list = []
    positions_df = pd.DataFrame()
    
    if conn:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            if is_cloud:
                positions_df = pd.read_sql("""
                    SELECT id, position_title, position_code, department, employment_type, vacancies, 
                           requirements, responsibilities, salary_range, application_deadline, status
                    FROM advertised_positions 
                    WHERE status = 'Open' AND application_deadline >= %s
                    ORDER BY application_deadline ASC
                """, conn, params=(today,))
            else:
                positions_df = pd.read_sql(f"""
                    SELECT id, position_title, position_code, department, employment_type, vacancies, 
                           requirements, responsibilities, salary_range, application_deadline, status
                    FROM advertised_positions 
                    WHERE status = 'Open' AND application_deadline >= '{today}'
                    ORDER BY application_deadline ASC
                """, conn)
            
            if not positions_df.empty:
                for _, row in positions_df.iterrows():
                    advertised_positions_list.append({
                        'id': row['id'],
                        'title': row['position_title'],
                        'code': row['position_code'],
                        'department': row['department'],
                        'employment_type': row['employment_type'],
                        'vacancies': row['vacancies'],
                        'requirements': row['requirements'],
                        'responsibilities': row['responsibilities'],
                        'salary_range': row['salary_range'],
                        'deadline': row['application_deadline'],
                        'status': row['status']
                    })
        except Exception as e:
            st.info("Loading advertised positions...")
    
    # =====================================================
    # SEARCH ADVERTISED POSITIONS BY POSITION CODE
    # =====================================================
    st.subheader("🔍 Search for Advertised Positions")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_position_code = st.text_input(
            "Enter Position Code to Search", 
            placeholder="e.g., CPSB/01/26(E)",
            help="Enter the position code from the job advertisement"
        )
    
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    # Search by code
    if search_button and search_position_code:
        found_position = next((p for p in advertised_positions_list if p['code'].lower() == search_position_code.lower()), None)
        
        if found_position:
            st.success(f"✅ Position Found: {found_position['title']}")
            
            with st.expander("📋 View Position Details", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Position Code:** {found_position['code']}")
                    st.write(f"**Department:** {found_position['department']}")
                    st.write(f"**Employment Type:** {found_position['employment_type']}")
                    st.write(f"**Vacancies:** {found_position['vacancies']}")
                with col2:
                    st.write(f"**Salary Range:** {found_position['salary_range']}")
                    st.write(f"**Application Deadline:** {found_position['deadline']}")
                    st.write(f"**Status:** {found_position['status']}")
                
                st.write("**Requirements:**")
                st.write(found_position['requirements'])
                st.write("**Responsibilities:**")
                st.write(found_position['responsibilities'])
        else:
            st.error(f"❌ No open position found with code: {search_position_code}")
    
    st.markdown("---")
    
    # =====================================================
    # DISPLAY AVAILABLE POSITIONS FROM DATABASE
    # =====================================================
    st.subheader("📢 Available Positions")
    
    if not positions_df.empty:
        st.info(f"✅ {len(positions_df)} position(s) currently available for application")
        
        position_options = ["Select a position..."]
        for _, row in positions_df.iterrows():
            deadline_info = f" (Deadline: {row['application_deadline']})" if row['application_deadline'] else ""
            position_options.append(f"{row['position_code']} - {row['position_title']}{deadline_info}")
        
        selected_display = st.selectbox("Choose a position to apply for", position_options)
        
        if selected_display != "Select a position...":
            selected_code = selected_display.split(" - ")[0]
            selected_position = next((p for p in advertised_positions_list if p['code'] == selected_code), None)
            
            if selected_position:
                with st.expander("📋 Position Details", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Position Title:** {selected_position['title']}")
                        st.write(f"**Position Code:** {selected_position['code']}")
                        st.write(f"**Department:** {selected_position['department']}")
                        st.write(f"**Employment Type:** {selected_position['employment_type']}")
                    with col2:
                        st.write(f"**Vacancies:** {selected_position['vacancies']}")
                        st.write(f"**Salary Range:** {selected_position['salary_range']}")
                        st.write(f"**Application Deadline:** {selected_position['deadline']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Requirements:**")
                    st.info(selected_position['requirements'] if selected_position['requirements'] else "Not specified")
                with col2:
                    st.markdown("**Responsibilities:**")
                    st.info(selected_position['responsibilities'] if selected_position['responsibilities'] else "Not specified")
    else:
        st.warning("⚠️ No open positions available at the moment. Please check back later.")
    
    st.markdown("---")
    
    # =====================================================
    # INITIALIZE SESSION STATE FOR DYNAMIC LISTS
    # =====================================================
    if 'academic_qualifications' not in st.session_state:
        st.session_state.academic_qualifications = []
    if 'professional_qualifications' not in st.session_state:
        st.session_state.professional_qualifications = []
    if 'other_courses' not in st.session_state:
        st.session_state.other_courses = []
    if 'professional_memberships' not in st.session_state:
        st.session_state.professional_memberships = []
    if 'work_experience' not in st.session_state:
        st.session_state.work_experience = []
    
    # =====================================================
    # APPLICATION FORM
    # =====================================================
    st.subheader("📝 Application Form")
    
    # WRAP EVERYTHING IN A FORM
    with st.form(key="application_form"):
        
        # Create tabs for better organization - 7 TABS
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📋 Position", 
            "👤 Personal Information", 
            "🏛️ Public Service", 
            "📚 Education", 
            "💼 Work Experience", 
            "👥 Referees", 
            "📎 Documents"
        ])
        
        # =========================================================
        # TAB 1: POSITION
        # =========================================================
        with tab1:
            st.markdown("### 📋 Position Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if selected_position:
                    position_applied = selected_position['title']
                    advertisement_ref = selected_position['code']
                    department = selected_position.get('department', '')
                    st.text_input("🎯 Position Applied For*", value=position_applied, disabled=True, help="Auto-filled from selected position")
                    st.text_input("📢 Advertisement Reference Number", value=advertisement_ref, disabled=True, help="Auto-filled from selected position")
                    st.text_input("🏢 Department", value=department, disabled=True, help="Auto-filled from selected position")
                elif found_position:
                    position_applied = found_position['title']
                    advertisement_ref = found_position['code']
                    department = found_position.get('department', '')
                    st.text_input("🎯 Position Applied For*", value=position_applied, disabled=True, help="Auto-filled from searched position")
                    st.text_input("📢 Advertisement Reference Number", value=advertisement_ref, disabled=True, help="Auto-filled from searched position")
                    st.text_input("🏢 Department", value=department, disabled=True, help="Auto-filled from searched position")
                else:
                    # Create position options from advertised_positions_list
                    pos_options = ["Select Position"] + [p['title'] for p in advertised_positions_list] if advertised_positions_list else ["Select Position"]
                    position_applied = st.selectbox("🎯 Position Applied For*", 
                        pos_options,
                        help="Select the position you wish to apply for")
                    
                    # Auto-fill department and reference if position selected
                    if position_applied != "Select Position":
                        for p in advertised_positions_list:
                            if p['title'] == position_applied:
                                advertisement_ref = p['code']
                                department = p.get('department', '')
                                break
                        st.text_input("🏢 Department", value=department, disabled=True)
                    else:
                        advertisement_ref = st.text_input("📢 Advertisement Reference Number", 
                                                          placeholder="e.g., CPSB/01/26(E)",
                                                          help="Reference number from the job advertisement")
                        department = st.text_input("🏢 Department", placeholder="e.g., Health, Education, Finance")
            
            with col2:
                application_date = st.date_input("📅 Application Date", value=datetime.now(), help="Date of application")
                source_of_info = st.selectbox("📺 How did you hear about this position?", [
                    "Select Source",
                    "Newspaper Advertisement",
                    "County Website",
                    "Social Media",
                    "Word of Mouth",
                    "Job Portal",
                    "Other"
                ], help="Where did you learn about this vacancy?")
            
            previously_applied = st.radio("Have you applied for any position with us before?", ["No", "Yes"], horizontal=True)
            if previously_applied == "Yes":
                previous_year = st.number_input("Which year did you previously apply?", min_value=2010, max_value=2025, step=1)
                st.info(f"Note: Previous application from {previous_year} will be considered")
        
        # =========================================================
        # TAB 2: PERSONAL INFORMATION
        # =========================================================
        with tab2:
            st.markdown("### 👤 Personal Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("👨‍🏫 Full Name (as per ID)*", placeholder="Enter your full name", help="Required field")
                gender = st.selectbox("⚧ Gender*", ["Male", "Female", "Other"], help="Required field")
                id_number = st.text_input("🆔 National ID Number*", placeholder="Enter ID number (e.g., 12345678)", help="Required field - Must be unique")
                yob = st.number_input("🎂 Year of Birth", step=1, min_value=1950, max_value=2026, help="Select year of birth")
                kra_pin = st.text_input("KRA PIN", placeholder="Enter KRA PIN (e.g., A123456789B)", help="Optional")
                ethnicity = st.selectbox("🌍 Ethnicity", ["Select Ethnicity", "Kikuyu", "Luo", "Luhya", "Kamba", "Kalenjin", "Meru", "Embu", "Mijikenda", "Turkana", "Maasai", "Kisii", "Taita", "Somali", "Other"])
                disability = st.selectbox("♿ Disability Status", ["None", "Physical", "Visual", "Hearing", "Speech", "Learning", "Other"], help="Select if you have any disability")
                nationality = st.selectbox("Nationality", ["Select", "Kenyan", "Other"])
                
            with col2:
                age = datetime.now().year - yob if yob else 0
                if age > 0:
                    if age < 18:
                        st.warning(f"⚠️ Age: {age} years - Below minimum recruitment age (18+)")
                    elif age > 55:
                        st.warning(f"⚠️ Age: {age} years - Check if within retirement requirements")
                    else:
                        st.success(f"✅ Age: {age} years")
                
                home_county = st.text_input("Home County", placeholder="Enter your home county")
                home_constituency = st.text_input("Home Constituency", placeholder="Enter your home constituency")
                subcounty = st.text_input("Sub County", placeholder="Enter your sub county")
                home_ward = st.text_input("Home Ward", placeholder="Enter your home ward")
                postal_address = st.text_input("Postal Address", placeholder="e.g., P.O. Box 123")
                postal_code = st.text_input("Postal Code", placeholder="e.g., 60100")
                town = st.text_input("Town/City", placeholder="Enter your town/city")
            
            st.markdown("---")
            st.markdown("#### 📞 Contact Information")
            
            col1, col2 = st.columns(2)
            with col1:
                contact = st.text_input("📱 Phone Number*", placeholder="07XXXXXXXX", help="Required - Format: 07XXXXXXXX")
                email = st.text_input("📧 Email Address*", placeholder="youremail@example.com", help="Required for official communication")
            
            with col2:
                alt_contact_name = st.text_input("Alternative Contact Person Name", placeholder="Full name of alternative contact")
                alt_contact_mobile = st.text_input("Alternative Contact Person Mobile Number", placeholder="07XXXXXXXX")
        
        # =========================================================
        # TAB 3: PUBLIC SERVICE
        # =========================================================
        with tab3:
            st.markdown("### 🏛️ Public Service Information")
            
            # Initialize public service variables with defaults
            public_institution_category = "N/A"
            public_institution = "N/A"
            station = "N/A"
            employment_number = "N/A"
            present_substantive_post = "N/A"
            date_of_current_appointment = None
            upgraded_post = "N/A"
            effective_date_previous_appointment = None
            secondment_organisation = "N/A"
            secondment_designation = "N/A"
            job_group = "N/A"
            terms_of_service = "N/A"
            
            col1, col2 = st.columns(2)
            
            with col1:
                in_public_service = st.radio("Are you currently in the Public Service?", ["No", "Yes"], horizontal=True)
                
                if in_public_service == "Yes":
                    public_institution_category = st.selectbox("Public Institution Category", [
                        "Select",
                        "National Government",
                        "County Government",
                        "State Corporation",
                        "Constitutional Commission",
                        "Other"
                    ])
                    public_institution = st.text_input("Public Institution", placeholder="Name of institution")
                    station = st.text_input("Station", placeholder="Your current station")
                    employment_number = st.text_input("Employment Number", placeholder="Your employment/payroll number")
            
            with col2:
                if in_public_service == "Yes":
                    present_substantive_post = st.text_input("Present Substantive Post (Full Designation)", placeholder="e.g., Senior Human Resource Officer")
                    date_of_current_appointment = st.date_input("Date of Current Appointment", value=None)
                    upgraded_post = st.text_input("Upgraded Post (if applicable)", placeholder="Enter upgraded post if applicable")
                    effective_date_previous_appointment = st.date_input("Effective Date of Previous Appointment", value=None)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if in_public_service == "Yes":
                    secondment_organisation = st.text_input("Secondment Organisation (if applicable)", placeholder="Name of organisation")
                    secondment_designation = st.text_input("Secondment Designation (if applicable)", placeholder="Your designation during secondment")
                    job_group = st.text_input("Job Group", placeholder="e.g., JG 'M'")
            
            with col2:
                if in_public_service == "Yes":
                    terms_of_service = st.selectbox("Terms of Service", [
                        "Select",
                        "Permanent",
                        "Contract",
                        "Temporary",
                        "Internship",
                        "Secondment"
                    ])
            
            st.markdown("---")
            st.markdown("#### ⚠️ Legal Declarations")
            
            col1, col2 = st.columns(2)
            with col1:
                convicted = st.radio("Have you ever been convicted of a criminal offence or subject of a probation order?", ["No", "Yes"], horizontal=True)
            with col2:
                dismissed = st.radio("Have you ever been dismissed or otherwise removed from employment?", ["No", "Yes"], horizontal=True)
            
            if convicted == "Yes":
                st.warning("⚠️ Please provide details in the remarks section at the end of the form.")
            if dismissed == "Yes":
                st.warning("⚠️ Please provide details in the remarks section at the end of the form.")
        
        # =========================================================
        # TAB 4: EDUCATION
        # =========================================================
        with tab4:
            st.markdown("### 📚 Education & Qualifications")
            
            # A. KCSE CERTIFICATE
            st.markdown("#### A. KCSE Certificate")
            col1, col2 = st.columns(2)
            with col1:
                secondary_school = st.text_input("Name of Secondary School", placeholder="Enter school name")
                index_number = st.text_input("Index Number", placeholder="e.g., 123456789")
            with col2:
                mean_grade = st.selectbox("Mean Grade", ["Select", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-"])
                certificate_no = st.text_input("Certificate No.", placeholder="Enter certificate number")
                year_completed = st.number_input("Year of Completion", min_value=1980, max_value=2026, step=1)
            
            st.markdown("---")
            
            # B. HIGHEST ACADEMIC QUALIFICATION
            st.markdown("#### B. Highest Academic Qualification")
            st.info("📌 You can add multiple academic qualifications. Use the buttons below the form to add/remove.")
            
            # Display existing academic qualifications (read-only in form)
            for idx, qual in enumerate(st.session_state.academic_qualifications):
                with st.expander(f"📜 Qualification #{idx + 1}: {qual.get('level', 'New')}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input(f"Qualification Level", 
                            value=qual.get('level', 'Select'), disabled=True, key=f"acad_display_level_{idx}")
                        st.text_input(f"Institution", 
                            value=qual.get('institution', ''), disabled=True, key=f"acad_display_inst_{idx}")
                    with col2:
                        st.number_input(f"Year of Graduation", 
                            value=qual.get('year', 2020), disabled=True, key=f"acad_display_year_{idx}")
                        st.text_input(f"Certificate No.", 
                            value=qual.get('cert_no', ''), disabled=True, key=f"acad_display_cert_{idx}")
            
            st.markdown("---")
            
            # C. PROFESSIONAL QUALIFICATIONS (read-only in form)
            st.markdown("#### C. Professional Qualifications")
            st.info("📌 Add your professional certifications. Use the buttons below the form to add/remove.")
            
            for idx, qual in enumerate(st.session_state.professional_qualifications):
                with st.expander(f"📜 Professional Cert #{idx + 1}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input(f"Institution", value=qual.get('institution', ''), disabled=True, key=f"prof_display_inst_{idx}")
                        st.text_input(f"Certificate Name", value=qual.get('name', ''), disabled=True, key=f"prof_display_name_{idx}")
                    with col2:
                        st.number_input(f"Year of Completion", value=qual.get('year', 2020), disabled=True, key=f"prof_display_year_{idx}")
                        st.text_input(f"Certificate No.", value=qual.get('cert_no', ''), disabled=True, key=f"prof_display_cert_{idx}")
            
            st.markdown("---")
            
            # D. OTHER RELEVANT COURSES (read-only in form)
            st.markdown("#### D. Other Relevant Courses")
            st.info("📌 Use the buttons below the form to add/remove courses.")
            
            for idx, course in enumerate(st.session_state.other_courses):
                with st.expander(f"📚 Course #{idx + 1}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input(f"Institution", value=course.get('institution', ''), disabled=True, key=f"other_display_inst_{idx}")
                        st.text_input(f"Course Name", value=course.get('name', ''), disabled=True, key=f"other_display_name_{idx}")
                    with col2:
                        st.number_input(f"Year of Completion", value=course.get('year', 2020), disabled=True, key=f"other_display_year_{idx}")
                        st.text_input(f"Certificate No.", value=course.get('cert_no', ''), disabled=True, key=f"other_display_cert_{idx}")
            
            st.markdown("---")
            
            # E. MEMBERSHIP TO PROFESSIONAL BODIES (read-only in form)
            st.markdown("#### E. Membership to Professional Bodies")
            st.info("📌 Use the buttons below the form to add/remove memberships.")
            
            for idx, member in enumerate(st.session_state.professional_memberships):
                with st.expander(f"🏛️ Membership #{idx + 1}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input(f"Professional Body", value=member.get('body', ''), disabled=True, key=f"member_display_body_{idx}")
                        st.text_input(f"Membership Type", value=member.get('membership_type', 'Select'), disabled=True, key=f"member_display_type_{idx}")
                    with col2:
                        st.text_input(f"Registration Number", value=member.get('reg_no', ''), disabled=True, key=f"member_display_reg_{idx}")
                        st.text_input(f"Date Renewed", value=str(member.get('date_renewed', '')), disabled=True, key=f"member_display_renewed_{idx}")
                        st.text_input(f"Expiry Date", value=str(member.get('expiry_date', '')), disabled=True, key=f"member_display_expiry_{idx}")
        
        # =========================================================
        # TAB 5: WORK EXPERIENCE
        # =========================================================
        with tab5:
            st.markdown("### 💼 Work Experience")
            st.info("📌 Add your work experience. Use the buttons below the form to add/remove.")
            
            for idx, exp in enumerate(st.session_state.work_experience):
                with st.expander(f"💼 Position #{idx + 1}: {exp.get('position', 'New Position')}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input(f"Position Held", value=exp.get('position', ''), disabled=True, key=f"work_display_pos_{idx}")
                        st.text_input(f"Organization", value=exp.get('organization', ''), disabled=True, key=f"work_display_org_{idx}")
                        st.text_area(f"Nature of Work/Duties", value=exp.get('duties', ''), disabled=True, height=80, key=f"work_display_duties_{idx}")
                    with col2:
                        st.text_input(f"Job Scale/Grade", value=exp.get('job_scale', ''), disabled=True, key=f"work_display_scale_{idx}")
                        st.number_input(f"Gross Monthly Salary (Kshs.)", value=exp.get('salary', 0), disabled=True, key=f"work_display_salary_{idx}")
                        st.text_input(f"Start Date", value=str(exp.get('start_date', '')), disabled=True, key=f"work_display_start_{idx}")
                        st.text_input(f"End Date", value=str(exp.get('end_date', '')), disabled=True, key=f"work_display_end_{idx}")
        
        # =========================================================
        # TAB 6: REFEREES
        # =========================================================
        with tab6:
            st.markdown("### 👥 Referees")
            st.info("Please provide three professional referees who can vouch for your work")
            
            # Referee 1
            st.markdown("#### 📌 Referee 1")
            col1, col2 = st.columns(2)
            with col1:
                referee1_name = st.text_input("Full Names", placeholder="Full name", key="ref1_name_full")
                referee1_occupation = st.text_input("Occupation", placeholder="e.g., HR Manager", key="ref1_occ")
                referee1_postal_address = st.text_input("Postal Address", placeholder="e.g., P.O. Box 123", key="ref1_postal")
            with col2:
                referee1_post_code = st.text_input("Post Code", placeholder="e.g., 60100", key="ref1_code")
                referee1_city = st.text_input("Postal City/Town", placeholder="e.g., Nairobi", key="ref1_city")
                referee1_mobile = st.text_input("Mobile Number", placeholder="07XXXXXXXX", key="ref1_mobile")
                referee1_email = st.text_input("E-Mail Address", placeholder="email@example.com", key="ref1_email")
                referee1_period = st.text_input("Period known (e.g., 5 years)", placeholder="e.g., 5 years", key="ref1_period")
            
            st.markdown("---")
            
            # Referee 2
            st.markdown("#### 📌 Referee 2")
            col1, col2 = st.columns(2)
            with col1:
                referee2_name = st.text_input("Full Names", placeholder="Full name", key="ref2_name_full")
                referee2_occupation = st.text_input("Occupation", placeholder="e.g., HR Manager", key="ref2_occ")
                referee2_postal_address = st.text_input("Postal Address", placeholder="e.g., P.O. Box 123", key="ref2_postal")
            with col2:
                referee2_post_code = st.text_input("Post Code", placeholder="e.g., 60100", key="ref2_code")
                referee2_city = st.text_input("Postal City/Town", placeholder="e.g., Nairobi", key="ref2_city")
                referee2_mobile = st.text_input("Mobile Number", placeholder="07XXXXXXXX", key="ref2_mobile")
                referee2_email = st.text_input("E-Mail Address", placeholder="email@example.com", key="ref2_email")
                referee2_period = st.text_input("Period known (e.g., 5 years)", placeholder="e.g., 5 years", key="ref2_period")
            
            st.markdown("---")
            
            # Referee 3
            st.markdown("#### 📌 Referee 3")
            col1, col2 = st.columns(2)
            with col1:
                referee3_name = st.text_input("Full Names", placeholder="Full name", key="ref3_name_full")
                referee3_occupation = st.text_input("Occupation", placeholder="e.g., HR Manager", key="ref3_occ")
                referee3_postal_address = st.text_input("Postal Address", placeholder="e.g., P.O. Box 123", key="ref3_postal")
            with col2:
                referee3_post_code = st.text_input("Post Code", placeholder="e.g., 60100", key="ref3_code")
                referee3_city = st.text_input("Postal City/Town", placeholder="e.g., Nairobi", key="ref3_city")
                referee3_mobile = st.text_input("Mobile Number", placeholder="07XXXXXXXX", key="ref3_mobile")
                referee3_email = st.text_input("E-Mail Address", placeholder="email@example.com", key="ref3_email")
                referee3_period = st.text_input("Period known (e.g., 5 years)", placeholder="e.g., 5 years", key="ref3_period")
        
        # =========================================================
        # TAB 7: DOCUMENTS
        # =========================================================
        with tab7:
            st.markdown("### 📎 Document Upload")
            st.warning("⚠️ **Important Notice:** Only upload scanned copies of **certificates** as indicated. No CVs and other testimonials will be accepted.")
            
            st.info("📌 Please ensure all documents are clear and legible. Accepted formats: PDF, JPG, PNG (Max size: 5MB per file)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📄 Personal Documents")
                national_id = st.file_uploader("National ID Card/Passport*", type=["pdf", "jpg", "jpeg", "png"], key="doc_id")
                birth_cert = st.file_uploader("Birth Certificate", type=["pdf", "jpg", "jpeg", "png"], key="doc_birth")
                passport_photo = st.file_uploader("Passport Size Photo", type=["jpg", "jpeg", "png"], key="doc_photo")
                
                st.markdown("#### 🎓 KCSE Certificate")
                kcse_cert = st.file_uploader("KCSE Certificate", type=["pdf", "jpg", "jpeg", "png"], key="doc_kcse")
            
            with col2:
                st.markdown("#### 🎓 Academic Certificates")
                degree_cert = st.file_uploader("Degree/Diploma/Certificate Certificates", type=["pdf", "jpg", "jpeg", "png"], key="doc_degree", help="Upload all academic certificates")
                
                st.markdown("#### 📜 Professional Certificates")
                prof_cert = st.file_uploader("Professional Certificates", type=["pdf", "jpg", "jpeg", "png"], key="doc_prof", help="Upload all professional certifications")
                
                st.markdown("#### 📋 Other Certificates")
                other_docs = st.file_uploader("Other Certificates", type=["pdf", "jpg", "jpeg", "png"], key="doc_other", help="Upload any other relevant certificates", accept_multiple_files=True)
            
            st.markdown("---")
            st.markdown("#### ✅ Document Checklist")
            
            col1, col2 = st.columns(2)
            with col1:
                doc_id_check = st.checkbox("✅ National ID Card/Passport", value=True)
                doc_kcse_check = st.checkbox("✅ KCSE Certificate")
                doc_degree_check = st.checkbox("✅ Academic Certificates (Degree/Diploma)")
            
            with col2:
                doc_prof_check = st.checkbox("✅ Professional Certificates")
                doc_photo_check = st.checkbox("✅ Passport Size Photo")
                doc_other_check = st.checkbox("✅ Other Relevant Certificates")
            
            st.caption("📌 Please ensure all required documents are uploaded before submitting your application.")
        
        # =========================================================
        # DECLARATION & REMARKS
        # =========================================================
        st.markdown("---")
        st.markdown("### ✍️ Declaration")
        
        declaration = st.checkbox("I declare that all information provided is true and accurate to the best of my knowledge. I understand that any false information may lead to disqualification.")
        
        remarks = st.text_area("Additional Remarks / Explanations", 
                              placeholder="Any additional information or explanations regarding your application...",
                              height=100)
        
        # Required fields note
        st.markdown("---")
        st.markdown("""
        <div style="background: #f8f9fa; padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;">
            <small>⚠️ <strong>Note:</strong> Fields marked with <span style="color: red;">*</span> are required</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Submit button inside the form
        submitted = st.form_submit_button("📤 Submit Application", use_container_width=True, type="primary")
        
        # =========================================================
        # PROCESS SUBMISSION
        # =========================================================
        if submitted:
            # Validation
            errors = []
            if not position_applied or position_applied == "Select Position":
                errors.append("Please select the position you are applying for")
            if not name:
                errors.append("Full Name is required")
            if not id_number:
                errors.append("ID Number is required")
            if not contact:
                errors.append("Phone Number is required")
            if not declaration:
                errors.append("Please accept the declaration to submit your application")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                conn = get_conn()
                c = conn.cursor()
                
                try:
                    # Build qualification summary
                    qual_summary = f"KCSE: {mean_grade if mean_grade != 'Select' else 'N/A'} ({year_completed})"
                    if st.session_state.academic_qualifications:
                        acad = st.session_state.academic_qualifications[0]
                        if acad.get('level') and acad.get('institution'):
                            qual_summary += f" | {acad['level']}: {acad['institution']} ({acad.get('year', '')})"
                    
                    # Build comprehensive remarks
                    full_remarks = f"""
                    === APPLICATION DETAILS ===
                    Position: {position_applied}
                    Advert Ref: {advertisement_ref}
                    Department: {department}
                    Source: {source_of_info}
                    Application Date: {application_date}
                    
                    === PERSONAL INFORMATION ===
                    Name: {name}
                    Gender: {gender}
                    ID Number: {id_number}
                    Year of Birth: {yob}
                    KRA PIN: {kra_pin}
                    Nationality: {nationality}
                    Home County: {home_county}
                    Home Constituency: {home_constituency}
                    Sub County: {subcounty}
                    Home Ward: {home_ward}
                    Postal Address: {postal_address}
                    Postal Code: {postal_code}
                    Town: {town}
                    Phone: {contact}
                    Email: {email}
                    
                    === PUBLIC SERVICE ===
                    In Public Service: {in_public_service}
                    Institution Category: {public_institution_category if in_public_service == "Yes" else "N/A"}
                    Institution: {public_institution if in_public_service == "Yes" else "N/A"}
                    Station: {station if in_public_service == "Yes" else "N/A"}
                    Employment No: {employment_number if in_public_service == "Yes" else "N/A"}
                    Present Post: {present_substantive_post if in_public_service == "Yes" else "N/A"}
                    Current Appointment: {date_of_current_appointment if in_public_service == "Yes" else "N/A"}
                    Upgraded Post: {upgraded_post if in_public_service == "Yes" else "N/A"}
                    Previous Appointment: {effective_date_previous_appointment if in_public_service == "Yes" else "N/A"}
                    Secondment Org: {secondment_organisation if in_public_service == "Yes" else "N/A"}
                    Secondment Designation: {secondment_designation if in_public_service == "Yes" else "N/A"}
                    Job Group: {job_group if in_public_service == "Yes" else "N/A"}
                    Terms of Service: {terms_of_service if in_public_service == "Yes" else "N/A"}
                    Convicted: {convicted}
                    Dismissed: {dismissed}
                    
                    === EDUCATION ===
                    KCSE School: {secondary_school}
                    KCSE Index: {index_number}
                    KCSE Grade: {mean_grade}
                    KCSE Cert No: {certificate_no}
                    KCSE Year: {year_completed}
                    
                    === QUALIFICATIONS ===
                    Academic Qualifications: {len(st.session_state.academic_qualifications)} records
                    Professional Qualifications: {len(st.session_state.professional_qualifications)} records
                    Other Courses: {len(st.session_state.other_courses)} records
                    Professional Memberships: {len(st.session_state.professional_memberships)} records
                    
                    === WORK EXPERIENCE ===
                    Number of Positions: {len(st.session_state.work_experience)} records
                    
                    === REFEREES ===
                    Referee 1: {referee1_name} - {referee1_occupation}
                    Referee 2: {referee2_name} - {referee2_occupation}
                    Referee 3: {referee3_name} - {referee3_occupation}
                    
                    === ADDITIONAL ===
                    {remarks}
                    """
                    
                    # Use dictionary approach to avoid column count errors
                    data = {
                        'sno': 0,
                        'name': name,
                        'gender': gender,
                        'id_number': id_number,
                        'yob': yob if yob else 0,
                        'ethnicity': ethnicity if ethnicity and ethnicity != "Select Ethnicity" else "",
                        'disability': disability if disability and disability != "None" else "",
                        'contact': contact,
                        'kcse_grade': year_completed if year_completed else 0,
                        'qualifications': qual_summary,
                        'subcounty': subcounty if subcounty else "",
                        'ward': home_ward if home_ward else "",
                        'experience': f"{len(st.session_state.work_experience)} positions",
                        'remarks': full_remarks,
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'created_by': st.session_state.user["username"] if st.session_state.user else "applicant",
                        'position_applied': position_applied,
                        'advertisement_ref': advertisement_ref,
                        'email': email if email else "",
                        'experience_years': 0,
                        'current_employer': "",
                        'referee1_name': referee1_name if referee1_name else "",
                        'referee1_contact': referee1_mobile if referee1_mobile else "",
                        'referee2_name': referee2_name if referee2_name else "",
                        'referee2_contact': referee2_mobile if referee2_mobile else ""
                    }
                    
                    # Build the INSERT statement dynamically
                    columns = ', '.join(data.keys())
                    placeholders = ', '.join(['?'] * len(data))
                    query = f"INSERT INTO staff ({columns}) VALUES ({placeholders})"
                    
                    # Execute
                    c.execute(query, tuple(data.values()))
                    
                    conn.commit()
                    
                    st.balloons()
                    st.success(f"""
                    ✅ **Application Successfully Submitted!**
                    
                    **Application Summary:**
                    - Name: {name}
                    - Position: {position_applied}
                    - Advert Ref: {advertisement_ref}
                    - ID Number: {id_number}
                    - Application Date: {application_date}
                    
                    **Next Steps:**
                    1. You will receive a confirmation SMS/Email
                    2. Shortlisted candidates will be contacted for interview
                    3. Keep your phone accessible for communication
                    
                    Thank you for applying to Embu County Public Service Board!
                    """)
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error submitting application: {str(e)}")
                finally:
                    conn.close()
    
    # =====================================================
    # BUTTONS OUTSIDE THE FORM (For adding/removing items)
    # =====================================================
    st.markdown("---")
    st.subheader("📋 Manage Your Lists")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("➕ Add Academic Qualification", use_container_width=True):
            st.session_state.academic_qualifications.append({
                'level': 'Select',
                'institution': '',
                'year': 2020,
                'cert_no': ''
            })
            st.rerun()
    
    with col2:
        if st.button("➕ Add Professional Cert", use_container_width=True):
            st.session_state.professional_qualifications.append({
                'institution': '',
                'name': '',
                'year': 2020,
                'cert_no': ''
            })
            st.rerun()
    
    with col3:
        if st.button("➕ Add Other Course", use_container_width=True):
            st.session_state.other_courses.append({
                'institution': '',
                'name': '',
                'year': 2020,
                'cert_no': ''
            })
            st.rerun()
    
    with col4:
        if st.button("➕ Add Membership", use_container_width=True):
            st.session_state.professional_memberships.append({
                'body': '',
                'membership_type': 'Select',
                'reg_no': '',
                'date_renewed': None,
                'expiry_date': None
            })
            st.rerun()
    
    with col5:
        if st.button("➕ Add Work Experience", use_container_width=True):
            st.session_state.work_experience.append({
                'position': '',
                'organization': '',
                'duties': '',
                'job_scale': '',
                'salary': 0,
                'start_date': None,
                'end_date': None
            })
            st.rerun()
    
    # Display remove buttons for each list
    if st.session_state.academic_qualifications:
        st.markdown("#### Remove Academic Qualifications")
        cols = st.columns(min(len(st.session_state.academic_qualifications), 4))
        for idx, qual in enumerate(st.session_state.academic_qualifications):
            col_idx = idx % len(cols)
            with cols[col_idx]:
                if st.button(f"🗑️ Remove #{idx+1}", key=f"remove_acad_{idx}"):
                    st.session_state.academic_qualifications.pop(idx)
                    st.rerun()
    
    if st.session_state.professional_qualifications:
        st.markdown("#### Remove Professional Certifications")
        cols = st.columns(min(len(st.session_state.professional_qualifications), 4))
        for idx, qual in enumerate(st.session_state.professional_qualifications):
            col_idx = idx % len(cols)
            with cols[col_idx]:
                if st.button(f"🗑️ Remove #{idx+1}", key=f"remove_prof_{idx}"):
                    st.session_state.professional_qualifications.pop(idx)
                    st.rerun()
    
    if st.session_state.other_courses:
        st.markdown("#### Remove Other Courses")
        cols = st.columns(min(len(st.session_state.other_courses), 4))
        for idx, course in enumerate(st.session_state.other_courses):
            col_idx = idx % len(cols)
            with cols[col_idx]:
                if st.button(f"🗑️ Remove #{idx+1}", key=f"remove_other_{idx}"):
                    st.session_state.other_courses.pop(idx)
                    st.rerun()
    
    if st.session_state.professional_memberships:
        st.markdown("#### Remove Memberships")
        cols = st.columns(min(len(st.session_state.professional_memberships), 4))
        for idx, member in enumerate(st.session_state.professional_memberships):
            col_idx = idx % len(cols)
            with cols[col_idx]:
                if st.button(f"🗑️ Remove #{idx+1}", key=f"remove_member_{idx}"):
                    st.session_state.professional_memberships.pop(idx)
                    st.rerun()
    
    if st.session_state.work_experience:
        st.markdown("#### Remove Work Experience")
        cols = st.columns(min(len(st.session_state.work_experience), 4))
        for idx, exp in enumerate(st.session_state.work_experience):
            col_idx = idx % len(cols)
            with cols[col_idx]:
                if st.button(f"🗑️ Remove #{idx+1}", key=f"remove_work_{idx}"):
                    st.session_state.work_experience.pop(idx)
                    st.rerun()
    
    # Clear all button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("🗑️ Clear All Lists", use_container_width=True, type="secondary"):
            st.session_state.academic_qualifications = []
            st.session_state.professional_qualifications = []
            st.session_state.other_courses = []
            st.session_state.professional_memberships = []
            st.session_state.work_experience = []
            st.rerun()

# =====================================================
# END OF data_entry() FUNCTION
# =====================================================
# =========================================================
# STAFF RECORDS
# =========================================================
def records():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">Applicants Records</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">View, search and manage applicant data</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Get advertised positions for filter
    try:
        if is_cloud:
            positions_df = pd.read_sql("""
                SELECT id, position_title, position_code, status 
                FROM advertised_positions 
                ORDER BY id DESC
            """, conn)
        else:
            positions_df = pd.read_sql("""
                SELECT id, position_title, position_code, status 
                FROM advertised_positions 
                ORDER BY id DESC
            """, conn)
    except:
        positions_df = pd.DataFrame()
    
    # Get all staff data
    df = pd.read_sql("SELECT * FROM staff ORDER BY id DESC", conn)
    conn.close()
    
    if df.empty:
        st.warning("No records found. Please add records using Staff Entry or Import Excel.")
        return
    
    # Initialize session state for search
    if 'advanced_search_triggered' not in st.session_state:
        st.session_state.advanced_search_triggered = False
    if 'quick_search_triggered' not in st.session_state:
        st.session_state.quick_search_triggered = False
    if 'advanced_results' not in st.session_state:
        st.session_state.advanced_results = None
    if 'quick_results' not in st.session_state:
        st.session_state.quick_results = None
    if 'status_filter' not in st.session_state:
        st.session_state.status_filter = "All Applicants"
    if 'advert_status_filter' not in st.session_state:
        st.session_state.advert_status_filter = "All"
    if 'quick_status_filter' not in st.session_state:
        st.session_state.quick_status_filter = "All Applicants"
    if 'quick_advert_status' not in st.session_state:
        st.session_state.quick_advert_status = "All"
    
    # Create two tabs: Advanced Search and Quick Search
    tab1, tab2 = st.tabs(["🔍 Advanced Search", "🔎 Quick Search"])
    
    # ==================== TAB 1: ADVANCED SEARCH ====================
    with tab1:
        st.markdown("### 📋 Advanced Search Filters")
        st.info("Select your search criteria below, then click the SEARCH button to find records.")
        
        # Create filter columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Position filter with status selection
            st.markdown("**Advertised Position Status**")
            advert_status_options = ["All", "Open", "Closed", "On Hold"]
            
            # Get current index for the radio button
            current_index = 0
            if st.session_state.advert_status_filter == "Open":
                current_index = 1
            elif st.session_state.advert_status_filter == "Closed":
                current_index = 2
            elif st.session_state.advert_status_filter == "On Hold":
                current_index = 3
            
            selected_advert_status = st.radio(
                "Select Position Status",
                advert_status_options,
                index=current_index,
                key="adv_advert_status",
                horizontal=True
            )
            
            # Check if status changed - if yes, reset search results
            if selected_advert_status != st.session_state.advert_status_filter:
                st.session_state.advert_status_filter = selected_advert_status
                st.session_state.advanced_search_triggered = False
                st.session_state.advanced_results = None
                st.session_state.status_filter = "All Applicants"
                st.rerun()
            
            # Filter positions based on status
            if selected_advert_status != "All":
                filtered_positions_df = positions_df[positions_df['status'] == selected_advert_status]
            else:
                filtered_positions_df = positions_df
            
            if not filtered_positions_df.empty:
                position_options = ["All Positions"] + [f"{row['position_title']} ({row['position_code']})" for _, row in filtered_positions_df.iterrows()]
                selected_position = st.selectbox("Filter by Position", position_options, key="adv_position_filter")
                # Store the selected position title for filtering
                if selected_position != "All Positions":
                    selected_position_title = selected_position.split(" (")[0]
                else:
                    selected_position_title = None
            else:
                selected_position = "All Positions"
                selected_position_title = None
                st.info(f"No {selected_advert_status} positions found")
            
            # Subcounty filter
            subcounty_options = ["All Sub-Counties"] + sorted(df['subcounty'].dropna().unique().tolist()) if 'subcounty' in df.columns else ["All Sub-Counties"]
            selected_subcounty = st.selectbox("Filter by Sub-County", subcounty_options, key="adv_subcounty_filter")
            
            # Gender filter
            gender_options = ["All Genders", "Male", "Female", "Other"]
            selected_gender = st.selectbox("Filter by Gender", gender_options, key="adv_gender_filter")
        
        with col2:
            # Ward filter
            ward_options = ["All Wards"] + sorted(df['ward'].dropna().unique().tolist()) if 'ward' in df.columns else ["All Wards"]
            selected_ward = st.selectbox("Filter by Ward", ward_options, key="adv_ward_filter")
            
            # Application Status filter (for the search itself, not the post-search filter)
            st.markdown("**Application Status (Search Filter)**")
            status_options = ["All Status"] + sorted(df['application_status'].dropna().unique().tolist()) if 'application_status' in df.columns else ["All Status"]
            selected_status = st.selectbox("Filter by Application Status", status_options, key="adv_status_filter")
            
            # Disability filter
            disability_options = ["All", "With Disability", "Without Disability"]
            selected_disability = st.selectbox("Filter by Disability", disability_options, key="adv_disability_filter")
        
        with col3:
            # Ethnicity filter
            ethnicity_options = ["All Ethnicities"] + sorted(df['ethnicity'].dropna().unique().tolist()) if 'ethnicity' in df.columns else ["All Ethnicities"]
            selected_ethnicity = st.selectbox("Filter by Ethnicity", ethnicity_options, key="adv_ethnicity_filter")
            
            # Qualification filter
            search_qualification = st.text_input("Search by Qualification", placeholder="Enter qualification...", key="adv_qualification_filter")
            
            # Age range filter
            if 'yob' in df.columns and not df['yob'].isna().all():
                current_year = datetime.now().year
                df['age_calc'] = current_year - df['yob']
                min_age = int(df['age_calc'].min()) if not df['age_calc'].isna().all() else 18
                max_age = int(df['age_calc'].max()) if not df['age_calc'].isna().all() else 100
                age_range = st.slider("Age Range", min_age, max_age, (min_age, max_age), key="adv_age_filter")
            else:
                age_range = (18, 100)
                st.slider("Age Range", 18, 100, (18, 100), key="adv_age_filter_dummy")
        
        # Search and Clear buttons
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            search_clicked = st.button("🔍 SEARCH RECORDS", use_container_width=True, type="primary", key="advanced_search_btn")
        
        with col1:
            if st.button("🗑️ Clear All", use_container_width=True, key="clear_advanced_btn"):
                st.session_state.advanced_search_triggered = False
                st.session_state.advanced_results = None
                st.session_state.status_filter = "All Applicants"
                st.session_state.advert_status_filter = "All"
                st.rerun()
        
        # Perform search when button is clicked
        if search_clicked:
            filtered_df = df.copy()
            
            # Filter by position status first
            # Get all position titles that match the selected status
            if selected_advert_status != "All":
                # Get position titles for the selected status
                valid_positions = positions_df[positions_df['status'] == selected_advert_status]['position_title'].tolist()
                if valid_positions:
                    filtered_df = filtered_df[filtered_df['position_applied'].isin(valid_positions)]
                else:
                    filtered_df = pd.DataFrame()  # No valid positions, return empty
            
            # Apply specific Position filter (if a specific position was selected)
            if selected_position_title is not None and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['position_applied'] == selected_position_title]
            
            # Apply Subcounty filter
            if selected_subcounty != "All Sub-Counties" and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['subcounty'] == selected_subcounty]
            
            # Apply Gender filter
            if selected_gender != "All Genders" and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['gender'] == selected_gender]
            
            # Apply Ward filter
            if selected_ward != "All Wards" and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['ward'] == selected_ward]
            
            # Apply Status filter
            if selected_status != "All Status" and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['application_status'] == selected_status]
            
            # Apply Disability filter
            if selected_disability == "With Disability" and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['disability'].notna() & (filtered_df['disability'] != '') & (filtered_df['disability'] != 'None') & (filtered_df['disability'].str.lower() != 'none')]
            elif selected_disability == "Without Disability" and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['disability'].isna() | (filtered_df['disability'] == '') | (filtered_df['disability'] == 'None') | (filtered_df['disability'].str.lower() == 'none')]
            
            # Apply Ethnicity filter
            if selected_ethnicity != "All Ethnicities" and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['ethnicity'] == selected_ethnicity]
            
            # Apply Qualification filter
            if search_qualification and not filtered_df.empty:
                filtered_df = filtered_df[filtered_df['qualifications'].str.contains(search_qualification, case=False, na=False)]
            
            # Apply Age filter
            if 'age_calc' in filtered_df.columns and not filtered_df.empty:
                filtered_df = filtered_df[(filtered_df['age_calc'] >= age_range[0]) & (filtered_df['age_calc'] <= age_range[1])]
            
            # Store results
            st.session_state.advanced_results = filtered_df
            st.session_state.advanced_search_triggered = True
            st.session_state.status_filter = "All Applicants"  # Reset post-search filter
        
        # Display results if search was performed
        if st.session_state.advanced_search_triggered:
            if st.session_state.advanced_results is not None and not st.session_state.advanced_results.empty:
                results_df = st.session_state.advanced_results
                
                # Show active filters summary
                st.markdown("---")
                st.markdown("### 📊 Filter Results by Application Status")
                
                # Show active advert status filter
                if st.session_state.advert_status_filter != "All":
                    st.info(f"📌 Position Status Filter: **{st.session_state.advert_status_filter}** | Records found: {len(results_df)}")
                
                # Create status filter buttons (POST-SEARCH filter)
                col1, col2, col3, col4 = st.columns(4)
                
                # Calculate counts for each status from current results
                total_count = len(results_df)
                shortlisted_count = len(results_df[results_df['application_status'] == 'Shortlisted']) if 'application_status' in results_df.columns else 0
                interviewed_count = len(results_df[results_df['interview_score'].notna() & (results_df['interview_score'] > 0)]) if 'interview_score' in results_df.columns else 0
                successful_count = len(results_df[results_df['application_status'] == 'Recommended']) if 'application_status' in results_df.columns else 0
                
                with col1:
                    if st.button(f"📊 All Applicants ({total_count})", use_container_width=True, key="status_all_btn"):
                        st.session_state.status_filter = "All Applicants"
                        st.rerun()
                
                with col2:
                    if st.button(f"⭐ Shortlisted ({shortlisted_count})", use_container_width=True, key="status_shortlisted_btn"):
                        st.session_state.status_filter = "Shortlisted"
                        st.rerun()
                
                with col3:
                    if st.button(f"🎤 Interviewed ({interviewed_count})", use_container_width=True, key="status_interviewed_btn"):
                        st.session_state.status_filter = "Interviewed"
                        st.rerun()
                
                with col4:
                    if st.button(f"🏆 Successful ({successful_count})", use_container_width=True, key="status_successful_btn"):
                        st.session_state.status_filter = "Successful"
                        st.rerun()
                
                # Apply the post-search status filter
                display_df = results_df.copy()
                if st.session_state.status_filter == "Shortlisted":
                    display_df = display_df[display_df['application_status'] == 'Shortlisted']
                elif st.session_state.status_filter == "Interviewed":
                    display_df = display_df[display_df['interview_score'].notna() & (display_df['interview_score'] > 0)]
                elif st.session_state.status_filter == "Successful":
                    display_df = display_df[display_df['application_status'] == 'Recommended']
                
                st.info(f"📌 Currently viewing: **{st.session_state.status_filter}** ({len(display_df)} records)")
                
                # Remove temporary age column if exists
                if 'age_calc' in display_df.columns:
                    display_df = display_df.drop(columns=['age_calc'])
                
                st.markdown("---")
                st.success(f"✅ Found {len(display_df)} record(s)")
                
                # Pagination
                page_size = st.selectbox("Records per page", [10, 25, 50, 100, 200], key="adv_page_size")
                if page_size > 0 and len(display_df) > 0:
                    total_pages = (len(display_df) + page_size - 1) // page_size
                    page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="adv_page_number")
                    
                    start_idx = (page_number - 1) * page_size
                    end_idx = start_idx + page_size
                    page_df = display_df.iloc[start_idx:end_idx]
                    
                    st.dataframe(page_df, use_container_width=True, height=400)
                    st.caption(f"Page {page_number} of {total_pages}")
                else:
                    st.dataframe(display_df, use_container_width=True, height=400)
                
                # Export buttons
                col1, col2 = st.columns(2)
                with col1:
                    csv = display_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Current View (CSV)",
                        csv,
                        f"staff_records_{st.session_state.status_filter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    try:
                        from io import BytesIO
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            display_df.to_excel(writer, sheet_name=f'Staff Records - {st.session_state.status_filter}', index=False)
                        st.download_button(
                            "📥 Download Current View (Excel)",
                            output.getvalue(),
                            f"staff_records_{st.session_state.status_filter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except:
                        pass
            else:
                st.warning("No records match your search criteria. Try adjusting the filters.")
        else:
            st.info("👆 Select your search criteria above and click SEARCH RECORDS to find staff records.")
    
    # ==================== TAB 2: QUICK SEARCH ====================
    with tab2:
        st.markdown("### 🔎 Quick Search by Name or ID Number")
        st.info("Enter a name or ID number below, then click the SEARCH button.")
        
        # Add advert status filter for quick search
        st.markdown("**Advertised Position Status**")
        q_advert_status_options = ["All", "Open", "Closed", "On Hold"]
        
        # Get current index for quick search radio
        q_current_index = 0
        if st.session_state.quick_advert_status == "Open":
            q_current_index = 1
        elif st.session_state.quick_advert_status == "Closed":
            q_current_index = 2
        elif st.session_state.quick_advert_status == "On Hold":
            q_current_index = 3
        
        q_selected_advert_status = st.radio(
            "Select Position Status",
            q_advert_status_options,
            index=q_current_index,
            key="quick_advert_status_radio",
            horizontal=True
        )
        
        # Check if status changed
        if q_selected_advert_status != st.session_state.quick_advert_status:
            st.session_state.quick_advert_status = q_selected_advert_status
            st.session_state.quick_search_triggered = False
            st.session_state.quick_results = None
            st.rerun()
        
        # Filter positions based on status
        if q_selected_advert_status != "All":
            q_filtered_positions = positions_df[positions_df['status'] == q_selected_advert_status]
            q_position_titles = q_filtered_positions['position_title'].tolist() if not q_filtered_positions.empty else []
        else:
            q_position_titles = positions_df['position_title'].tolist() if not positions_df.empty else []
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search by Name or ID Number", placeholder="Type name or ID number...", key="quick_search_input")
        with col2:
            quick_search_clicked = st.button("🔍 SEARCH", use_container_width=True, key="quick_search_btn")
        
        # Clear button for quick search
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("🗑️ Clear", use_container_width=True, key="clear_quick_btn"):
                st.session_state.quick_search_triggered = False
                st.session_state.quick_results = None
                st.session_state.quick_status_filter = "All Applicants"
                st.session_state.quick_advert_status = "All"
                st.rerun()
        
        # Perform quick search when button is clicked
        if quick_search_clicked and search_term:
            quick_results = df[
                df['name'].str.contains(search_term, case=False, na=False) |
                df['id_number'].str.contains(search_term, na=False)
            ]
            
            # Apply position status filter
            if q_selected_advert_status != "All" and q_position_titles:
                quick_results = quick_results[quick_results['position_applied'].isin(q_position_titles)]
            
            st.session_state.quick_results = quick_results
            st.session_state.quick_search_triggered = True
        
        # Display quick search results
        if st.session_state.quick_search_triggered:
            if st.session_state.quick_results is not None and not st.session_state.quick_results.empty:
                quick_df = st.session_state.quick_results
                
                # Show active advert status filter
                if st.session_state.quick_advert_status != "All":
                    st.info(f"📌 Currently showing positions with status: **{st.session_state.quick_advert_status}**")
                
                st.markdown("---")
                st.markdown("### 📊 Filter by Application Status")
                
                # Create status filter buttons
                col1, col2, col3, col4 = st.columns(4)
                
                q_total = len(quick_df)
                q_shortlisted = len(quick_df[quick_df['application_status'] == 'Shortlisted']) if 'application_status' in quick_df.columns else 0
                q_interviewed = len(quick_df[quick_df['interview_score'].notna() & (quick_df['interview_score'] > 0)]) if 'interview_score' in quick_df.columns else 0
                q_successful = len(quick_df[quick_df['application_status'] == 'Recommended']) if 'application_status' in quick_df.columns else 0
                
                with col1:
                    if st.button(f"📊 All Applicants ({q_total})", use_container_width=True, key="q_status_all_btn"):
                        st.session_state.quick_status_filter = "All Applicants"
                        st.rerun()
                
                with col2:
                    if st.button(f"⭐ Shortlisted ({q_shortlisted})", use_container_width=True, key="q_status_shortlisted_btn"):
                        st.session_state.quick_status_filter = "Shortlisted"
                        st.rerun()
                
                with col3:
                    if st.button(f"🎤 Interviewed ({q_interviewed})", use_container_width=True, key="q_status_interviewed_btn"):
                        st.session_state.quick_status_filter = "Interviewed"
                        st.rerun()
                
                with col4:
                    if st.button(f"🏆 Successful ({q_successful})", use_container_width=True, key="q_status_successful_btn"):
                        st.session_state.quick_status_filter = "Successful"
                        st.rerun()
                
                # Apply status filter
                display_quick = quick_df.copy()
                if st.session_state.quick_status_filter == "Shortlisted":
                    display_quick = display_quick[display_quick['application_status'] == 'Shortlisted']
                elif st.session_state.quick_status_filter == "Interviewed":
                    display_quick = display_quick[display_quick['interview_score'].notna() & (display_quick['interview_score'] > 0)]
                elif st.session_state.quick_status_filter == "Successful":
                    display_quick = display_quick[display_quick['application_status'] == 'Recommended']
                
                st.info(f"📌 Currently showing: **{st.session_state.quick_status_filter}** ({len(display_quick)} records)")
                
                st.markdown("---")
                st.success(f"✅ Found {len(display_quick)} record(s)")
                st.dataframe(display_quick, use_container_width=True)
                
                # Export quick search results
                csv = display_quick.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Search Results (CSV)",
                    csv,
                    f"quick_search_results_{st.session_state.quick_status_filter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            elif quick_search_clicked and search_term:
                st.warning("No records found matching your search term.")
        else:
            if not quick_search_clicked:
                st.info("👆 Enter a name or ID number above and click SEARCH to find specific staff members.")
    
    # ==================== SUPER ADMIN DELETE FUNCTIONALITY ====================
    if st.session_state.user["role"] == "Super Admin":
        st.markdown("---")
        st.warning("⚠️ SUPER ADMIN ACTIONS - Use with extreme caution!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Delete single record
            st.subheader("🗑️ Delete Specific Record")
            record_id = st.number_input("Enter Record ID to delete", min_value=1, step=1, key="delete_record_id")
            if st.button("Delete Record", use_container_width=True, key="delete_single_btn"):
                confirm = st.checkbox("Confirm delete this record?")
                if confirm:
                    conn = get_conn()
                    c = conn.cursor()
                    
                    c.execute("SELECT name, id_number FROM staff WHERE id = ?", (record_id,))
                    record = c.fetchone()
                    
                    if record:
                        c.execute("DELETE FROM staff WHERE id = ?", (record_id,))
                        conn.commit()
                        log_audit(st.session_state.user['username'], "DELETE", record_id, f"Deleted staff: {record[0]} (ID: {record[1]})", "Success")
                        st.success(f"✅ Record {record_id} deleted successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Record {record_id} not found")
                    conn.close()
                else:
                    st.warning("Please confirm to delete")
        
        with col2:
            # Delete all filtered records
            if st.session_state.advanced_search_triggered and st.session_state.advanced_results is not None and not st.session_state.advanced_results.empty:
                current_display_df = st.session_state.advanced_results.copy()
                if st.session_state.status_filter == "Shortlisted":
                    current_display_df = current_display_df[current_display_df['application_status'] == 'Shortlisted']
                elif st.session_state.status_filter == "Interviewed":
                    current_display_df = current_display_df[current_display_df['interview_score'].notna() & (current_display_df['interview_score'] > 0)]
                elif st.session_state.status_filter == "Successful":
                    current_display_df = current_display_df[current_display_df['application_status'] == 'Recommended']
                
                st.subheader("⚠️ Delete Current View Records")
                st.caption(f"This will delete ALL {len(current_display_df)} records currently displayed ({st.session_state.status_filter})")
                
                if st.button("🗑️ Delete Current View Records", use_container_width=True, key="delete_all_btn"):
                    confirm = st.checkbox("Confirm: I understand this will delete ALL filtered records permanently")
                    if confirm and not current_display_df.empty:
                        conn = get_conn()
                        c = conn.cursor()
                        
                        ids_to_delete = current_display_df['id'].tolist()
                        if ids_to_delete:
                            placeholders = ','.join(['?'] * len(ids_to_delete))
                            c.execute(f"DELETE FROM staff WHERE id IN ({placeholders})", ids_to_delete)
                            conn.commit()
                            
                            log_audit(st.session_state.user['username'], "DELETE_ALL", 0, f"Deleted {len(ids_to_delete)} {st.session_state.status_filter} records", "Success")
                            st.success(f"✅ {len(ids_to_delete)} records deleted successfully!")
                            st.session_state.advanced_results = None
                            st.session_state.advanced_search_triggered = False
                            st.session_state.status_filter = "All Applicants"
                            st.rerun()
                        conn.close()
                    else:
                        st.warning("Please confirm to delete records")
            else:
                st.info("Run an advanced search first to enable 'Delete Current View Records'")
# =========================================================
# EDIT APPLICANT RECORD (RECRUITMENT SYSTEM)
# =========================================================
def edit_applicant():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">✏️ Edit Application</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Update applicant information and recruitment status</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Get all applicants data
    df = pd.read_sql("SELECT * FROM staff ORDER BY id DESC", conn)
    
    if df.empty:
        st.warning("No applicants found to edit.")
        conn.close()
        return
    
    # Initialize session state variables
    if 'edit_search_results' not in st.session_state:
        st.session_state.edit_search_results = None
    if 'edit_search_performed' not in st.session_state:
        st.session_state.edit_search_performed = False
    if 'selected_applicant' not in st.session_state:
        st.session_state.selected_applicant = None
    if 'edit_search_triggered' not in st.session_state:
        st.session_state.edit_search_triggered = False
    
    # ======================================================
    # ADVANCED SEARCH SECTION
    # ======================================================
    st.subheader("🔍 Search Applicant")
    
    # Create search columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_name = st.text_input("Search by Name", placeholder="Enter full or partial name...", key="edit_search_name")
        search_id = st.text_input("Search by ID Number", placeholder="Enter ID number...", key="edit_search_id")
        gender_filter = st.selectbox("Filter by Gender", ["All", "Male", "Female", "Other"], key="edit_gender_filter")
    
    with col2:
        position_options = ["All Positions"] + sorted(df['position_applied'].dropna().unique().tolist())
        position_filter = st.selectbox("Filter by Position", position_options, key="edit_position_filter")
        
        status_options = ["All Status"] + sorted(df['application_status'].dropna().unique().tolist())
        status_filter = st.selectbox("Filter by Status", status_options, key="edit_status_filter")
        
        subcounty_options = ["All Sub-Counties"] + sorted(df['subcounty'].dropna().unique().tolist())
        subcounty_filter = st.selectbox("Filter by Sub-County", subcounty_options, key="edit_subcounty_filter")
    
    with col3:
        search_qualification = st.text_input("Search by Qualification", placeholder="Enter qualification...", key="edit_qualification_filter")
        
        if 'yob' in df.columns and not df['yob'].isna().all():
            age_range = st.slider("Age Range", 18, 100, (18, 100), key="edit_age_filter")
    
    # Search and Clear buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_clicked = st.button("🔍 SEARCH APPLICANTS", use_container_width=True, type="primary", key="edit_search_btn")
    
    with col1:
        if st.button("🗑️ Clear Search", use_container_width=True, key="edit_clear_btn"):
            st.session_state.edit_search_results = None
            st.session_state.edit_search_performed = False
            st.session_state.selected_applicant = None
            st.session_state.edit_search_triggered = False
            st.rerun()
    
    # Perform search ONLY when button is clicked
    if search_clicked:
        filtered_df = df.copy()
        
        # Apply filters
        if search_name:
            filtered_df = filtered_df[filtered_df['name'].str.contains(search_name, case=False, na=False)]
        if search_id:
            filtered_df = filtered_df[filtered_df['id_number'].str.contains(search_id, na=False)]
        if gender_filter != "All":
            filtered_df = filtered_df[filtered_df['gender'] == gender_filter]
        if position_filter != "All Positions":
            filtered_df = filtered_df[filtered_df['position_applied'] == position_filter]
        if status_filter != "All Status":
            filtered_df = filtered_df[filtered_df['application_status'] == status_filter]
        if subcounty_filter != "All Sub-Counties":
            filtered_df = filtered_df[filtered_df['subcounty'] == subcounty_filter]
        if search_qualification:
            filtered_df = filtered_df[filtered_df['qualifications'].str.contains(search_qualification, case=False, na=False)]
        if 'yob' in filtered_df.columns:
            current_year = datetime.now().year
            filtered_df['age_calc'] = current_year - filtered_df['yob']
            filtered_df = filtered_df[(filtered_df['age_calc'] >= age_range[0]) & (filtered_df['age_calc'] <= age_range[1])]
            # Remove temporary age column
            filtered_df = filtered_df.drop(columns=['age_calc'])
        
        st.session_state.edit_search_results = filtered_df
        st.session_state.edit_search_performed = True
        st.session_state.edit_search_triggered = True
        st.session_state.selected_applicant = None  # Clear selected applicant on new search
    
    # Display search results ONLY if search was performed
    if st.session_state.edit_search_triggered and st.session_state.edit_search_performed:
        results_df = st.session_state.edit_search_results
        
        if results_df is None or results_df.empty:
            st.warning("No applicants found matching your search criteria.")
            # Reset search state
            st.session_state.edit_search_triggered = False
        else:
            st.success(f"✅ Found {len(results_df)} applicant(s)")
            
            # Display results in a table for selection
            st.subheader("📋 Select Applicant to Edit")
            
            # Create a dataframe for selection
            select_df = results_df[['id', 'name', 'id_number', 'position_applied', 'application_status']].copy()
            st.dataframe(select_df, use_container_width=True)
            
            # Dropdown to select applicant
            selected_id = st.selectbox(
                "Select Applicant by ID",
                results_df['id'].tolist(),
                format_func=lambda x: f"ID: {x} - {results_df[results_df['id']==x]['name'].iloc[0]} ({results_df[results_df['id']==x]['position_applied'].iloc[0]})",
                key="edit_selected_applicant_dropdown"
            )
            
            if selected_id and selected_id != st.session_state.selected_applicant:
                st.session_state.selected_applicant = selected_id
                st.rerun()
    
# =========================================================
# REVIEW MODULE
# =========================================================
def review_module():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">⭐ Review Module</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Review and evaluate applicants with remarks tracking</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Super Admin access check
    if st.session_state.user.get("role") != "Super Admin":
        st.error("⛔ Access Denied. Super Admin privileges required.")
        conn.close()
        return
    
    # =========================================================
    # CREATE REVIEW TABLE FIRST (USING CURSOR)
    # =========================================================
    try:
        cursor = conn.cursor()
        
        if is_cloud:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_reviews (
                    id SERIAL PRIMARY KEY,
                    applicant_id INTEGER,
                    applicant_name TEXT,
                    id_number TEXT,
                    contact TEXT,
                    position_applied TEXT,
                    advertisement_ref TEXT,
                    department TEXT,
                    vacancies INTEGER,
                    remarks TEXT,
                    reviewed_by TEXT,
                    review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'Pending'
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    applicant_id INTEGER,
                    applicant_name TEXT,
                    id_number TEXT,
                    contact TEXT,
                    position_applied TEXT,
                    advertisement_ref TEXT,
                    department TEXT,
                    vacancies INTEGER,
                    remarks TEXT,
                    reviewed_by TEXT,
                    review_date TEXT,
                    status TEXT DEFAULT 'Pending'
                )
            """)
        conn.commit()
        cursor.close()
    except Exception as e:
        st.error(f"Error creating table: {e}")
    
    # Get advertised positions for filter
    try:
        if is_cloud:
            positions_df = pd.read_sql("""
                SELECT id, position_title, position_code, department, vacancies, status 
                FROM advertised_positions 
                ORDER BY id DESC
            """, conn)
        else:
            positions_df = pd.read_sql("""
                SELECT id, position_title, position_code, department, vacancies, status 
                FROM advertised_positions 
                ORDER BY id DESC
            """, conn)
    except:
        positions_df = pd.DataFrame()
    
    # Get all staff data
    df = pd.read_sql("SELECT * FROM staff ORDER BY id DESC", conn)
    
    if df.empty:
        st.warning("No records found. Please add records using Staff Entry or Import Excel.")
        conn.close()
        return
    
    # Initialize session state
    if 'review_search_triggered' not in st.session_state:
        st.session_state.review_search_triggered = False
    if 'review_results' not in st.session_state:
        st.session_state.review_results = None
    if 'review_selected_ids' not in st.session_state:
        st.session_state.review_selected_ids = []
    if 'review_advert_status_filter' not in st.session_state:
        st.session_state.review_advert_status_filter = "All"
    if 'review_quick_advert_status' not in st.session_state:
        st.session_state.review_quick_advert_status = "All"
    
    # Create two tabs: Search & Review and All Reviews
    review_tab1, review_tab2 = st.tabs(["📝 Search & Review", "📋 All Reviews"])
    
    # ==================== TAB 1: SEARCH & REVIEW ====================
    with review_tab1:
        st.markdown("### 🔍 Search Applicants")
        
        # Create sub-tabs for Advanced Search and Quick Search
        search_type_tab1, search_type_tab2 = st.tabs(["🔎 Advanced Search", "📝 Quick Search"])
        
        # ==================== ADVANCED SEARCH SUB-TAB ====================
        with search_type_tab1:
            st.info("Select your search criteria below, then click the SEARCH button to find applicants.")
            
            # Create filter columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Position filter with status selection
                st.markdown("**Advertised Position Status**")
                advert_status_options = ["All", "Open", "Closed", "On Hold"]
                
                current_index = 0
                if st.session_state.review_advert_status_filter == "Open":
                    current_index = 1
                elif st.session_state.review_advert_status_filter == "Closed":
                    current_index = 2
                elif st.session_state.review_advert_status_filter == "On Hold":
                    current_index = 3
                
                selected_advert_status = st.radio(
                    "Select Position Status",
                    advert_status_options,
                    index=current_index,
                    key="review_advert_status",
                    horizontal=True
                )
                
                if selected_advert_status != st.session_state.review_advert_status_filter:
                    st.session_state.review_advert_status_filter = selected_advert_status
                    st.session_state.review_search_triggered = False
                    st.session_state.review_results = None
                    st.rerun()
                
                if selected_advert_status != "All":
                    filtered_positions_df = positions_df[positions_df['status'] == selected_advert_status]
                else:
                    filtered_positions_df = positions_df
                
                if not filtered_positions_df.empty:
                    position_options = ["All Positions"] + [f"{row['position_title']} ({row['position_code']})" for _, row in filtered_positions_df.iterrows()]
                    selected_position = st.selectbox("Filter by Position", position_options, key="review_position_filter")
                    if selected_position != "All Positions":
                        selected_position_title = selected_position.split(" (")[0]
                    else:
                        selected_position_title = None
                else:
                    selected_position = "All Positions"
                    selected_position_title = None
                    st.info(f"No {selected_advert_status} positions found")
                
                # Subcounty filter
                subcounty_options = ["All Sub-Counties"] + sorted(df['subcounty'].dropna().unique().tolist()) if 'subcounty' in df.columns else ["All Sub-Counties"]
                selected_subcounty = st.selectbox("Filter by Sub-County", subcounty_options, key="review_subcounty_filter")
                
                # Gender filter
                gender_options = ["All Genders", "Male", "Female", "Other"]
                selected_gender = st.selectbox("Filter by Gender", gender_options, key="review_gender_filter")
            
            with col2:
                # Ward filter
                ward_options = ["All Wards"] + sorted(df['ward'].dropna().unique().tolist()) if 'ward' in df.columns else ["All Wards"]
                selected_ward = st.selectbox("Filter by Ward", ward_options, key="review_ward_filter")
                
                # Application Status filter
                st.markdown("**Application Status**")
                status_options = ["All Status"] + sorted(df['application_status'].dropna().unique().tolist()) if 'application_status' in df.columns else ["All Status"]
                selected_status = st.selectbox("Filter by Application Status", status_options, key="review_status_search")
                
                # Disability filter
                disability_options = ["All", "With Disability", "Without Disability"]
                selected_disability = st.selectbox("Filter by Disability", disability_options, key="review_disability_filter")
            
            with col3:
                # Ethnicity filter
                ethnicity_options = ["All Ethnicities"] + sorted(df['ethnicity'].dropna().unique().tolist()) if 'ethnicity' in df.columns else ["All Ethnicities"]
                selected_ethnicity = st.selectbox("Filter by Ethnicity", ethnicity_options, key="review_ethnicity_filter")
                
                # Qualification filter
                search_qualification = st.text_input("Search by Qualification", placeholder="Enter qualification...", key="review_qualification_filter")
                
                # Age range filter
                if 'yob' in df.columns and not df['yob'].isna().all():
                    current_year = datetime.now().year
                    df['age_calc'] = current_year - df['yob']
                    min_age = int(df['age_calc'].min()) if not df['age_calc'].isna().all() else 18
                    max_age = int(df['age_calc'].max()) if not df['age_calc'].isna().all() else 100
                    age_range = st.slider("Age Range", min_age, max_age, (min_age, max_age), key="review_age_filter")
                else:
                    age_range = (18, 100)
                    st.slider("Age Range", 18, 100, (18, 100), key="review_age_filter_dummy")
            
            # Search and Clear buttons
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                search_clicked = st.button("🔍 SEARCH APPLICANTS", use_container_width=True, type="primary", key="review_search_btn")
            
            with col1:
                if st.button("🗑️ Clear All", use_container_width=True, key="review_clear_btn"):
                    st.session_state.review_search_triggered = False
                    st.session_state.review_results = None
                    st.session_state.review_selected_ids = []
                    st.rerun()
            
            # Perform search
            if search_clicked:
                filtered_df = df.copy()
                
                # Filter by position status
                if selected_advert_status != "All":
                    valid_positions = positions_df[positions_df['status'] == selected_advert_status]['position_title'].tolist()
                    if valid_positions:
                        filtered_df = filtered_df[filtered_df['position_applied'].isin(valid_positions)]
                    else:
                        filtered_df = pd.DataFrame()
                
                if selected_position_title and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['position_applied'] == selected_position_title]
                
                if selected_subcounty != "All Sub-Counties" and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['subcounty'] == selected_subcounty]
                
                if selected_gender != "All Genders" and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['gender'] == selected_gender]
                
                if selected_ward != "All Wards" and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['ward'] == selected_ward]
                
                if selected_status != "All Status" and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['application_status'] == selected_status]
                
                if selected_disability == "With Disability" and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['disability'].notna() & (filtered_df['disability'] != '') & (filtered_df['disability'] != 'None') & (filtered_df['disability'].str.lower() != 'none')]
                elif selected_disability == "Without Disability" and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['disability'].isna() | (filtered_df['disability'] == '') | (filtered_df['disability'] == 'None') | (filtered_df['disability'].str.lower() == 'none')]
                
                if selected_ethnicity != "All Ethnicities" and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['ethnicity'] == selected_ethnicity]
                
                if search_qualification and not filtered_df.empty:
                    filtered_df = filtered_df[filtered_df['qualifications'].str.contains(search_qualification, case=False, na=False)]
                
                if 'age_calc' in filtered_df.columns and not filtered_df.empty:
                    filtered_df = filtered_df[(filtered_df['age_calc'] >= age_range[0]) & (filtered_df['age_calc'] <= age_range[1])]
                
                st.session_state.review_results = filtered_df
                st.session_state.review_search_triggered = True
                st.session_state.review_selected_ids = []
        
        # ==================== QUICK SEARCH SUB-TAB ====================
        with search_type_tab2:
            st.info("Search by Name or ID Number to quickly find applicants.")
            
            # Add advert status filter for quick search
            st.markdown("**Advertised Position Status**")
            q_advert_status_options = ["All", "Open", "Closed", "On Hold"]
            
            q_current_index = 0
            if st.session_state.review_quick_advert_status == "Open":
                q_current_index = 1
            elif st.session_state.review_quick_advert_status == "Closed":
                q_current_index = 2
            elif st.session_state.review_quick_advert_status == "On Hold":
                q_current_index = 3
            
            q_selected_advert_status = st.radio(
                "Select Position Status",
                q_advert_status_options,
                index=q_current_index,
                key="review_quick_advert_status",
                horizontal=True
            )
            
            # Update session state
            if q_selected_advert_status != st.session_state.review_quick_advert_status:
                st.session_state.review_quick_advert_status = q_selected_advert_status
                st.rerun()
            
            # Filter positions based on status
            if q_selected_advert_status != "All":
                q_filtered_positions = positions_df[positions_df['status'] == q_selected_advert_status]
                q_position_titles = q_filtered_positions['position_title'].tolist() if not q_filtered_positions.empty else []
            else:
                q_position_titles = positions_df['position_title'].tolist() if not positions_df.empty else []
            
            col1, col2 = st.columns([3, 1])
            with col1:
                quick_search_term = st.text_input("Search by Name or ID Number", placeholder="Type name or ID number...", key="review_quick_search_input")
            with col2:
                quick_search_clicked = st.button("🔍 QUICK SEARCH", use_container_width=True, type="primary", key="review_quick_search_btn")
            
            # Clear button for quick search
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                if st.button("🗑️ Clear Quick Search", use_container_width=True, key="review_quick_clear_btn"):
                    st.session_state.review_search_triggered = False
                    st.session_state.review_results = None
                    st.session_state.review_selected_ids = []
                    st.rerun()
            
            # Perform quick search when button is clicked
            if quick_search_clicked and quick_search_term:
                quick_results = df[
                    df['name'].str.contains(quick_search_term, case=False, na=False) |
                    df['id_number'].str.contains(quick_search_term, na=False)
                ]
                
                # Apply position status filter
                if q_selected_advert_status != "All" and q_position_titles:
                    quick_results = quick_results[quick_results['position_applied'].isin(q_position_titles)]
                
                st.session_state.review_results = quick_results
                st.session_state.review_search_triggered = True
                st.session_state.review_selected_ids = []
                
                if quick_results.empty:
                    st.warning("No records found matching your search term.")
        
        # Display results (common for both Advanced and Quick Search)
        if st.session_state.review_search_triggered:
            if st.session_state.review_results is not None and not st.session_state.review_results.empty:
                results_df = st.session_state.review_results
                
                st.success(f"✅ Found {len(results_df)} applicant(s)")
                
                # Display results with checkboxes
                st.markdown("### 📋 Select Applicants to Review")
                
                # Create a form for batch selection
                with st.form("review_selection_form"):
                    # Display dataframe with checkboxes
                    selected_ids = []
                    
                    for idx, row in results_df.iterrows():
                        col1, col2, col3, col4, col5, col6 = st.columns([0.3, 2, 1.5, 1.5, 2, 1.5])
                        
                        with col1:
                            is_selected = st.checkbox("", key=f"review_select_{row['id']}")
                            if is_selected:
                                selected_ids.append(row['id'])
                        
                        with col2:
                            st.write(f"**{row['name']}**")
                        with col3:
                            st.write(f"ID: {row['id_number']}")
                        with col4:
                            st.write(f"Contact: {row['contact']}")
                        with col5:
                            st.write(f"Position: {row['position_applied'][:30]}")
                        with col6:
                            st.write(f"Status: {row['application_status']}")
                    
                    st.markdown("---")
                    
                    # Remarks input
                    remarks = st.text_area("Remarks", placeholder="Enter review remarks for selected applicants...", height=100, key="review_remarks_input")
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        submit_review = st.form_submit_button("✅ SUBMIT REVIEW", use_container_width=True, type="primary")
                    
                    if submit_review and selected_ids:
                        # Save reviews to database
                        cur = conn.cursor()
                        saved_count = 0
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        username = st.session_state.user['username']
                        
                        for app_id in selected_ids:
                            # Convert numpy.int64 to Python int
                            app_id_int = int(app_id)
                            applicant = results_df[results_df['id'] == app_id_int].iloc[0]
                            
                            # Convert all numpy values to Python native types
                            applicant_name = str(applicant['name']) if applicant['name'] else ''
                            applicant_id_number = str(applicant['id_number']) if applicant['id_number'] else ''
                            applicant_contact = str(applicant['contact']) if applicant['contact'] else ''
                            applicant_position = str(applicant['position_applied']) if applicant['position_applied'] else ''
                            
                            # Get position details
                            position_details = positions_df[positions_df['position_title'] == applicant_position]
                            dept = str(position_details['department'].iloc[0]) if not position_details.empty else 'N/A'
                            vacancies = int(position_details['vacancies'].iloc[0]) if not position_details.empty else 0
                            advert_ref = str(position_details['position_code'].iloc[0]) if not position_details.empty else 'N/A'
                            
                            # Convert remarks to string
                            remarks_str = str(remarks) if remarks else ''
                            
                            if is_cloud:
                                cur.execute("""
                                    INSERT INTO hr_reviews (
                                        applicant_id, applicant_name, id_number, contact,
                                        position_applied, advertisement_ref, department, vacancies,
                                        remarks, reviewed_by, review_date, status
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    app_id_int, applicant_name, applicant_id_number, applicant_contact,
                                    applicant_position, advert_ref, dept, vacancies,
                                    remarks_str, username, now, 'Pending'
                                ))
                            else:
                                cur.execute("""
                                    INSERT INTO hr_reviews (
                                        applicant_id, applicant_name, id_number, contact,
                                        position_applied, advertisement_ref, department, vacancies,
                                        remarks, reviewed_by, review_date, status
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    app_id_int, applicant_name, applicant_id_number, applicant_contact,
                                    applicant_position, advert_ref, dept, vacancies,
                                    remarks_str, username, now, 'Pending'
                                ))
                            saved_count += 1
                        
                        conn.commit()
                        cur.close()
                        
                        log_audit(username, "REVIEW_SUBMIT", 0, f"Submitted review for {saved_count} applicant(s) with remarks", "Success")
                        
                        st.success(f"✅ Successfully reviewed {saved_count} applicant(s)!")
                        st.session_state.review_selected_ids = []
                        st.rerun()
                    
                    elif submit_review and not selected_ids:
                        st.warning("⚠️ Please select at least one applicant to review")
                
            else:
                st.warning("No records match your search criteria.")
        else:
            st.info("👆 Use Advanced Search or Quick Search above to find applicants to review.")
    
    # ==================== TAB 2: ALL REVIEWS ====================
    with review_tab2:
        st.markdown("### 📋 All Reviews")
        
        # Load all reviews
        try:
            reviews_df = pd.read_sql("SELECT * FROM hr_reviews ORDER BY review_date DESC", conn)
        except Exception as e:
            st.info("No reviews found. Submit reviews in the 'Search & Review' tab first.")
            reviews_df = pd.DataFrame()
        
        if reviews_df.empty:
            st.info("No reviews have been submitted yet.")
        else:
            # =========================================================
            # QUICK SEARCH FOR ALL REVIEWS (Same as Search & Review)
            # =========================================================
            st.markdown("### 🔎 Quick Search")
            st.info("Search by Name or ID Number to quickly find reviews.")
            
            # Add advert status filter for quick search
            st.markdown("**Advertised Position Status**")
            q_advert_status_options = ["All", "Open", "Closed", "On Hold"]
            
            q_current_index = 0
            if st.session_state.get('review_quick_advert_status', "All") == "Open":
                q_current_index = 1
            elif st.session_state.get('review_quick_advert_status', "All") == "Closed":
                q_current_index = 2
            elif st.session_state.get('review_quick_advert_status', "All") == "On Hold":
                q_current_index = 3
            
            q_selected_advert_status = st.radio(
                "Select Position Status",
                q_advert_status_options,
                index=q_current_index,
                key="review_quick_advert_status_all",
                horizontal=True
            )
            
            # Update session state
            if q_selected_advert_status != st.session_state.get('review_quick_advert_status', "All"):
                st.session_state.review_quick_advert_status = q_selected_advert_status
                st.rerun()
            
            # Filter positions based on status
            if q_selected_advert_status != "All":
                q_filtered_positions = positions_df[positions_df['status'] == q_selected_advert_status]
                q_position_titles = q_filtered_positions['position_title'].tolist() if not q_filtered_positions.empty else []
            else:
                q_position_titles = positions_df['position_title'].tolist() if not positions_df.empty else []
            
            col1, col2 = st.columns([3, 1])
            with col1:
                quick_search_term = st.text_input("Search by Name or ID Number", placeholder="Type name or ID number...", key="review_quick_search_input_all")
            with col2:
                quick_search_clicked = st.button("🔍 QUICK SEARCH", use_container_width=True, type="primary", key="review_quick_search_btn_all")
            
            # Clear button for quick search
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                if st.button("🗑️ Clear Quick Search", use_container_width=True, key="review_quick_clear_btn_all"):
                    st.session_state.review_search_triggered = False
                    st.session_state.review_results = None
                    st.session_state.review_selected_ids = []
                    st.rerun()
            
            # Perform quick search when button is clicked
            if quick_search_clicked and quick_search_term:
                quick_results = reviews_df[
                    reviews_df['applicant_name'].str.contains(quick_search_term, case=False, na=False) |
                    reviews_df['id_number'].str.contains(quick_search_term, na=False)
                ]
                
                # Apply position status filter
                if q_selected_advert_status != "All" and q_position_titles:
                    quick_results = quick_results[quick_results['position_applied'].isin(q_position_titles)]
                
                filtered_reviews = quick_results
                
                if quick_results.empty:
                    st.warning("No records found matching your search term.")
            else:
                # If no search performed, show all reviews
                filtered_reviews = reviews_df
            
            # Show search results count
            st.info(f"📊 Showing {len(filtered_reviews)} of {len(reviews_df)} reviews")
            st.markdown("---")
            
            # Group filtered reviews by position
            if not filtered_reviews.empty:
                grouped_reviews = filtered_reviews.groupby(['position_applied', 'advertisement_ref', 'department', 'vacancies'])
                
                # Build display and export content
                display_content = []
                export_content = []
                
                for (position, advert_ref, dept, vacancies), group in grouped_reviews:
                    # Header
                    header = f"{position} {advert_ref} {dept} VACANCIES {vacancies}"
                    st.markdown(f"### {header}")
                    display_content.append(header)
                    export_content.append(header)
                    export_content.append("")
                    
                    # Table header
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown("**Name**")
                    with col2:
                        st.markdown("**ID Number**")
                    with col3:
                        st.markdown("**Contacts**")
                    with col4:
                        st.markdown("**Remarks**")
                    
                    export_content.append("Name\tID Number\tContacts\tRemarks")
                    
                    # Table rows
                    for idx, row in group.iterrows():
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.write(row['applicant_name'])
                        with col2:
                            st.write(row['id_number'])
                        with col3:
                            st.write(row['contact'])
                        with col4:
                            st.write(row['remarks'] if row['remarks'] else '')
                        
                        export_content.append(f"{row['applicant_name']}\t{row['id_number']}\t{row['contact']}\t{row['remarks'] if row['remarks'] else ''}")
                    
                    st.caption(f"Total: {len(group)} applicant(s)")
                    export_content.append(f"Total: {len(group)} applicant(s)")
                    export_content.append("")
                    st.markdown("---")
                
                # Export
                st.markdown("### 📥 Export Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    export_text = "\n".join(export_content)
                    st.download_button(
                        "📥 Download as Text (TXT)",
                        export_text,
                        f"all_reviews_{datetime.now().strftime('%Y%m%d')}.txt",
                        "text/plain",
                        use_container_width=True
                    )
                
                with col2:
                    # CSV export
                    export_rows = []
                    for (position, advert_ref, dept, vacancies), group in grouped_reviews:
                        for idx, row in group.iterrows():
                            export_rows.append({
                                'Position': position,
                                'Advert Code': advert_ref,
                                'Department': dept,
                                'Vacancies': vacancies,
                                'Name': row['applicant_name'],
                                'ID Number': row['id_number'],
                                'Contacts': row['contact'],
                                'Remarks': row['remarks'] if row['remarks'] else ''
                            })
                    export_df = pd.DataFrame(export_rows)
                    csv = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download as CSV",
                        csv,
                        f"all_reviews_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
            else:
                st.info("No reviews match your search criteria.")
# =========================================================
# EDIT APPLICANT RECORD (RECRUITMENT SYSTEM) - FIXED
# =========================================================
def edit_applicant():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">✏️ Edit Application</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Update applicant information and recruitment status</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Get all applicants data
    df = pd.read_sql("SELECT * FROM staff ORDER BY id DESC", conn)
    
    if df.empty:
        st.warning("No applicants found to edit.")
        conn.close()
        return
    
    # Initialize session state
    if 'edit_selected_applicant' not in st.session_state:
        st.session_state.edit_selected_applicant = None
    if 'edit_search_results' not in st.session_state:
        st.session_state.edit_search_results = None
    if 'edit_search_performed' not in st.session_state:
        st.session_state.edit_search_performed = False
    
    # Search section - Only show if no applicant is selected
    if st.session_state.edit_selected_applicant is None:
        st.subheader("🔍 Search Applicant")
        
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("Search by Name", placeholder="Enter name...", key="edit_search_name")
        with col2:
            search_id = st.text_input("Search by ID Number", placeholder="Enter ID number...", key="edit_search_id")
        
        # Search button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔍 SEARCH", use_container_width=True, type="primary", key="edit_search_btn"):
                # Perform search
                filtered_df = df.copy()
                if search_name:
                    filtered_df = filtered_df[filtered_df['name'].str.contains(search_name, case=False, na=False)]
                if search_id:
                    filtered_df = filtered_df[filtered_df['id_number'].str.contains(search_id, na=False)]
                
                st.session_state.edit_search_results = filtered_df
                st.session_state.edit_search_performed = True
        
        # Display search results
        if st.session_state.edit_search_performed and st.session_state.edit_search_results is not None:
            results_df = st.session_state.edit_search_results
            
            if results_df.empty:
                st.warning("No applicants found matching your search criteria.")
                st.session_state.edit_search_performed = False
            else:
                st.success(f"Found {len(results_df)} applicant(s)")
                st.dataframe(results_df[['id', 'name', 'id_number', 'position_applied', 'application_status']], use_container_width=True)
                
                # Select applicant - convert id to int
                id_list = [int(row['id']) for _, row in results_df.iterrows()]
                
                selected_id = st.selectbox(
                    "Select Applicant ID to Edit",
                    id_list,
                    format_func=lambda x: f"{x} - {results_df[results_df['id']==x]['name'].iloc[0]}",
                    key="edit_select_applicant"
                )
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("📝 Load Applicant", use_container_width=True, type="primary"):
                        st.session_state.edit_selected_applicant = int(selected_id)
                        st.rerun()
    
    # Edit form - Only show when an applicant is selected
    if st.session_state.edit_selected_applicant is not None:
        applicant = pd.read_sql(f"SELECT * FROM staff WHERE id = {int(st.session_state.edit_selected_applicant)}", conn)
        
        if not applicant.empty:
            app = applicant.iloc[0]
            
            # Back button
            if st.button("← Back to Search", use_container_width=False):
                st.session_state.edit_selected_applicant = None
                st.session_state.edit_search_results = None
                st.session_state.edit_search_performed = False
                st.rerun()
            
            st.markdown("---")
            st.subheader(f"✏️ Editing: {app['name']}")
            
            # Show all applications by this applicant
            all_apps = df[df['id_number'] == app['id_number']]
            if len(all_apps) > 1:
                st.info(f"📌 This applicant has applied for {len(all_apps)} position(s)")
                for _, row in all_apps.iterrows():
                    st.caption(f"   - {row['position_applied']} ({row['application_status']})")
            
            st.markdown("---")
            
            # Create tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Application", "👤 Personal", "🎓 Education", "📍 Location"])
            
            # Helper function to convert numpy types to Python native types
            def to_native(val):
                if val is None or pd.isna(val):
                    return None
                if isinstance(val, (np.int64, np.int32)):
                    return int(val)
                if isinstance(val, (np.float64, np.float32)):
                    return float(val)
                return val
            
            # ==================== TAB 1: APPLICATION DETAILS ====================
            with tab1:
                col1, col2 = st.columns(2)
                with col1:
                    # Get unique position options
                    position_options = df['position_applied'].dropna().unique().tolist()
                    if not position_options:
                        position_options = ["ECDE Teacher", "Administrative Officer", "Accountant"]
                    
                    current_position = app['position_applied'] if app['position_applied'] else position_options[0]
                    position_index = position_options.index(current_position) if current_position in position_options else 0
                    
                    new_position = st.selectbox("Position Applied", position_options, index=position_index, key="edit_position")
                    
                    status_options = ["Pending", "Shortlisted", "Interview Scheduled", "Interviewed", "Recommended", "Hired", "Rejected"]
                    current_status = app['application_status'] if app['application_status'] else "Pending"
                    status_index = status_options.index(current_status) if current_status in status_options else 0
                    new_status = st.selectbox("Application Status", status_options, index=status_index, key="edit_status")
                
                with col2:
                    interview_date_val = datetime.strptime(app['interview_date'], "%Y-%m-%d") if app['interview_date'] and app['interview_date'] != "None" else datetime.now()
                    interview_date = st.date_input("Interview Date", value=interview_date_val, key="edit_interview_date")
                    
                    interview_score_val = float(to_native(app['interview_score'])) if app['interview_score'] else 0.0
                    interview_score = st.number_input("Interview Score (0-100)", min_value=0.0, max_value=100.0, value=interview_score_val, step=5.0, key="edit_score")
                
                remarks = st.text_area("Remarks/Notes", value=app['remarks'] if app['remarks'] else "", height=100, key="edit_remarks")
            
            # ==================== TAB 2: PERSONAL INFORMATION ====================
            with tab2:
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Full Name", value=app['name'] if app['name'] else "", key="edit_name")
                    
                    gender_options = ["Male", "Female", "Other"]
                    current_gender = app['gender'] if app['gender'] else "Male"
                    gender_index = gender_options.index(current_gender) if current_gender in gender_options else 0
                    new_gender = st.selectbox("Gender", gender_options, index=gender_index, key="edit_gender")
                    
                    new_id = st.text_input("ID Number", value=app['id_number'] if app['id_number'] else "", key="edit_id")
                    
                    yob_val = int(to_native(app['yob'])) if app['yob'] else 1990
                    new_yob = st.number_input("Year of Birth", min_value=1900, max_value=2026, value=yob_val, key="edit_yob")
                
                with col2:
                    new_contact = st.text_input("Phone Number", value=app['contact'] if app['contact'] else "", key="edit_contact")
                    new_email = st.text_input("Email Address", value=app['email'] if app['email'] else "", key="edit_email")
                    new_subcounty = st.text_input("Sub-County", value=app['subcounty'] if app['subcounty'] else "", key="edit_subcounty")
                    new_ward = st.text_input("Ward", value=app['ward'] if app['ward'] else "", key="edit_ward")
            
            # ==================== TAB 3: EDUCATION ====================
            with tab3:
                col1, col2 = st.columns(2)
                with col1:
                    new_qualifications = st.text_area("Qualifications", value=app['qualifications'] if app['qualifications'] else "", height=100, key="edit_qualifications")
                    new_institution = st.text_input("Institution", value=app['institution'] if app['institution'] else "", key="edit_institution")
                with col2:
                    new_kcse = st.text_input("KCSE Year/Grade", value=app['kcse'] if app['kcse'] else "", key="edit_kcse")
                    exp_val = int(to_native(app['experience_years'])) if app['experience_years'] else 0
                    new_experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=exp_val, key="edit_experience")
            
            # ==================== TAB 4: LOCATION & REFEREES ====================
            with tab4:
                st.markdown("**Referees**")
                col1, col2 = st.columns(2)
                with col1:
                    new_referee1 = st.text_input("Referee 1 Name", value=app['referee1_name'] if app['referee1_name'] else "", key="edit_ref1")
                    new_referee1_contact = st.text_input("Referee 1 Contact", value=app['referee1_contact'] if app['referee1_contact'] else "", key="edit_ref1_contact")
                with col2:
                    new_referee2 = st.text_input("Referee 2 Name", value=app['referee2_name'] if app['referee2_name'] else "", key="edit_ref2")
                    new_referee2_contact = st.text_input("Referee 2 Contact", value=app['referee2_contact'] if app['referee2_contact'] else "", key="edit_ref2_contact")
            
            # Save button
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("💾 SAVE CHANGES", use_container_width=True, type="primary"):
                    try:
                        cursor = conn.cursor()
                        
                        # Convert all values to Python native types
                        values = (
                            str(new_name) if new_name else None,
                            str(new_gender) if new_gender else None,
                            str(new_id) if new_id else None,
                            int(new_yob) if new_yob else None,
                            str(new_contact) if new_contact else None,
                            str(new_email) if new_email else None,
                            str(new_subcounty) if new_subcounty else None,
                            str(new_ward) if new_ward else None,
                            str(new_qualifications) if new_qualifications else None,
                            str(new_institution) if new_institution else None,
                            str(new_kcse) if new_kcse else None,
                            int(new_experience) if new_experience else 0,
                            str(new_position) if new_position else None,
                            str(new_status) if new_status else None,
                            interview_date.strftime("%Y-%m-%d") if interview_date else None,
                            float(interview_score) if interview_score else 0.0,
                            str(remarks) if remarks else None,
                            str(new_referee1) if new_referee1 else None,
                            str(new_referee1_contact) if new_referee1_contact else None,
                            str(new_referee2) if new_referee2 else None,
                            str(new_referee2_contact) if new_referee2_contact else None,
                            int(app['id'])
                        )
                        
                        if is_cloud:
                            cursor.execute("""
                                UPDATE staff SET 
                                    name = %s, gender = %s, id_number = %s, yob = %s,
                                    contact = %s, email = %s, subcounty = %s, ward = %s,
                                    qualifications = %s, institution = %s, kcse = %s,
                                    experience_years = %s, position_applied = %s,
                                    application_status = %s, interview_date = %s,
                                    interview_score = %s, remarks = %s,
                                    referee1_name = %s, referee1_contact = %s,
                                    referee2_name = %s, referee2_contact = %s
                                WHERE id = %s
                            """, values)
                        else:
                            cursor.execute("""
                                UPDATE staff SET 
                                    name = ?, gender = ?, id_number = ?, yob = ?,
                                    contact = ?, email = ?, subcounty = ?, ward = ?,
                                    qualifications = ?, institution = ?, kcse = ?,
                                    experience_years = ?, position_applied = ?,
                                    application_status = ?, interview_date = ?,
                                    interview_score = ?, remarks = ?,
                                    referee1_name = ?, referee1_contact = ?,
                                    referee2_name = ?, referee2_contact = ?
                                WHERE id = ?
                            """, values)
                        
                        conn.commit()
                        
                        log_audit(st.session_state.user['username'], "EDIT_APPLICANT", int(app['id']), 
                                 f"Updated applicant: {new_name} (ID: {new_id}) - Status: {new_status}", "Success")
                        
                        st.success("✅ Applicant updated successfully!")
                        st.balloons()
                        st.session_state.edit_selected_applicant = None
                        st.session_state.edit_search_results = None
                        st.session_state.edit_search_performed = False
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error updating: {e}")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.edit_selected_applicant = None
                    st.session_state.edit_search_results = None
                    st.session_state.edit_search_performed = False
                    st.rerun()
    
    conn.close()
# =========================================================
# SHORTLIST MANAGEMENT SYSTEM (Manual + Upload)
# =========================================================

def shortlist_management():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">⭐ Shortlist Management</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Shortlist candidates manually or via bulk upload using Name & ID Number</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📋 Manual Shortlisting", "📤 Bulk Upload Shortlist", "📊 Shortlisted Candidates"])
    
    # ==================== TAB 1: MANUAL SHORTLISTING ====================
    with tab1:
        st.subheader("✏️ Manual Shortlisting")
        st.info("Search and select candidates by Name or ID Number to add to shortlist")
        
        conn = get_conn()
        if conn is None:
            st.error("Database connection failed")
            return
        
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Get all applicants
        applicants_df = pd.read_sql("SELECT id, name, id_number, contact, email, qualifications, experience_years, application_status, subcounty FROM staff ORDER BY id DESC", conn)
        conn.close()
        
        if applicants_df.empty:
            st.warning("No applicants found. Please import applicants first.")
            return
        
        # Search by Name or ID
        col1, col2 = st.columns(2)
        
        with col1:
            search_by = st.radio("Search by", ["Name", "ID Number", "Both"])
        
        with col2:
            if search_by == "Name":
                search_term = st.text_input("Enter Name", placeholder="Type candidate name...")
            elif search_by == "ID Number":
                search_term = st.text_input("Enter ID Number", placeholder="Type ID number...")
            else:
                search_term = st.text_input("Search by Name or ID", placeholder="Type name or ID number...")
        
        # Additional filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_experience = st.number_input("Min Experience (Years)", min_value=0, max_value=30, value=0)
        
        with col2:
            qualification_filter = st.selectbox("Qualification", ["All", "ECDE Certificate", "ECDE Diploma", "Bachelor's Degree", "Master's Degree"])
        
        with col3:
            subcounty_filter = st.selectbox("Sub-County", ["All"] + sorted(applicants_df['subcounty'].dropna().unique().tolist()))
        
        # Filter applicants
        filtered_df = applicants_df.copy()
        
        if search_term:
            if search_by == "Name":
                filtered_df = filtered_df[filtered_df['name'].str.contains(search_term, case=False, na=False)]
            elif search_by == "ID Number":
                filtered_df = filtered_df[filtered_df['id_number'].str.contains(search_term, na=False)]
            else:
                filtered_df = filtered_df[
                    filtered_df['name'].str.contains(search_term, case=False, na=False) |
                    filtered_df['id_number'].str.contains(search_term, na=False)
                ]
        
        if min_experience > 0:
            filtered_df = filtered_df[filtered_df['experience_years'] >= min_experience]
        
        if qualification_filter != "All":
            filtered_df = filtered_df[filtered_df['qualifications'].str.contains(qualification_filter, case=False, na=False)]
        
        if subcounty_filter != "All":
            filtered_df = filtered_df[filtered_df['subcounty'] == subcounty_filter]
        
        # Only show non-shortlisted candidates
        filtered_df = filtered_df[filtered_df['application_status'] != 'Shortlisted']
        filtered_df = filtered_df[filtered_df['application_status'] != 'Hired']
        
        st.markdown(f"**📋 Found {len(filtered_df)} eligible candidates**")
        
        if not filtered_df.empty:
            st.markdown("### ✅ Select Candidates to Shortlist")
            
            selected_ids = []
            
            for idx, row in filtered_df.iterrows():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 2, 1.5, 1.5, 1.5, 1.5, 0.5])
                
                with col1:
                    selected = st.checkbox("", key=f"select_{row['id']}")
                    if selected:
                        selected_ids.append(row['id'])
                
                with col2:
                    st.write(f"**{row['name']}**")
                with col3:
                    st.write(f"🆔 {row['id_number']}")
                with col4:
                    st.write(f"📞 {row['contact']}")
                with col5:
                    st.write(f"⭐ {row['experience_years']} yrs")
                with col6:
                    qual_short = str(row['qualifications'])[:15] + "..." if len(str(row['qualifications'])) > 15 else row['qualifications']
                    st.write(f"🎓 {qual_short}")
                with col7:
                    st.write(f"📍 {row['subcounty'][:10] if row['subcounty'] else 'N/A'}")
            
            if selected_ids:
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button(f"⭐ Shortlist {len(selected_ids)} Selected Candidate(s)", use_container_width=True, type="primary"):
                        update_conn = get_conn()
                        if update_conn is None:
                            st.error("Database connection failed")
                        else:
                            update_cursor = update_conn.cursor()
                            success_count = 0
                            
                            for app_id in selected_ids:
                                try:
                                    if is_cloud:
                                        update_cursor.execute("""
                                            UPDATE staff 
                                            SET application_status = 'Shortlisted',
                                                shortlist_date = CURRENT_TIMESTAMP
                                            WHERE id = %s
                                        """, (app_id,))
                                    else:
                                        update_cursor.execute("""
                                            UPDATE staff 
                                            SET application_status = 'Shortlisted',
                                                shortlist_date = CURRENT_TIMESTAMP
                                            WHERE id = ?
                                        """, (app_id,))
                                    success_count += 1
                                except Exception as e:
                                    st.error(f"Error shortlisting ID {app_id}: {e}")
                            
                            update_conn.commit()
                            update_conn.close()
                            
                            if success_count > 0:
                                st.success(f"✅ {success_count} candidate(s) have been shortlisted successfully!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("No candidates were shortlisted. Please try again.")
            else:
                st.info("👆 Select candidates above to shortlist")
        else:
            st.info("No eligible candidates found matching your criteria")
    
    # ==================== TAB 2: BULK UPLOAD SHORTLIST ====================
    with tab2:
        st.subheader("📤 Bulk Upload Shortlist")
        st.info("Upload an Excel or CSV file containing candidate IDs to shortlist multiple candidates at once")
        
        conn = get_conn()
        if conn is None:
            st.error("Database connection failed")
            return
        
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # File upload option
        st.markdown("### 📁 Upload File")
        
        uploaded_file = st.file_uploader(
            "Choose Excel/CSV File",
            type=["xlsx", "xls", "csv"],
            key="bulk_shortlist_upload",
            help="File should contain ID numbers in a column"
        )
        
        # Store processing state
        if 'bulk_processed' not in st.session_state:
            st.session_state.bulk_processed = False
        if 'bulk_matched' not in st.session_state:
            st.session_state.bulk_matched = []
        if 'bulk_not_found' not in st.session_state:
            st.session_state.bulk_not_found = []
        
        if uploaded_file is not None:
            try:
                # Read the file
                if uploaded_file.name.endswith('.csv'):
                    bulk_df = pd.read_csv(uploaded_file)
                else:
                    bulk_df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ File loaded! {len(bulk_df)} rows found")
                
                with st.expander("Preview uploaded file"):
                    st.dataframe(bulk_df.head(10), use_container_width=True)
                
                # Column selection
                st.markdown("### 📋 Select ID Number Column")
                
                id_column = st.selectbox(
                    "Select the column containing ID Numbers",
                    list(bulk_df.columns),
                    key="bulk_id_column"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔍 Find Matching Candidates", use_container_width=True):
                        # Reset state
                        st.session_state.bulk_processed = True
                        st.session_state.bulk_matched = []
                        st.session_state.bulk_not_found = []
                        
                        # Process IDs
                        id_list = bulk_df[id_column].astype(str).str.strip().tolist()
                        id_list = list(dict.fromkeys(id_list))
                        
                        if conn:
                            cursor = conn.cursor()
                            
                            for id_num in id_list:
                                try:
                                    if is_cloud:
                                        cursor.execute("""
                                            SELECT id, name, id_number, contact, application_status 
                                            FROM staff 
                                            WHERE id_number = %s
                                        """, (id_num,))
                                    else:
                                        cursor.execute("""
                                            SELECT id, name, id_number, contact, application_status 
                                            FROM staff 
                                            WHERE id_number = ?
                                        """, (id_num,))
                                    
                                    result = cursor.fetchone()
                                    
                                    if result:
                                        if result[4] != 'Shortlisted' and result[4] != 'Hired':
                                            st.session_state.bulk_matched.append({
                                                'id': result[0],
                                                'name': result[1],
                                                'id_number': result[2],
                                                'contact': result[3],
                                                'current_status': result[4]
                                            })
                                        else:
                                            st.session_state.bulk_not_found.append(f"{id_num} (Already {result[4]})")
                                    else:
                                        st.session_state.bulk_not_found.append(f"{id_num} (Not found)")
                                except Exception as e:
                                    st.session_state.bulk_not_found.append(f"{id_num} (Error: {str(e)[:50]})")
                            
                            st.rerun()
                
                # Show results after processing
                if st.session_state.bulk_processed:
                    st.markdown("---")
                    st.subheader("📊 Results")
                    
                    if st.session_state.bulk_matched:
                        st.success(f"✅ Found {len(st.session_state.bulk_matched)} candidates to shortlist")
                        
                        matched_df = pd.DataFrame(st.session_state.bulk_matched)
                        st.dataframe(matched_df[['name', 'id_number', 'contact', 'current_status']], use_container_width=True)
                        
                        # Shortlist button
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            if st.button(f"⭐ SHORTLIST {len(st.session_state.bulk_matched)} CANDIDATES", use_container_width=True, type="primary"):
                                update_conn = get_conn()
                                if update_conn:
                                    update_cursor = update_conn.cursor()
                                    success_count = 0
                                    
                                    for candidate in st.session_state.bulk_matched:
                                        try:
                                            if is_cloud:
                                                update_cursor.execute("""
                                                    UPDATE staff 
                                                    SET application_status = 'Shortlisted',
                                                        shortlist_date = CURRENT_TIMESTAMP
                                                    WHERE id = %s
                                                """, (candidate['id'],))
                                            else:
                                                update_cursor.execute("""
                                                    UPDATE staff 
                                                    SET application_status = 'Shortlisted',
                                                        shortlist_date = CURRENT_TIMESTAMP
                                                    WHERE id = ?
                                                """, (candidate['id'],))
                                            success_count += 1
                                        except Exception as e:
                                            st.error(f"Error shortlisting {candidate['name']}: {e}")
                                    
                                    update_conn.commit()
                                    update_conn.close()
                                    
                                    if success_count > 0:
                                        st.success(f"✅ {success_count} candidates shortlisted successfully!")
                                        st.balloons()
                                        
                                        # Reset state and rerun
                                        st.session_state.bulk_processed = False
                                        st.session_state.bulk_matched = []
                                        st.session_state.bulk_not_found = []
                                        st.rerun()
                                    else:
                                        st.error("No candidates were shortlisted.")
                    else:
                        st.warning("No valid candidates found to shortlist")
                    
                    if st.session_state.bulk_not_found:
                        with st.expander(f"⚠️ {len(st.session_state.bulk_not_found)} IDs not found or already shortlisted"):
                            for item in st.session_state.bulk_not_found[:20]:
                                st.write(f"- {item}")
                    
                    if st.button("🔄 Clear & Start Over", use_container_width=True):
                        st.session_state.bulk_processed = False
                        st.session_state.bulk_matched = []
                        st.session_state.bulk_not_found = []
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        
        conn.close()
        
        st.markdown("---")
        st.markdown("### ✏️ Or Paste ID Numbers Manually")
        
        manual_ids = st.text_area(
            "Paste ID Numbers (one per line)",
            placeholder="12345678\n87654321\n34567890",
            height=120,
            key="manual_shortlist_ids"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📋 Process Manual IDs", use_container_width=True, type="primary"):
                if manual_ids.strip():
                    # Parse IDs
                    id_list = [id_num.strip() for id_num in manual_ids.replace(',', '\n').split('\n') if id_num.strip()]
                    
                    if not id_list:
                        st.warning("No valid ID numbers found.")
                    else:
                        # Create a new connection for this operation
                        manual_conn = get_conn()
                        if manual_conn:
                            manual_cursor = manual_conn.cursor()
                            is_cloud_manual = st.secrets.get("DATABASE_URL") is not None
                            matched = []
                            not_found = []
                            
                            # Find matching candidates
                            for id_num in id_list:
                                try:
                                    if is_cloud_manual:
                                        manual_cursor.execute("""
                                            SELECT id, name, id_number, contact, application_status 
                                            FROM staff 
                                            WHERE id_number = %s
                                        """, (id_num,))
                                    else:
                                        manual_cursor.execute("""
                                            SELECT id, name, id_number, contact, application_status 
                                            FROM staff 
                                            WHERE id_number = ?
                                        """, (id_num,))
                                    
                                    result = manual_cursor.fetchone()
                                    
                                    if result:
                                        if result[4] != 'Shortlisted' and result[4] != 'Hired':
                                            matched.append({
                                                'id': result[0],
                                                'name': result[1],
                                                'id_number': result[2],
                                                'contact': result[3],
                                                'current_status': result[4]
                                            })
                                        else:
                                            not_found.append(f"{id_num} - {result[1]} (Already {result[4]})")
                                    else:
                                        not_found.append(f"{id_num} (Not found)")
                                except Exception as e:
                                    not_found.append(f"{id_num} (Error: {str(e)[:50]})")
                            
                            # Display results
                            if matched:
                                st.success(f"✅ Found {len(matched)} candidate(s)")
                                
                                matched_df = pd.DataFrame(matched)
                                st.dataframe(matched_df[['name', 'id_number', 'contact', 'current_status']], use_container_width=True)
                                
                                # Shortlist button
                                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                                with col_btn2:
                                    if st.button(f"⭐ SHORTLIST THESE {len(matched)} CANDIDATES", use_container_width=True, type="primary"):
                                        success_count = 0
                                        
                                        for candidate in matched:
                                            try:
                                                if is_cloud_manual:
                                                    manual_cursor.execute("""
                                                        UPDATE staff 
                                                        SET application_status = 'Shortlisted',
                                                            shortlist_date = CURRENT_TIMESTAMP
                                                        WHERE id = %s
                                                    """, (candidate['id'],))
                                                else:
                                                    manual_cursor.execute("""
                                                        UPDATE staff 
                                                        SET application_status = 'Shortlisted',
                                                            shortlist_date = CURRENT_TIMESTAMP
                                                        WHERE id = ?
                                                    """, (candidate['id'],))
                                                success_count += 1
                                                st.success(f"✅ Shortlisted: {candidate['name']}")
                                            except Exception as e:
                                                st.error(f"Error shortlisting {candidate['name']}: {e}")
                                        
                                        # Commit the transaction
                                        manual_conn.commit()
                                        
                                        if success_count > 0:
                                            st.balloons()
                                            st.success(f"✅ {success_count} candidate(s) shortlisted successfully!")
                                            st.rerun()
                                        else:
                                            st.error("No candidates were shortlisted.")
                            else:
                                st.warning("No valid candidates found to shortlist")
                            
                            if not_found:
                                with st.expander(f"⚠️ {len(not_found)} IDs not found or already shortlisted"):
                                    for item in not_found:
                                        st.write(f"- {item}")
                            
                            manual_conn.close()
                else:
                    st.warning("Please paste ID numbers")
    
    # ==================== TAB 3: SHORTLISTED CANDIDATES ====================
    with tab3:
        st.subheader("📊 Shortlisted Candidates")
        
        conn = get_conn()
        if conn is None:
            st.error("Cannot connect to database")
            return
        
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Refresh button with cache clear
        col1, col2, col3 = st.columns([3, 1, 1])
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col3:
            if st.button("📊 Show All", use_container_width=True):
                st.rerun()
        
        st.markdown("---")
        
        try:
            # Force fresh query - no caching
            shortlisted_df = get_cached_shortlisted_candidates()
            
            # Debug - show count
            st.write(f"**Debug: Found {len(shortlisted_df)} shortlisted candidates in database**")
            
            if shortlisted_df.empty:
                st.info("No candidates have been shortlisted yet. Use the tabs above to shortlist candidates.")
            else:
                st.success(f"✅ Total Shortlisted Candidates: {len(shortlisted_df)}")
                
                # Display the dataframe
                st.dataframe(
                    shortlisted_df[['name', 'id_number', 'contact', 'qualifications', 'experience_years', 'subcounty']],
                    use_container_width=True,
                    height=400
                )
                
                # Export option
                csv = shortlisted_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Shortlist (CSV)",
                    csv,
                    f"shortlisted_candidates_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
                
        except Exception as e:
            st.error(f"Error loading shortlisted candidates: {str(e)}")
        finally:
            conn.close()
# =========================================================
# DATA QUALITY
# =========================================================
def data_quality():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">Data Quality Report</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Monitor data quality and completeness</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM staff", conn)
    conn.close()
    
    if df.empty:
        st.warning("No data available.")
        return
    
    st.subheader("📊 Data Completeness Score")
    
    # Calculate completeness for each column
    completeness = {}
    for col in df.columns:
        non_null = df[col].notna().sum()
        non_empty = (df[col] != "").sum() if col in df.select_dtypes(include=['object']).columns else non_null
        completeness[col] = (non_empty / len(df)) * 100
    
    completeness_df = pd.DataFrame({
        'Column': list(completeness.keys()),
        'Completeness (%)': list(completeness.values())
    }).sort_values('Completeness (%)', ascending=False)
    
    fig = px.bar(completeness_df, x='Column', y='Completeness (%)', 
                 title="Data Completeness by Field",
                 color='Completeness (%)',
                 color_continuous_scale='RdYlGn',
                 range_color=[0, 100])
    fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white')
    st.plotly_chart(fig, use_container_width=True)
    
    # Data issues
    st.subheader("⚠️ Data Quality Issues")
    
    issues = []
    
    # Check for missing names
    missing_names = df['name'].isna().sum() + (df['name'] == "").sum()
    if missing_names > 0:
        issues.append(f"❌ {missing_names} records missing staff names")
    
    # Check for missing ID numbers
    missing_ids = df['id_number'].isna().sum() + (df['id_number'] == "").sum()
    if missing_ids > 0:
        issues.append(f"❌ {missing_ids} records missing ID numbers")
    
    # Check for duplicate IDs
    duplicate_ids = df[df.duplicated('id_number', keep=False)]['id_number'].nunique()
    if duplicate_ids > 0:
        issues.append(f"⚠️ {duplicate_ids} duplicate ID numbers found")
    
    # Check for invalid years
    current_year = datetime.now().year
    invalid_years = df[(df['yob'] < 1950) | (df['yob'] > current_year)].shape[0]
    if invalid_years > 0:
        issues.append(f"⚠️ {invalid_years} records with invalid year of birth")
    
    # Check for invalid phone numbers
    if 'contact' in df.columns:
        invalid_phones = df[~df['contact'].str.match(r'^07\d{8}$', na=True)].shape[0]
        if invalid_phones > 0:
            issues.append(f"⚠️ {invalid_phones} records with invalid phone numbers (should be 07XXXXXXXX)")
    
    if issues:
        for issue in issues:
            st.warning(issue)
    else:
        st.success("✅ No data quality issues found!")
    
    # Recommendations
    st.subheader("💡 Recommendations")
    col1, col2 = st.columns(2)
    with col1:
        if completeness.get('qualifications', 0) < 80:
            st.info("📚 Consider adding qualification information for staff members")
        if completeness.get('contact', 0) < 80:
            st.info("📞 Consider adding contact information for better communication")
    with col2:
        if completeness.get('subcounty', 0) < 90:
            st.info("📍 Ensure sub-county information is complete for all staff")
        if completeness.get('experience', 0) < 70:
            st.info("💼 Encourage staff to add their experience details")

# =========================================================
# AUDIT TRAIL (Safe version - checks for column existence)
# =========================================================
def audit_trail():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">🔒 Audit Trail</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Comprehensive system activity tracking and user monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Restrict access to Super Admin only
    if st.session_state.user["role"] != "Super Admin":
        st.error("⛔ Access Denied. Super Admin privileges required.")
        return
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    try:
        # Get table columns to check what's available
        if is_cloud:
            columns_df = pd.read_sql("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'audit_log'
            """, conn)
            existing_columns = columns_df['column_name'].tolist()
        else:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(audit_log)")
            existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Get statistics (basic, always works)
        stats_df = pd.read_sql("""
            SELECT 
                COUNT(*) as total_audits,
                COUNT(DISTINCT username) as unique_users,
                MIN(timestamp) as first_activity,
                MAX(timestamp) as last_activity
            FROM audit_log
        """, conn)
        
        if not stats_df.empty and stats_df.iloc[0]['total_audits'] > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Activities", stats_df.iloc[0]['total_audits'])
            with col2:
                st.metric("Active Users", stats_df.iloc[0]['unique_users'])
            with col3:
                first_date = stats_df.iloc[0]['first_activity']
                st.metric("First Activity", str(first_date)[:10] if first_date else 'N/A')
            with col4:
                last_date = stats_df.iloc[0]['last_activity']
                st.metric("Last Activity", str(last_date)[:10] if last_date else 'N/A')
            
            st.markdown("---")
        
        # Status chart (only if status column exists)
        if 'status' in existing_columns:
            status_counts = pd.read_sql("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM audit_log
                GROUP BY status
                ORDER BY count DESC
            """, conn)
            
            if not status_counts.empty:
                st.subheader("📊 Activity Status Distribution")
                fig_status = px.pie(status_counts, values='count', names='status', 
                                    title="Success vs Failed Activities",
                                    color_discrete_sequence=['#10b981', '#ef4444', '#f59e0b'])
                fig_status.update_layout(height=350)
                st.plotly_chart(fig_status, use_container_width=True)
                st.markdown("---")
        else:
            st.info("💡 Tip: Add 'status' column to audit_log for better tracking")
        
        # Action counts chart (always works)
        action_counts = pd.read_sql("""
            SELECT 
                action,
                COUNT(*) as count
            FROM audit_log
            GROUP BY action
            ORDER BY count DESC
            LIMIT 8
        """, conn)
        
        if not action_counts.empty:
            st.subheader("📈 Most Common Actions")
            fig_action = px.bar(action_counts, x='action', y='count', 
                                title="Top Actions",
                                color='count',
                                color_continuous_scale='Blues')
            fig_action.update_layout(height=350)
            st.plotly_chart(fig_action, use_container_width=True)
            st.markdown("---")
        
        # Filters
        st.subheader("🔍 Filter Audit Log")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_filter = st.selectbox("Date Range", 
                ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
                key="audit_date_filter")
        
        with col2:
            actions = pd.read_sql("SELECT DISTINCT action FROM audit_log ORDER BY action", conn)
            action_list = ['All'] + actions['action'].tolist() if not actions.empty else ['All']
            selected_action = st.selectbox("Action Type", action_list, key="audit_action_filter")
        
        with col3:
            users = pd.read_sql("SELECT DISTINCT username FROM audit_log ORDER BY username", conn)
            user_list = ['All'] + users['username'].tolist() if not users.empty else ['All']
            selected_user = st.selectbox("User", user_list, key="audit_user_filter")
        
        # Build query
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if date_filter == "Last 7 Days":
            if is_cloud:
                query += " AND timestamp >= NOW() - INTERVAL '7 days'"
            else:
                query += " AND timestamp >= datetime('now', '-7 days')"
        elif date_filter == "Last 30 Days":
            if is_cloud:
                query += " AND timestamp >= NOW() - INTERVAL '30 days'"
            else:
                query += " AND timestamp >= datetime('now', '-30 days')"
        elif date_filter == "Last 90 Days":
            if is_cloud:
                query += " AND timestamp >= NOW() - INTERVAL '90 days'"
            else:
                query += " AND timestamp >= datetime('now', '-90 days')"
        
        if selected_action != "All":
            if is_cloud:
                query += " AND action = %s"
            else:
                query += " AND action = ?"
            params.append(selected_action)
        
        if selected_user != "All":
            if is_cloud:
                query += " AND username = %s"
            else:
                query += " AND username = ?"
            params.append(selected_user)
        
        query += " ORDER BY timestamp DESC LIMIT 500"
        
        if params:
            if is_cloud:
                audit_df = pd.read_sql(query, conn, params=tuple(params))
            else:
                audit_df = pd.read_sql(query, conn, params=tuple(params))
        else:
            audit_df = pd.read_sql(query, conn)
        
        # Display results
        st.markdown("---")
        st.subheader("📋 Audit Log Entries")
        st.caption(f"Showing {len(audit_df)} records")
        
        if not audit_df.empty:
            display_df = audit_df.copy()
            
            if 'timestamp' in display_df.columns:
                display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Select available columns
            display_columns = ['timestamp', 'username', 'action']
            if 'status' in display_df.columns:
                display_columns.append('status')
            if 'ip_address' in display_df.columns:
                display_columns.append('ip_address')
            display_columns.extend(['record_id', 'details'])
            
            available_cols = [col for col in display_columns if col in display_df.columns]
            display_df = display_df[available_cols]
            
            # Rename columns
            column_rename = {
                'timestamp': 'Timestamp',
                'username': 'User',
                'action': 'Action',
                'status': 'Status',
                'ip_address': 'IP Address',
                'record_id': 'Record ID',
                'details': 'Details'
            }
            display_df = display_df.rename(columns={k: v for k, v in column_rename.items() if k in display_df.columns})
            
            st.dataframe(display_df, use_container_width=True, height=500)
            
            csv = audit_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Audit Log (CSV)",
                csv,
                f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.info("No audit records found matching your criteria.")
            
    except Exception as e:
        st.error(f"Error loading audit trail: {str(e)}")
    
    conn.close()
# =========================================================
# HR DATA FUNCTIONS (Using main database)
# =========================================================

def load_employees():
    """Load employees from main database"""
    conn = get_conn()
    if conn is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql("SELECT * FROM employees ORDER BY name", conn)
        conn.close()
        return df
    except Exception as e:
        conn.close()
        return pd.DataFrame()

def insert_employee(data):
    """Insert employee into main database"""
    conn = get_conn()
    if conn is None:
        return False
    
    cursor = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    try:
        if is_cloud:
            cursor.execute("""
                INSERT INTO employees (
                    staff_no, name, personal_no, age, department,
                    first_appointment_date, first_appointment_designation,
                    current_designation, current_job_group,
                    academic_qualifications, professional_qualifications,
                    discipline_history, chrmc_approval_date, cpsb_approval_date,
                    created_at, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            """, data + (st.session_state.user['username'],))
        else:
            cursor.execute("""
                INSERT INTO employees (
                    staff_no, name, personal_no, age, department,
                    first_appointment_date, first_appointment_designation,
                    current_designation, current_job_group,
                    academic_qualifications, professional_qualifications,
                    discipline_history, chrmc_approval_date, cpsb_approval_date,
                    created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data + (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.user['username']))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error inserting employee: {e}")
        conn.close()
        return False

def update_employee(staff_no, column, value):
    """Update employee field"""
    conn = get_conn()
    cursor = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    if is_cloud:
        cursor.execute(f"UPDATE employees SET {column} = %s WHERE staff_no = %s", (value, staff_no))
    else:
        cursor.execute(f"UPDATE employees SET {column} = ? WHERE staff_no = ?", (value, staff_no))
    
    conn.commit()
    conn.close()

def delete_employee(staff_no):
    """Delete employee"""
    conn = get_conn()
    cursor = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    if is_cloud:
        cursor.execute("DELETE FROM employees WHERE staff_no = %s", (staff_no,))
    else:
        cursor.execute("DELETE FROM employees WHERE staff_no = ?", (staff_no,))
    
    conn.commit()
    conn.close()
# =========================================================
# BACKUP & RESTORE (PostgreSQL Compatible)
# =========================================================
def backup_restore():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">Backup & Restore</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Database backup and recovery tools</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.user["role"] != "Admin":
        st.error("⛔ Access Denied. Admin privileges required.")
        return
    
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Backup Database")
        st.info("Export your database to CSV/Excel format")
        
        backup_format = st.selectbox("Backup Format", ["CSV", "Excel", "SQL Dump"], key="backup_format")
        
        if st.button("Create Backup", use_container_width=True):
            if is_cloud:
                # For PostgreSQL - Export to CSV
                conn = get_conn()
                
                # Get list of all tables
                tables = ['employees', 'staff', 'hr_promotions', 'hr_discipline', 
                         'hr_unpaid_leave', 'hr_confirmation', 'hr_redesignation',
                         'hr_translation', 'hr_salary_harmonization', 'employee_contracts',
                         'users', 'audit_log']
                
                if backup_format == "CSV":
                    # Create a zip file with all CSV exports
                    import zipfile
                    from io import BytesIO
                    
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for table in tables:
                            try:
                                df = pd.read_sql(f"SELECT * FROM {table}", conn)
                                if not df.empty:
                                    csv_data = df.to_csv(index=False).encode('utf-8')
                                    zip_file.writestr(f"{table}_backup_{datetime.now().strftime('%Y%m%d')}.csv", csv_data)
                            except Exception as e:
                                st.warning(f"Could not backup {table}: {e}")
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        "⬇️ Download Backup (ZIP)",
                        zip_buffer,
                        f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        "application/zip",
                        use_container_width=True
                    )
                    st.success("Backup created successfully!")
                    
                elif backup_format == "Excel":
                    # Create Excel file with multiple sheets
                    from io import BytesIO
                    output = BytesIO()
                    
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for table in tables:
                            try:
                                df = pd.read_sql(f"SELECT * FROM {table}", conn)
                                if not df.empty:
                                    sheet_name = table[:31]  # Excel sheet name limit
                                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                            except Exception as e:
                                st.warning(f"Could not backup {table}: {e}")
                    
                    output.seek(0)
                    st.download_button(
                        "⬇️ Download Backup (Excel)",
                        output,
                        f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    st.success("Backup created successfully!")
                    
                else:  # SQL Dump
                    st.info("SQL Dump is available via Neon Dashboard")
                    st.markdown("""
                    To create a full SQL dump:
                    1. Go to your **Neon Dashboard**
                    2. Click on your project
                    3. Go to **"Backups"** tab
                    4. Click **"Create backup"**
                    """)
                
                conn.close()
                
            else:
                # For SQLite - Simple file backup
                backup_file = f"backup_ecde_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy("ecde.db", backup_file)
                with open(backup_file, "rb") as f:
                    st.download_button("⬇️ Download Backup", f, backup_file, use_container_width=True)
                st.success("Backup created successfully!")
            
            log_audit(st.session_state.user['username'], "BACKUP", 0, "Database backup created", "Success")
    
    with col2:
        st.subheader("🔄 Restore Database")
        st.warning("⚠️ Restoring will overwrite current data!")
        
        if is_cloud:
            st.info("""
            **For PostgreSQL (Cloud):**
            - Restore from Neon Dashboard
            - Or use the backup files above to manually re-import
            
            **Steps to restore:**
            1. Download your backup file
            2. Go to Neon Dashboard
            3. Use the import feature or
            4. Manually re-upload data using Import Staff feature
            """)
            
            if st.button("📊 View Backup History", use_container_width=True):
                # Show backup history from audit log
                conn = get_conn()
                backup_logs = pd.read_sql("""
                    SELECT timestamp, details 
                    FROM audit_log 
                    WHERE action = 'BACKUP' 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """, conn)
                conn.close()
                
                if not backup_logs.empty:
                    st.dataframe(backup_logs, use_container_width=True)
                else:
                    st.info("No backup history found")
        else:
            # For SQLite - File restore
            uploaded_file = st.file_uploader("Choose backup file", type=["db"])
            if uploaded_file and st.button("Restore Database", use_container_width=True):
                confirm = st.checkbox("Confirm: I understand this will overwrite ALL current data")
                if confirm:
                    with open("ecde.db", "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    log_audit(st.session_state.user['username'], "RESTORE", 0, "Restored database from backup", "Success")
                    st.success("Database restored successfully! Please restart the app.")
                    st.rerun()
                else:
                    st.warning("Please confirm to restore database")

# =========================================================
# SETTINGS MANAGEMENT SYSTEM
# =========================================================

# Create settings tables in init_db() - ADD THESE TO YOUR EXISTING init_db()
def create_settings_tables():
    """Create additional tables for settings management - SAFE for both DBs"""
    conn = get_conn()
    if conn is None:
        return
    
    c = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    if is_cloud:
        # PostgreSQL syntax
        c.execute("""
        CREATE TABLE IF NOT EXISTS dropdown_options (
            id SERIAL PRIMARY KEY,
            category TEXT,
            option_value TEXT,
            option_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS advertised_positions (
            id SERIAL PRIMARY KEY,
            position_title TEXT,
            position_code TEXT,
            department TEXT,
            employment_type TEXT,
            vacancies INTEGER,
            requirements TEXT,
            responsibilities TEXT,
            salary_range TEXT,
            application_deadline TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS recruitment_rounds (
            id SERIAL PRIMARY KEY,
            round_name TEXT,
            start_date TEXT,
            end_date TEXT,
            positions_available TEXT,
            status TEXT DEFAULT 'Upcoming',
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelists (
            id SERIAL PRIMARY KEY,
            name TEXT,
            role TEXT,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
    else:
        # SQLite syntax
        c.execute("""
        CREATE TABLE IF NOT EXISTS dropdown_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            option_value TEXT,
            option_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS advertised_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_title TEXT,
            position_code TEXT,
            department TEXT,
            employment_type TEXT,
            vacancies INTEGER,
            requirements TEXT,
            responsibilities TEXT,
            salary_range TEXT,
            application_deadline TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS recruitment_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_name TEXT,
            start_date TEXT,
            end_date TEXT,
            positions_available TEXT,
            status TEXT DEFAULT 'Upcoming',
            created_at TEXT,
            created_by TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
    
    conn.commit()
    conn.close()
# =========================================================
# SYSTEM SETTINGS (COMPLETE WITH ALL FEATURES)
# =========================================================
# =========================================================
# SYSTEM SETTINGS (COMPLETE WITH ALL FEATURES + BULK IMPORT)
# =========================================================
def system_settings():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">⚙️ System Settings</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Manage dropdown options, board members, scoring criteria, positions, and system preferences</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.user["role"] != "Admin":
        st.error("⛔ Access Denied. Admin privileges required.")
        return
    
    # Create tabs - ADDED TAB 8 for Bulk Import
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📋 Dropdown Options",
        "👥 Board Members",
        "📊 Scoring Criteria",
        "🎯 Scoring Parameters",
        "📢 Advertised Positions",
        "🔄 Recruitment Rounds",
        "⚙️ General Settings",
        "📥 Bulk Import Positions"  # NEW TAB
    ])
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # ==================== TAB 1: DROPDOWN OPTIONS ====================
    with tab1:
        st.subheader("📋 Manage Dropdown Options")
        st.info("Add, edit, or remove options that appear in dropdown menus throughout the system")
        
        # Select category to manage
        categories = ["Ethnicity", "Disability", "KCSE_Grade", "Qualification", "SubCounty", "Ward", "EmploymentType", "SourceOfInfo"]
        selected_category = st.selectbox("Select Category to Manage", categories)
        
        if selected_category:
            # Display current options - FIXED: Use parameterized query for PostgreSQL
            try:
                if is_cloud:
                    # PostgreSQL - use parameterized query with %s
                    query = "SELECT id, option_value, option_order, is_active FROM dropdown_options WHERE category = %s ORDER BY option_order"
                    options_df = pd.read_sql(query, conn, params=(selected_category,))
                else:
                    # SQLite - use ? placeholder
                    query = "SELECT id, option_value, option_order, is_active FROM dropdown_options WHERE category = ? ORDER BY option_order"
                    options_df = pd.read_sql(query, conn, params=(selected_category,))
                
                if not options_df.empty:
                    st.write(f"**Current {selected_category} Options:**")
                    
                    # Editable dataframe
                    edited_df = st.data_editor(
                        options_df[['option_value', 'option_order', 'is_active']],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"editor_{selected_category}"
                    )
                    
                    # Save changes button
                    if st.button(f"💾 Save {selected_category} Changes", use_container_width=True):
                        cursor = conn.cursor()
                        
                        # Clear existing options - FIXED: Use parameterized query
                        if is_cloud:
                            cursor.execute("DELETE FROM dropdown_options WHERE category = %s", (selected_category,))
                        else:
                            cursor.execute("DELETE FROM dropdown_options WHERE category = ?", (selected_category,))
                        
                        # Insert updated options
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        username = st.session_state.user['username']
                        
                        for idx, row in edited_df.iterrows():
                            if row['option_value'] and row['option_value'] != "":
                                if is_cloud:
                                    cursor.execute("""
                                        INSERT INTO dropdown_options (category, option_value, option_order, is_active, created_at, created_by)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """, (selected_category, row['option_value'], row['option_order'], row['is_active'], now, username))
                                else:
                                    cursor.execute("""
                                        INSERT INTO dropdown_options (category, option_value, option_order, is_active, created_at, created_by)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (selected_category, row['option_value'], row['option_order'], row['is_active'], now, username))
                        
                        conn.commit()
                        st.success(f"{selected_category} options updated successfully!")
                        st.rerun()
                else:
                    st.info(f"No options found for {selected_category}")
                    
            except Exception as e:
                st.error(f"Error loading options: {str(e)}")
        # ==================== TAB 2: BOARD MEMBERS ====================
    with tab2:
        st.subheader("👥 Manage Board Members / Panelists")
        st.info("Add, edit, or remove panelists who will score candidates during interviews")
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Initialize panelists table if not exists
        if is_cloud:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS panelists (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    role TEXT,
                    email TEXT,
                    phone TEXT,
                    is_active INTEGER DEFAULT 1,
                    display_order INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS panelists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    role TEXT,
                    email TEXT,
                    phone TEXT,
                    is_active INTEGER DEFAULT 1,
                    display_order INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
        
        # Force update board members (delete old, insert new)
        cursor.execute("DELETE FROM panelists")
        
        # Insert default board members
        default_panelists = [
            ('Jim Nyaga Njoka, MBS', 'Chairman CPSB', 'jim.mnjoka50@gmail.com', '0720 651 158', 1, 1),
            ('Wilson Gitonga Ireri', 'Secretary/CEO CPSB', 'wilsongireri@gmail.com', '0722 167 074', 1, 2),
            ('Joyce Thaara Njeru', 'Board Member CPSB', 'njerujoyce596@gmail.com', '0720 499 289', 1, 3),
            ('Godfrey Joseph Nyaga Njuki', 'Board Member CPSB', 'njuki.nyaga0@gmail.com', '0721 582 096', 1, 4),
            ('Agnes Mukami Muriuki', 'Board Member CPSB', 'agnesmuriuki1@gmail.com', '0719 395 839', 1, 5),
            ('Samuel Musyoke Wambua', 'Board Member CPSB', 'musyoke@gmail.com', '0729 048 407', 1, 6),
            ('Salesio Njoka Kiriga', 'Board Member CPSB', 'salesionjoka73@gmail.com', '0726 967 607', 1, 7)
        ]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for name, role, email, phone, active, order in default_panelists:
            if is_cloud:
                cursor.execute('''
                    INSERT INTO panelists (name, role, email, phone, is_active, display_order, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (name, role, email, phone, active, order, now))
            else:
                cursor.execute('''
                    INSERT INTO panelists (name, role, email, phone, is_active, display_order, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, role, email, phone, active, order, now))
        
        conn.commit()
        st.info(f"✅ Added {len(default_panelists)} default board members")
        
        # Display existing panelists
        panelists_df = pd.read_sql("SELECT id, name, role, is_active, display_order FROM panelists ORDER BY display_order, id", conn)
        
        st.markdown("### Current Panelists")
        
        if not panelists_df.empty:
            edited_panelists = st.data_editor(
                panelists_df[['name', 'role', 'is_active', 'display_order']],
                use_container_width=True,
                num_rows="dynamic",
                key="panelist_editor"
            )
            
            if st.button("💾 Save Panelist Changes", use_container_width=True):
                # Clear existing
                if is_cloud:
                    cursor.execute("DELETE FROM panelists")
                else:
                    cursor.execute("DELETE FROM panelists")
                
                # Insert updated
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for idx, row in edited_panelists.iterrows():
                    if row['name'] and row['name'].strip():
                        if is_cloud:
                            cursor.execute("""
                                INSERT INTO panelists (name, role, is_active, display_order, created_at)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (row['name'], row['role'], row['is_active'], row['display_order'], now))
                        else:
                            cursor.execute("""
                                INSERT INTO panelists (name, role, is_active, display_order, created_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (row['name'], row['role'], row['is_active'], row['display_order'], now))
                conn.commit()
                st.success("✅ Panelists updated successfully!")
                st.rerun()
        else:
            st.info("No panelists found. Add panelists below.")
    
    # ==================== TAB 3: SCORING CRITERIA ====================
    with tab3:
        st.subheader("📊 Manage Scoring Criteria")
        st.info("Set maximum scores for each evaluation criterion used in the scoresheet")
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Initialize criteria table if not exists
        try:
            if is_cloud:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scoring_criteria (
                        id SERIAL PRIMARY KEY,
                        criteria_key TEXT UNIQUE,
                        criteria_name TEXT,
                        max_score INTEGER,
                        description TEXT,
                        is_active INTEGER DEFAULT 1
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scoring_criteria (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        criteria_key TEXT UNIQUE,
                        criteria_name TEXT,
                        max_score INTEGER,
                        description TEXT,
                        is_active INTEGER DEFAULT 1
                    )
                """)
            conn.commit()
        except Exception as e:
            st.error(f"Error creating table: {e}")
        
        # Check if criteria exist, if not, insert defaults
        try:
            cursor.execute("SELECT COUNT(*) FROM scoring_criteria")
            count_row = cursor.fetchone()
            if count_row and count_row[0] == 0:
                default_criteria = [
                    ("academic", "Academic and Professional Qualifications", 10, "Degree, Certificate, Form Four, Computer skills", 1),
                    ("hr_knowledge", "Knowledge on Human Resource Management", 15, "Understanding of HR principles and practices", 1),
                    ("procurement", "Knowledge of Public Finance/Procurement", 15, "Understanding of PPADA and public finance", 1),
                    ("gov_structure", "Government Structure & Organization Functions", 10, "Knowledge of county and national government", 1),
                    ("leadership", "Strategic Leadership Capability & Potential", 15, "Leadership qualities and strategic thinking", 1),
                    ("communication", "Communication Skills", 5, "Verbal and written communication abilities", 1),
                    ("general_knowledge", "General Knowledge (National, Regional & Global)", 10, "Awareness of current affairs", 1),
                    ("technical", "Knowledge/Experience in Technical Area", 20, "Specialized expertise for the position", 1)
                ]
                for criteria in default_criteria:
                    if is_cloud:
                        cursor.execute("""
                            INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
                            VALUES (%s, %s, %s, %s, %s)
                        """, criteria)
                    else:
                        cursor.execute("""
                            INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
                            VALUES (?, ?, ?, ?, ?)
                        """, criteria)
                conn.commit()
                st.success("✅ Default scoring criteria added")
        except Exception as e:
            st.warning(f"Could not check/add criteria: {e}")
        
        # Get current criteria
        try:
            criteria_df = pd.read_sql("SELECT id, criteria_key, criteria_name, max_score, description, is_active FROM scoring_criteria ORDER BY id", conn)
            
            if not criteria_df.empty:
                st.markdown("### Scoring Criteria Configuration")
                
                edited_criteria = st.data_editor(
                    criteria_df[['criteria_name', 'max_score', 'description', 'is_active']],
                    use_container_width=True,
                    key="criteria_editor"
                )
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button("💾 Save Criteria Changes", use_container_width=True):
                        for idx, row in edited_criteria.iterrows():
                            criteria_id = criteria_df.iloc[idx]['id']
                            if is_cloud:
                                cursor.execute("""
                                    UPDATE scoring_criteria 
                                    SET criteria_name = %s, max_score = %s, description = %s, is_active = %s
                                    WHERE id = %s
                                """, (row['criteria_name'], row['max_score'], row['description'], row['is_active'], criteria_id))
                            else:
                                cursor.execute("""
                                    UPDATE scoring_criteria 
                                    SET criteria_name = ?, max_score = ?, description = ?, is_active = ?
                                    WHERE id = ?
                                """, (row['criteria_name'], row['max_score'], row['description'], row['is_active'], criteria_id))
                        conn.commit()
                        st.success("✅ Scoring criteria updated successfully!")
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Reset to Default", use_container_width=True):
                        # Delete all
                        if is_cloud:
                            cursor.execute("DELETE FROM scoring_criteria")
                        else:
                            cursor.execute("DELETE FROM scoring_criteria")
                        
                        # Re-insert defaults
                        default_criteria = [
                            ("academic", "Academic and Professional Qualifications", 10, "Degree, Certificate, Form Four, Computer skills", 1),
                            ("hr_knowledge", "Knowledge on Human Resource Management", 15, "Understanding of HR principles and practices", 1),
                            ("procurement", "Knowledge of Public Finance/Procurement", 15, "Understanding of PPADA and public finance", 1),
                            ("gov_structure", "Government Structure & Organization Functions", 10, "Knowledge of county and national government", 1),
                            ("leadership", "Strategic Leadership Capability & Potential", 15, "Leadership qualities and strategic thinking", 1),
                            ("communication", "Communication Skills", 5, "Verbal and written communication abilities", 1),
                            ("general_knowledge", "General Knowledge (National, Regional & Global)", 10, "Awareness of current affairs", 1),
                            ("technical", "Knowledge/Experience in Technical Area", 20, "Specialized expertise for the position", 1)
                        ]
                        for criteria in default_criteria:
                            if is_cloud:
                                cursor.execute("""
                                    INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, criteria)
                            else:
                                cursor.execute("""
                                    INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
                                    VALUES (?, ?, ?, ?, ?)
                                """, criteria)
                        conn.commit()
                        st.success("✅ Scoring criteria reset to defaults!")
                        st.rerun()
                
                total_max = criteria_df['max_score'].sum()
                st.info(f"📊 **Total Possible Score: {total_max} points**")
            else:
                st.warning("No scoring criteria found. Please refresh the page.")
        except Exception as e:
            st.error(f"Error loading criteria: {e}")
    
    # ==================== TAB 4: SCORING PARAMETERS ====================
    with tab4:
        st.subheader("🎯 Scoring Parameters")
        st.info("Configure scoring thresholds and requirements")
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Initialize parameters table
        if is_cloud:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scoring_parameters (
                    id SERIAL PRIMARY KEY,
                    param_key TEXT UNIQUE,
                    param_name TEXT,
                    param_value TEXT,
                    description TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scoring_parameters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    param_key TEXT UNIQUE,
                    param_name TEXT,
                    param_value TEXT,
                    description TEXT
                )
            """)
        
        # Check if parameters exist
        cursor.execute("SELECT COUNT(*) FROM scoring_parameters")
        if cursor.fetchone()[0] == 0:
            default_params = [
                ("pass_mark", "Passing Score", "70", "Minimum score required to be considered for hiring"),
                ("distinction_mark", "Distinction Score", "85", "Score for exceptional performance"),
                ("interview_weight", "Interview Weight (%)", "70", "Weight of interview score in final calculation"),
                ("criteria_weight", "Criteria Weight (%)", "30", "Weight of criteria score in final calculation"),
                ("max_panelists", "Maximum Panelists", "8", "Number of panelists expected to score"),
                ("min_panelists_required", "Minimum Panelists Required", "5", "Minimum panelists needed for valid score"),
                ("shortlist_score", "Auto-Shortlist Score", "70", "Score above which candidates are auto-shortlisted"),
                ("reject_score", "Auto-Reject Score", "40", "Score below which candidates are auto-rejected")
            ]
            for param in default_params:
                if is_cloud:
                    cursor.execute("""
                        INSERT INTO scoring_parameters (param_key, param_name, param_value, description)
                        VALUES (%s, %s, %s, %s)
                    """, param)
                else:
                    cursor.execute("""
                        INSERT INTO scoring_parameters (param_key, param_name, param_value, description)
                        VALUES (?, ?, ?, ?)
                    """, param)
            conn.commit()
        
        # Get parameters
        params_df = pd.read_sql("SELECT param_key, param_name, param_value, description FROM scoring_parameters ORDER BY param_name", conn)
        
        st.markdown("### Configure Parameters")
        
        for idx, row in params_df.iterrows():
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**{row['param_name']}**")
                st.caption(row['description'])
            with col2:
                new_value = st.text_input(
                    "Value",
                    value=row['param_value'],
                    key=f"param_{row['param_key']}",
                    label_visibility="collapsed"
                )
                if new_value != row['param_value']:
                    if is_cloud:
                        cursor.execute("""
                            UPDATE scoring_parameters 
                            SET param_value = %s 
                            WHERE param_key = %s
                        """, (new_value, row['param_key']))
                    else:
                        cursor.execute("""
                            UPDATE scoring_parameters 
                            SET param_value = ? 
                            WHERE param_key = ?
                        """, (new_value, row['param_key']))
                    conn.commit()
        
        if st.button("💾 Save All Parameters", use_container_width=True):
            st.success("✅ Parameters saved successfully!")
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Scoring Levels Interpretation")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            cursor.execute("SELECT param_value FROM scoring_parameters WHERE param_key = 'pass_mark'")
            pass_mark = cursor.fetchone()
            st.info(f"✅ **Passing Score:** {pass_mark[0] if pass_mark else '70'}% and above")
        with col2:
            cursor.execute("SELECT param_value FROM scoring_parameters WHERE param_key = 'distinction_mark'")
            distinction = cursor.fetchone()
            st.success(f"🏆 **Distinction:** {distinction[0] if distinction else '85'}% and above")
        with col3:
            cursor.execute("SELECT param_value FROM scoring_parameters WHERE param_key = 'reject_score'")
            reject = cursor.fetchone()
            st.error(f"❌ **Auto-Reject:** Below {reject[0] if reject else '40'}%")
    
    # ==================== TAB 5: ADVERTISED POSITIONS ====================
    with tab5:
        st.subheader("📢 Manage Advertised Positions")
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Form to add new position
        with st.expander("➕ Post New Position", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                position_title = st.text_input("Position Title*", placeholder="e.g., ECDE Teacher")
                position_code = st.text_input("Position Code", placeholder="e.g., ECDE/2024/01")
                department = st.text_input("Department", placeholder="e.g., Early Childhood Education")
                employment_type = st.selectbox("Employment Type", ["Permanent", "Contract", "Temporary", "Part-time", "Internship"])
                vacancies = st.number_input("Number of Vacancies", min_value=1, max_value=100, value=1)
                
            with col2:
                salary_range = st.text_input("Salary Range", placeholder="e.g., KES 30,000 - 50,000")
                application_deadline = st.date_input("Application Deadline")
                status = st.selectbox("Position Status", ["Open", "Closed", "On Hold"])
            
            requirements = st.text_area("Requirements", placeholder="List all requirements for this position...", height=100)
            responsibilities = st.text_area("Responsibilities", placeholder="List key responsibilities...", height=100)
            
            if st.button("📢 Post Position", use_container_width=True):
                if position_title:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if is_cloud:
                        cursor.execute("""
                            INSERT INTO advertised_positions (
                                position_title, position_code, department, employment_type, vacancies,
                                requirements, responsibilities, salary_range, application_deadline, status,
                                created_at, created_by
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            position_title, position_code, department, employment_type, vacancies,
                            requirements, responsibilities, salary_range, application_deadline.strftime("%Y-%m-%d"),
                            status, now, st.session_state.user['username']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO advertised_positions (
                                position_title, position_code, department, employment_type, vacancies,
                                requirements, responsibilities, salary_range, application_deadline, status,
                                created_at, created_by
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            position_title, position_code, department, employment_type, vacancies,
                            requirements, responsibilities, salary_range, application_deadline.strftime("%Y-%m-%d"),
                            status, now, st.session_state.user['username']
                        ))
                    conn.commit()
                    st.success(f"Position '{position_title}' posted successfully!")
                    st.rerun()
                else:
                    st.error("Position Title is required")
        
        # Display existing positions
        st.markdown("---")
        st.write("**Currently Advertised Positions**")
        
        # Add a master refresh button
        col_refresh1, col_refresh2, col_refresh3 = st.columns([3, 1, 1])
        with col_refresh2:
            if st.button("🔄 Refresh Page", use_container_width=True):
                st.rerun()
        with col_refresh3:
            if st.button("📊 Show Stats", use_container_width=True):
                try:
                    stats = pd.read_sql("SELECT status, COUNT(*) as count FROM advertised_positions GROUP BY status", conn)
                    st.dataframe(stats, use_container_width=True)
                except Exception as e:
                    st.error(f"Error loading stats: {e}")
        
        st.markdown("---")
        
        # Fetch and display positions
        try:
            positions_df = pd.read_sql("SELECT * FROM advertised_positions ORDER BY id DESC", conn)
        except Exception as e:
            st.error(f"Error loading positions: {e}")
            positions_df = pd.DataFrame()
        
        if not positions_df.empty:
            for idx, position in positions_df.iterrows():
                with st.expander(f"📌 {position['position_title']} - {position['status']} (Vacancies: {position['vacancies']})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Position Code:** {position['position_code']}")
                        st.write(f"**Department:** {position['department']}")
                        st.write(f"**Employment Type:** {position['employment_type']}")
                        st.write(f"**Salary Range:** {position['salary_range']}")
                    with col2:
                        st.write(f"**Application Deadline:** {position['application_deadline']}")
                        st.write(f"**Posted By:** {position['created_by']}")
                        st.write(f"**Posted On:** {position['created_at']}")
                    
                    st.write("**Requirements:**")
                    st.write(position['requirements'] if position['requirements'] else "Not specified")
                    st.write("**Responsibilities:**")
                    st.write(position['responsibilities'] if position['responsibilities'] else "Not specified")
                    
                    # Auto-save status - NO UPDATE BUTTON NEEDED
                    status_options = ["Open", "Closed", "On Hold"]
                    current_index = status_options.index(position['status']) if position['status'] in status_options else 0
                    new_status = st.selectbox("Status", status_options, key=f"status_{position['id']}", index=current_index)
                    
                    # Auto-save when selection changes
                    if new_status != position['status']:
                        if is_cloud:
                            cursor.execute("UPDATE advertised_positions SET status = %s WHERE id = %s", (new_status, position['id']))
                        else:
                            cursor.execute("UPDATE advertised_positions SET status = ? WHERE id = ?", (new_status, position['id']))
                        conn.commit()
                        st.success(f"✅ Status changed to {new_status}")
                        st.rerun()
                    
                    # Delete button
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col3:
                        if st.button(f"🗑️ Delete", key=f"delete_{position['id']}"):
                            if is_cloud:
                                cursor.execute("DELETE FROM advertised_positions WHERE id = %s", (position['id'],))
                            else:
                                cursor.execute("DELETE FROM advertised_positions WHERE id = ?", (position['id'],))
                            conn.commit()
                            st.warning(f"Position '{position['position_title']}' deleted!")
                            st.rerun()
        else:
            st.info("No advertised positions yet. Use the form above to add positions or use Bulk Import.")
    
    # ==================== TAB 6: RECRUITMENT ROUNDS ====================
    with tab6:
        st.subheader("🔄 Manage Recruitment Rounds")
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Add new recruitment round
        with st.expander("➕ Create New Recruitment Round", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                round_name = st.text_input("Round Name", placeholder="e.g., 2024 ECDE Teacher Recruitment")
                start_date = st.date_input("Start Date")
            with col2:
                end_date = st.date_input("End Date")
                round_status = st.selectbox("Status", ["Upcoming", "Active", "Closed", "Completed"])
            
            if st.button("Create Recruitment Round", use_container_width=True):
                if round_name:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if is_cloud:
                        cursor.execute("""
                            INSERT INTO recruitment_rounds (round_name, start_date, end_date, status, created_at, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            round_name, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"),
                            round_status, now, st.session_state.user['username']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO recruitment_rounds (round_name, start_date, end_date, status, created_at, created_by)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            round_name, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"),
                            round_status, now, st.session_state.user['username']
                        ))
                    conn.commit()
                    st.success(f"Recruitment round '{round_name}' created!")
                    st.rerun()
                else:
                    st.error("Round name is required")
        
        # Display existing rounds
        st.markdown("---")
        st.write("**Recruitment Rounds**")
        
        rounds_df = pd.read_sql("SELECT * FROM recruitment_rounds ORDER BY id DESC", conn)
        
        if not rounds_df.empty:
            for idx, round_item in rounds_df.iterrows():
                with st.expander(f"🔄 {round_item['round_name']} - {round_item['status']} ({round_item['start_date']} to {round_item['end_date']})"):
                    st.write(f"**Created By:** {round_item['created_by']}")
                    st.write(f"**Created On:** {round_item['created_at']}")
                    
                    new_round_status = st.selectbox("Update Round Status", ["Upcoming", "Active", "Closed", "Completed"], key=f"round_status_{round_item['id']}", index=["Upcoming", "Active", "Closed", "Completed"].index(round_item['status']))
                    if st.button(f"Update Round Status", key=f"update_round_{round_item['id']}"):
                        if is_cloud:
                            cursor.execute("UPDATE recruitment_rounds SET status = %s WHERE id = %s", (new_round_status, round_item['id']))
                        else:
                            cursor.execute("UPDATE recruitment_rounds SET status = ? WHERE id = ?", (new_round_status, round_item['id']))
                        conn.commit()
                        st.success(f"Round status updated to {new_round_status}")
                        st.rerun()
                    
                    if st.button(f"🗑️ Delete Round", key=f"delete_round_{round_item['id']}"):
                        if is_cloud:
                            cursor.execute("DELETE FROM recruitment_rounds WHERE id = %s", (round_item['id'],))
                        else:
                            cursor.execute("DELETE FROM recruitment_rounds WHERE id = ?", (round_item['id'],))
                        conn.commit()
                        st.rerun()
        else:
            st.info("No recruitment rounds created yet.")
    
    # ==================== TAB 7: GENERAL SETTINGS ====================
    with tab7:
        st.subheader("⚙️ General System Settings")
        st.info("Configure system-wide preferences")
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # System Preferences
        st.markdown("### 🎨 System Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            theme = st.selectbox("Dashboard Theme", ["Light", "Dark", "Auto"])
            items_per_page = st.number_input("Records Per Page", min_value=10, max_value=200, value=50, step=10)
            date_format = st.selectbox("Date Format", ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"])
        
        with col2:
            dashboard_period = st.selectbox("Default Dashboard Period", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"])
            email_notifications = st.checkbox("Enable Email Notifications", value=True)
            if email_notifications:
                admin_email = st.text_input("Admin Email Address", placeholder="admin@ecde.go.ke")
        
        st.markdown("---")
        
        # Recruitment Settings
        st.markdown("### 📋 Recruitment Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            default_status = st.selectbox("Default Application Status", ["Pending", "Received", "Under Review"])
            deadline_buffer = st.number_input("Days Before Deadline Reminder", min_value=1, max_value=30, value=7)
        
        with col2:
            pass_mark = st.number_input("Interview Pass Mark (%)", min_value=50, max_value=90, value=70, step=5)
            max_applications = st.number_input("Max Applications Per Position", min_value=100, max_value=5000, value=1000, step=100)
        
        st.markdown("---")
        
        # Data Management
        st.markdown("### 🗄️ Data Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            auto_delete = st.checkbox("Auto-delete Old Applications", value=False)
            if auto_delete:
                retention_days = st.number_input("Retention Period (Days)", min_value=30, max_value=730, value=365)
        
        with col2:
            auto_backup = st.checkbox("Auto-backup Database", value=True)
            if auto_backup:
                backup_frequency = st.selectbox("Backup Frequency", ["Daily", "Weekly", "Monthly"])
        
        st.markdown("---")
        
        # Save Settings Button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 Save All Settings", use_container_width=True, type="primary"):
                st.success("✅ Settings saved successfully!")
                st.balloons()
                log_audit(st.session_state.user['username'], "SETTINGS_UPDATE", 0, "System settings updated", "Success")
        
        # System Information
        st.markdown("---")
        st.markdown("### ℹ️ System Information")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("System Version", "2.0.0")
        with col2:
            st.metric("Last Backup", "Not configured")
        with col3:
            try:
                cursor.execute("SELECT COUNT(*) FROM staff")
                total = cursor.fetchone()[0]
                st.metric("Database Records", f"{total:,}")
            except:
                st.metric("Database Records", "0")
    
    # ==================== TAB 8: BULK IMPORT POSITIONS ====================
    with tab8:
        st.subheader("📥 Bulk Import Advertised Positions")
        st.info("Upload an Excel or CSV file to import multiple advertised positions at once")
        
        # ============================================
        # DOWNLOAD TEMPLATE SECTION
        # ============================================
        st.markdown("### 📄 Step 1: Download Template")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Create template dataframe
            template_df = pd.DataFrame({
                'position_title': ['ECDE Teacher - Permanent', 'ECDE Trainer', 'ECDE Supervisor'],
                'position_code': ['ECDE/2024/001', 'ECDE/2024/002', 'ECDE/2024/003'],
                'department': ['Early Childhood Education', 'Training Department', 'Quality Assurance'],
                'employment_type': ['Permanent', 'Contract', 'Permanent'],
                'vacancies': [10, 3, 5],
                'requirements': [
                    "Bachelor's Degree in ECDE or Education\nTSC Registration\nCPR Certification",
                    "Master's Degree in ECDE\n5+ years teaching experience\nTraining certification",
                    "Bachelor's Degree\n3+ years supervisory experience\nValid driving license"
                ],
                'responsibilities': [
                    "Teach children aged 3-5 years\nDevelop lesson plans\nAssess student progress",
                    "Train ECDE teachers\nDevelop training materials\nConduct workshops",
                    "Supervise ECDE centers\nQuality assurance visits\nTeacher evaluation"
                ],
                'salary_range': ['KES 35,000 - 45,000', 'KES 60,000 - 80,000', 'KES 50,000 - 65,000'],
                'application_deadline': ['2025-01-31', '2025-01-15', '2025-01-20'],
                'status': ['Open', 'Open', 'Open']
            })
            
            csv_data = template_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download CSV Template", 
                csv_data, 
                "positions_import_template.csv", 
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            # Excel template
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, sheet_name='Positions', index=False)
            excel_data = output.getvalue()
            st.download_button(
                "📥 Download Excel Template", 
                excel_data, 
                "positions_import_template.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        st.markdown("---")
        
        # ============================================
        # UPLOAD SECTION
        # ============================================
        st.markdown("### 📂 Step 2: Upload Your File")
        
        uploaded_file = st.file_uploader(
            "Choose Excel or CSV file",
            type=["xlsx", "xls", "csv"],
            key="bulk_positions_upload",
            help="File must contain columns: position_title, position_code, department, employment_type, vacancies, requirements, responsibilities, salary_range, application_deadline, status"
        )
        
        if uploaded_file:
            try:
                # Read the file
                if uploaded_file.name.endswith('.csv'):
                    import_df = pd.read_csv(uploaded_file)
                else:
                    import_df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ File loaded successfully! Found {len(import_df)} rows")
                
                # Preview data
                with st.expander("📊 Preview uploaded data", expanded=True):
                    st.dataframe(import_df.head(10), use_container_width=True)
                
                # Column validation
                required_columns = ['position_title', 'position_code', 'department', 'employment_type', 
                                   'vacancies', 'requirements', 'responsibilities', 'salary_range', 
                                   'application_deadline', 'status']
                
                missing_cols = [col for col in required_columns if col not in import_df.columns]
                
                if missing_cols:
                    st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                    st.info("Please use the template above which has all required columns")
                else:
                    st.success("✅ All required columns found!")
                    
                    # Show column mapping info
                    st.markdown("### 📋 Column Mapping")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Required columns (found):**")
                        for col in required_columns:
                            st.write(f"✅ {col}")
                    with col2:
                        st.write("**Optional columns (ignored):**")
                        extra_cols = [col for col in import_df.columns if col not in required_columns]
                        if extra_cols:
                            for col in extra_cols[:5]:
                                st.write(f"📌 {col}")
                        else:
                            st.write("None")
                    
                    # Import button
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("🚀 IMPORT POSITIONS", use_container_width=True, type="primary", key="bulk_import_btn"):
                            with st.spinner("Importing positions..."):
                                cursor = conn.cursor()
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                username = st.session_state.user['username']
                                
                                inserted = 0
                                skipped = 0
                                errors = []
                                
                                progress_bar = st.progress(0)
                                
                                for idx, row in import_df.iterrows():
                                    try:
                                        position_title = str(row['position_title']).strip()
                                        if not position_title or position_title == 'nan':
                                            skipped += 1
                                            errors.append(f"Row {idx+2}: Missing position title")
                                            continue
                                        
                                        # Check for duplicate position_code
                                        position_code = str(row['position_code']).strip() if pd.notna(row['position_code']) else ''
                                        if position_code and position_code != 'nan':
                                            if is_cloud:
                                                cursor.execute("SELECT id FROM advertised_positions WHERE position_code = %s", (position_code,))
                                            else:
                                                cursor.execute("SELECT id FROM advertised_positions WHERE position_code = ?", (position_code,))
                                            if cursor.fetchone():
                                                skipped += 1
                                                errors.append(f"Row {idx+2}: Position code '{position_code}' already exists")
                                                continue
                                        
                                        # Insert position
                                        if is_cloud:
                                            cursor.execute("""
                                                INSERT INTO advertised_positions (
                                                    position_title, position_code, department, employment_type, vacancies,
                                                    requirements, responsibilities, salary_range, application_deadline, status,
                                                    created_at, created_by
                                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                            """, (
                                                position_title,
                                                position_code,
                                                str(row['department']) if pd.notna(row['department']) else '',
                                                str(row['employment_type']) if pd.notna(row['employment_type']) else 'Permanent',
                                                int(row['vacancies']) if pd.notna(row['vacancies']) else 1,
                                                str(row['requirements']) if pd.notna(row['requirements']) else '',
                                                str(row['responsibilities']) if pd.notna(row['responsibilities']) else '',
                                                str(row['salary_range']) if pd.notna(row['salary_range']) else '',
                                                str(row['application_deadline']) if pd.notna(row['application_deadline']) else datetime.now().strftime("%Y-%m-%d"),
                                                str(row['status']) if pd.notna(row['status']) else 'Open',
                                                now, username
                                            ))
                                        else:
                                            cursor.execute("""
                                                INSERT INTO advertised_positions (
                                                    position_title, position_code, department, employment_type, vacancies,
                                                    requirements, responsibilities, salary_range, application_deadline, status,
                                                    created_at, created_by
                                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                            """, (
                                                position_title,
                                                position_code,
                                                str(row['department']) if pd.notna(row['department']) else '',
                                                str(row['employment_type']) if pd.notna(row['employment_type']) else 'Permanent',
                                                int(row['vacancies']) if pd.notna(row['vacancies']) else 1,
                                                str(row['requirements']) if pd.notna(row['requirements']) else '',
                                                str(row['responsibilities']) if pd.notna(row['responsibilities']) else '',
                                                str(row['salary_range']) if pd.notna(row['salary_range']) else '',
                                                str(row['application_deadline']) if pd.notna(row['application_deadline']) else datetime.now().strftime("%Y-%m-%d"),
                                                str(row['status']) if pd.notna(row['status']) else 'Open',
                                                now, username
                                            ))
                                        inserted += 1
                                        
                                    except Exception as e:
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: {str(e)[:100]}")
                                    
                                    # Update progress
                                    progress_bar.progress((idx + 1) / len(import_df))
                                
                                conn.commit()
                                
                                if inserted > 0:
                                    st.success(f"✅ Successfully imported {inserted} positions!")
                                    st.balloons()
                                
                                if skipped > 0:
                                    st.warning(f"⚠️ Skipped {skipped} rows")
                                    if errors:
                                        with st.expander(f"View {len(errors)} errors"):
                                            for err in errors[:20]:
                                                st.write(f"- {err}")
                                
                                if inserted > 0:
                                    st.rerun()
                            
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        
        # ============================================
        # INSTRUCTIONS SECTION
        # ============================================
        with st.expander("📖 Instructions for Bulk Import"):
            st.markdown("""
            ### How to use Bulk Import:
            
            1. **Download the template** (CSV or Excel) using the buttons above
            2. **Open the template** in Excel or Google Sheets
            3. **Fill in your positions** - one row per position
            4. **Save your file** (keep as CSV or Excel format)
            5. **Upload the file** using the file uploader
            6. **Click IMPORT POSITIONS** to add them to the database
            
            ### Column Descriptions:
            
            | Column | Required | Description |
            |--------|----------|-------------|
            | position_title | Yes | Name of the position |
            | position_code | No | Unique code for the position |
            | department | No | Department name |
            | employment_type | No | Permanent, Contract, Temporary, etc. |
            | vacancies | No | Number of openings (default: 1) |
            | requirements | No | Job requirements (use \n for line breaks) |
            | responsibilities | No | Job duties (use \n for line breaks) |
            | salary_range | No | Salary range |
            | application_deadline | No | Closing date (YYYY-MM-DD format) |
            | status | No | Open, Closed, or On Hold (default: Open) |
            
            ### Notes:
            - Use the template as a guide
            - You can add more rows than the template
            - Duplicate position_codes will be skipped
            - All fields except position_title are optional
            """)
# =========================================================
# REPORTS FUNCTION
# =========================================================
def reports():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">📈 Reports & Analytics</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Generate comprehensive recruitment reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Check if staff table exists and has data
    try:
        df = pd.read_sql("SELECT * FROM staff", conn)
    except:
        st.warning("Database not properly initialized. Please restart the application.")
        conn.close()
        return
    
    # Get advertised positions for filter
    try:
        if is_cloud:
            positions_df = pd.read_sql("""
                SELECT id, position_title, position_code, status 
                FROM advertised_positions 
                ORDER BY id DESC
            """, conn)
        else:
            positions_df = pd.read_sql("""
                SELECT id, position_title, position_code, status 
                FROM advertised_positions 
                ORDER BY id DESC
            """, conn)
    except:
        positions_df = pd.DataFrame()
    
    conn.close()
    
    if df.empty:
        st.warning("No data available to generate reports. Please import applicant data first.")
        return
    
    # ======================================================
    # FILTER SECTION
    # ======================================================
    st.subheader("🔍 Filter Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Position filter
        if not positions_df.empty:
            position_options = ["All Positions"] + [f"{row['position_title']} ({row['position_code']})" for _, row in positions_df.iterrows()]
            selected_position = st.selectbox("Filter by Position", position_options, key="report_position_filter")
            
            if selected_position != "All Positions":
                selected_position_title = selected_position.split(" (")[0]
                df = df[df['position_applied'] == selected_position_title]
        else:
            st.info("No advertised positions found")
        
        # Subcounty filter
        if 'subcounty' in df.columns and not df.empty:
            subcounty_options = ["All Sub-Counties"] + sorted(df['subcounty'].dropna().unique().tolist())
            selected_subcounty = st.selectbox("Filter by Sub-County", subcounty_options, key="report_subcounty_filter")
            if selected_subcounty != "All Sub-Counties":
                df = df[df['subcounty'] == selected_subcounty]
        
        # Gender filter
        if 'gender' in df.columns and not df.empty:
            gender_options = ["All Genders", "Male", "Female", "Other"]
            selected_gender = st.selectbox("Filter by Gender", gender_options, key="report_gender_filter")
            if selected_gender != "All Genders":
                df = df[df['gender'] == selected_gender]
    
    with col2:
        # Ward filter
        if 'ward' in df.columns and not df.empty:
            ward_options = ["All Wards"] + sorted(df['ward'].dropna().unique().tolist())
            selected_ward = st.selectbox("Filter by Ward", ward_options, key="report_ward_filter")
            if selected_ward != "All Wards":
                df = df[df['ward'] == selected_ward]
        
        # Disability filter
        if 'disability' in df.columns and not df.empty:
            disability_options = ["All", "With Disability", "Without Disability"]
            selected_disability = st.selectbox("Filter by Disability", disability_options, key="report_disability_filter")
            if selected_disability == "With Disability":
                df = df[df['disability'].notna() & (df['disability'] != '') & (df['disability'] != 'None') & (df['disability'].str.lower() != 'none')]
            elif selected_disability == "Without Disability":
                df = df[df['disability'].isna() | (df['disability'] == '') | (df['disability'] == 'None') | (df['disability'].str.lower() == 'none')]
        
        # Ethnicity filter
        if 'ethnicity' in df.columns and not df.empty:
            ethnicity_options = ["All Ethnicities"] + sorted(df['ethnicity'].dropna().unique().tolist())
            selected_ethnicity = st.selectbox("Filter by Ethnicity", ethnicity_options, key="report_ethnicity_filter")
            if selected_ethnicity != "All Ethnicities":
                df = df[df['ethnicity'] == selected_ethnicity]
    
    with col3:
        # Age range filter
        if 'yob' in df.columns and not df.empty and not df['yob'].isna().all():
            current_year = datetime.now().year
            df['age'] = current_year - df['yob']
            min_age = int(df['age'].min()) if not df['age'].isna().all() else 18
            max_age = int(df['age'].max()) if not df['age'].isna().all() else 100
            age_range = st.slider("Age Range", min_age, max_age, (min_age, max_age), key="report_age_filter")
            df = df[(df['age'] >= age_range[0]) & (df['age'] <= age_range[1])]
        
        # Date range filter
        if 'created_at' in df.columns and not df.empty:
            df['created_date'] = pd.to_datetime(df['created_at']).dt.date
            min_date = df['created_date'].min()
            max_date = df['created_date'].max()
            date_range = st.date_input("Date Range", [min_date, max_date], key="report_date_filter")
            if len(date_range) == 2:
                df = df[(df['created_date'] >= date_range[0]) & (df['created_date'] <= date_range[1])]
    
    # Show active filters summary
    st.info(f"📊 **Showing {len(df)} records** based on selected filters")
    st.markdown("---")
    
    # Report type selector
    report_type = st.selectbox(
        "Select Report Type",
        ["📊 Applicant Summary Report", "📋 Shortlisted Candidates Report", "🎓 Qualifications Analysis", 
         "📍 Geographic Distribution", "📅 Application Timeline", "📑 Complete Export"]
    )
    
    # ==================== APPLICANT SUMMARY REPORT ====================
    if report_type == "📊 Applicant Summary Report":
        st.subheader("Applicant Summary Report")
        
        if df.empty:
            st.warning("No data matches the selected filters.")
        else:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total = len(df)
                st.metric("Total Applicants", total)
            
            with col2:
                shortlisted = len(df[df['application_status'] == 'Shortlisted']) if 'application_status' in df.columns else 0
                st.metric("Shortlisted", shortlisted, delta=f"{shortlisted/total*100:.0f}%" if total > 0 else "0%")
            
            with col3:
                interviewed = len(df[df['application_status'] == 'Interviewed']) if 'application_status' in df.columns else 0
                st.metric("Interviewed", interviewed)
            
            with col4:
                hired = len(df[df['application_status'] == 'Hired']) if 'application_status' in df.columns else 0
                st.metric("Hired", hired)
            
            # Status distribution
            if 'application_status' in df.columns:
                st.subheader("Application Status Distribution")
                status_counts = df['application_status'].value_counts()
                fig = px.pie(values=status_counts.values, names=status_counts.index, title="Applications by Status")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Gender distribution
            if 'gender' in df.columns:
                st.subheader("Gender Distribution")
                col1, col2 = st.columns(2)
                with col1:
                    gender_counts = df['gender'].value_counts()
                    fig = px.pie(values=gender_counts.values, names=gender_counts.index, title="Gender Ratio")
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.dataframe(gender_counts.reset_index().rename(columns={'index': 'Gender', 'gender': 'Count'}), use_container_width=True)
            
            # Disability distribution
            if 'disability' in df.columns:
                st.subheader("Disability Distribution")
                disability_counts = df['disability'].apply(lambda x: 'With Disability' if pd.notna(x) and x != '' and x != 'None' and x.lower() != 'none' else 'Without Disability').value_counts()
                fig = px.pie(values=disability_counts.values, names=disability_counts.index, title="Disability Status")
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            # Ethnicity distribution
            if 'ethnicity' in df.columns:
                st.subheader("Ethnicity Distribution")
                ethnicity_counts = df['ethnicity'].value_counts().head(10)
                fig = px.bar(x=ethnicity_counts.values, y=ethnicity_counts.index, orientation='h',
                            title="Top 10 Ethnicities", labels={'x': 'Count', 'y': 'Ethnicity'})
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Export button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Filtered Report (CSV)", csv, f"applicant_report_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
    
    # ==================== SHORTLISTED CANDIDATES REPORT ====================
    elif report_type == "📋 Shortlisted Candidates Report":
        st.subheader("Shortlisted Candidates Report")
        
        if df.empty:
            st.warning("No data matches the selected filters.")
        elif 'application_status' in df.columns:
            shortlisted_df = df[df['application_status'] == 'Shortlisted']
            
            if shortlisted_df.empty:
                st.info("No shortlisted candidates found matching the filters.")
            else:
                st.success(f"Total Shortlisted: {len(shortlisted_df)}")
                
                # Display shortlisted candidates
                display_cols = ['name', 'id_number', 'contact', 'gender', 'subcounty', 'ward', 'qualifications', 'experience_years', 'position_applied']
                available_cols = [col for col in display_cols if col in shortlisted_df.columns]
                st.dataframe(shortlisted_df[available_cols], use_container_width=True)
                
                # Export shortlist
                csv = shortlisted_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Shortlist (CSV)", csv, f"shortlist_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
        else:
            st.warning("Application status data not available")
    
    # ==================== QUALIFICATIONS ANALYSIS ====================
    elif report_type == "🎓 Qualifications Analysis":
        st.subheader("Qualifications Analysis")
        
        if df.empty:
            st.warning("No data matches the selected filters.")
        elif 'qualifications' in df.columns:
            qual_counts = df['qualifications'].value_counts().head(15)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(x=qual_counts.values, y=qual_counts.index, orientation='h', 
                            title="Top Qualifications", labels={'x': 'Count', 'y': 'Qualification'})
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(qual_counts.reset_index().rename(columns={'index': 'Qualification', 'qualifications': 'Count'}), use_container_width=True)
            
            # Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Qualifications Data (CSV)", csv, f"qualifications_report_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
        else:
            st.warning("Qualifications data not available")
    
    # ==================== GEOGRAPHIC DISTRIBUTION ====================
    elif report_type == "📍 Geographic Distribution":
        st.subheader("Geographic Distribution of Applicants")
        
        if df.empty:
            st.warning("No data matches the selected filters.")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                if 'subcounty' in df.columns:
                    subcounty_counts = df['subcounty'].value_counts().head(15)
                    fig = px.bar(x=subcounty_counts.values, y=subcounty_counts.index, orientation='h',
                                title="Applications by Sub-County", labels={'x': 'Number of Applicants', 'y': 'Sub-County'})
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(subcounty_counts.reset_index().rename(columns={'index': 'Sub-County', 'subcounty': 'Count'}), use_container_width=True)
                else:
                    st.info("Sub-county data not available")
            
            with col2:
                if 'ward' in df.columns:
                    ward_counts = df['ward'].value_counts().head(15)
                    fig = px.bar(x=ward_counts.values, y=ward_counts.index, orientation='h',
                                title="Applications by Ward", labels={'x': 'Number of Applicants', 'y': 'Ward'})
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(ward_counts.reset_index().rename(columns={'index': 'Ward', 'ward': 'Count'}), use_container_width=True)
                else:
                    st.info("Ward data not available")
    
    # ==================== APPLICATION TIMELINE ====================
    elif report_type == "📅 Application Timeline":
        st.subheader("Application Timeline")
        
        if df.empty:
            st.warning("No data matches the selected filters.")
        elif 'created_at' in df.columns:
            df['created_date'] = pd.to_datetime(df['created_at']).dt.date
            timeline = df.groupby('created_date').size().reset_index(name='count')
            timeline = timeline.sort_values('created_date')
            
            fig = px.line(timeline, x='created_date', y='count', 
                         title="Applications Over Time", labels={'count': 'Number of Applications', 'created_date': 'Date'})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Cumulative applications
            timeline['cumulative'] = timeline['count'].cumsum()
            fig2 = px.area(timeline, x='created_date', y='cumulative',
                           title="Cumulative Applications", labels={'cumulative': 'Total Applications', 'created_date': 'Date'})
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
            
            # Export timeline data
            csv = timeline.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Timeline Data (CSV)", csv, f"timeline_report_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
        else:
            st.warning("Date data not available")
    
    # ==================== COMPLETE EXPORT ====================
    elif report_type == "📑 Complete Export":
        st.subheader("Complete Data Export")
        
        if df.empty:
            st.warning("No data matches the selected filters.")
        else:
            st.info(f"Exporting {len(df)} filtered records")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Column selection
                all_columns = df.columns.tolist()
                selected_columns = st.multiselect("Select columns to export", all_columns, default=all_columns)
            
            with col2:
                # Format selection
                export_format = st.selectbox("Export format", ["CSV", "Excel", "JSON"])
            
            if selected_columns:
                export_df = df[selected_columns]
                
                if export_format == "CSV":
                    csv = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download CSV", csv, f"complete_export_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
                
                elif export_format == "Excel":
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        export_df.to_excel(writer, sheet_name='Applicants', index=False)
                        
                        # Add summary sheet
                        summary = pd.DataFrame({
                            'Metric': ['Total Records', 'Export Date', 'Exported By', 'Columns Exported'],
                            'Value': [len(export_df), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                     st.session_state.user['username'], ', '.join(selected_columns)]
                        })
                        summary.to_excel(writer, sheet_name='Summary', index=False)
                    
                    st.download_button("📥 Download Excel", output.getvalue(), f"complete_export_{datetime.now().strftime('%Y%m%d')}.xlsx", 
                                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                
                elif export_format == "JSON":
                    json_str = export_df.to_json(orient='records', indent=2)
                    st.download_button("📥 Download JSON", json_str, f"complete_export_{datetime.now().strftime('%Y%m%d')}.json", use_container_width=True)
# =========================================================
# USER MANAGEMENT
# =========================================================
def users():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">User Management</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Manage system users, roles, and permissions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Allow both Admin and Super Admin to access user management
    if st.session_state.user["role"] not in ["Admin", "Super Admin"]:
        st.error("⛔ Access Denied. Admin or Super Admin privileges required.")
        return
    
    # Initialize session state for editing
    if 'editing_user' not in st.session_state:
        st.session_state.editing_user = None
    if 'changing_password_for' not in st.session_state:
        st.session_state.changing_password_for = None
    if 'show_create_form' not in st.session_state:
        st.session_state.show_create_form = False
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    cursor = conn.cursor()
    
    # =====================================================
    # CHANGE PASSWORD FORM
    # =====================================================
    if st.session_state.changing_password_for:
        # Fetch user details
        if is_cloud:
            cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (st.session_state.changing_password_for,))
        else:
            cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (st.session_state.changing_password_for,))
        user_data = cursor.fetchone()
        
        if user_data:
            st.subheader(f"🔐 Change Password for: {user_data[1]} ({user_data[2]})")
            
            with st.form("change_password_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                with col2:
                    confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Confirm new password")
                
                st.info("Password must be at least 4 characters long")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    if st.form_submit_button("🔑 Change Password", use_container_width=True, type="primary"):
                        if not new_password:
                            st.error("❌ Password cannot be empty")
                        elif len(new_password) < 4:
                            st.error("❌ Password must be at least 4 characters")
                        elif new_password != confirm_password:
                            st.error("❌ Passwords do not match")
                        else:
                            hashed_password = hash_password(new_password)
                            if is_cloud:
                                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_data[0]))
                            else:
                                cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_data[0]))
                            conn.commit()
                            st.success(f"✅ Password changed successfully for '{user_data[1]}'!")
                            log_audit(
                                st.session_state.user['username'], 
                                "PASSWORD_CHANGE", 
                                user_data[0], 
                                f"Password changed for user: {user_data[1]} (Role: {user_data[2]})", 
                                "Success"
                            )
                            st.session_state.changing_password_for = None
                            st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.session_state.changing_password_for = None
                        st.rerun()
        else:
            st.error("User not found")
            st.session_state.changing_password_for = None
            st.rerun()
        
        st.markdown("---")
    
    # =====================================================
    # EDIT USER FORM (With Email and Phone)
    # =====================================================
    elif st.session_state.editing_user:
        # Fetch user details
        if is_cloud:
            cursor.execute("SELECT id, username, role, email, phone FROM users WHERE id = %s", (st.session_state.editing_user,))
        else:
            cursor.execute("SELECT id, username, role, email, phone FROM users WHERE id = ?", (st.session_state.editing_user,))
        user_data = cursor.fetchone()
        
        if user_data:
            st.subheader(f"✏️ Edit User: {user_data[1]}")
            
            # Get current values
            current_role = user_data[2] if len(user_data) > 2 else "User"
            current_email = user_data[3] if len(user_data) > 3 else ''
            current_phone = user_data[4] if len(user_data) > 4 else ''
            
            role_options = ["User", "HR", "Admin", "Super Admin"]
            
            # Set index based on current role
            role_index = role_options.index(current_role) if current_role in role_options else 0
            
            with st.form("edit_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username", value=user_data[1], disabled=True, help="Username cannot be changed")
                    new_email = st.text_input("Email", value=current_email, placeholder="user@example.com", key="edit_email", help="Used for password reset notifications")
                with col2:
                    new_role = st.selectbox("Role", role_options, index=role_index, key="edit_role_select")
                    new_phone = st.text_input("Phone Number", value=current_phone, placeholder="0712345678", key="edit_phone", help="Used for SMS notifications")
                
                # Role description helper
                if new_role == "Super Admin":
                    st.info("🔐 **Super Admin**: Full system access including Audit Trail, Backup & Restore, Test Data, and User Management")
                elif new_role == "Admin":
                    st.info("📋 **Admin**: Can manage staff, process promotions, manage users, but cannot access Audit Trail, Backup & Restore, or Test Data")
                elif new_role == "HR":
                    st.info("👔 **HR**: Can only access HR Functions module")
                else:
                    st.info("👤 **User**: Basic access - view staff, register applicants, HR functions")
                
                # Warning when demoting a Super Admin
                if current_role == "Super Admin" and new_role != "Super Admin":
                    st.warning("⚠️ Warning: You are demoting a Super Admin. This user will lose access to Audit Trail, Backup & Restore, and Test Data.")
                
                # Warning when changing your own role
                if user_data[1] == st.session_state.user.get('username') and new_role != current_role:
                    st.warning("⚠️ Warning: You are changing your own role. Make sure you have another Super Admin account if demoting yourself.")
                
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                        if is_cloud:
                            cursor.execute("""
                                UPDATE users SET 
                                    role = %s, 
                                    email = %s, 
                                    phone = %s 
                                WHERE id = %s
                            """, (new_role, new_email if new_email else None, new_phone if new_phone else None, user_data[0]))
                        else:
                            cursor.execute("""
                                UPDATE users SET 
                                    role = ?, 
                                    email = ?, 
                                    phone = ? 
                                WHERE id = ?
                            """, (new_role, new_email if new_email else None, new_phone if new_phone else None, user_data[0]))
                        conn.commit()
                        st.success(f"✅ User '{user_data[1]}' updated successfully! New role: {new_role}")
                        log_audit(
                            st.session_state.user['username'], 
                            "EDIT_USER", 
                            user_data[0], 
                            f"Changed user '{user_data[1]}' role from {current_role} to {new_role} | Email: {new_email} | Phone: {new_phone}", 
                            "Success"
                        )
                        st.session_state.editing_user = None
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.session_state.editing_user = None
                        st.rerun()
        else:
            st.error("User not found")
            st.session_state.editing_user = None
            st.rerun()
        
        st.markdown("---")
    
    # =====================================================
    # DISPLAY EXISTING USERS
    # =====================================================
    else:
        # Action buttons at the top
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.subheader("📋 Existing Users")
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        with col3:
            if st.button("➕ Create New User", use_container_width=True):
                st.session_state.show_create_form = True
                st.rerun()
        
        # Display users table
        try:
            users_df = pd.read_sql("SELECT id, username, role, email, phone, created_at FROM users ORDER BY created_at DESC", conn)
            
            if not users_df.empty:
                # Create a more interactive display
                for idx, user in users_df.iterrows():
                    with st.container():
                        col1, col2, col3, col4, col5, col6, col7 = st.columns([1.2, 1.2, 0.8, 1.2, 0.8, 0.8, 0.8])
                        
                        with col1:
                            st.write(f"**{user['username']}**")
                        with col2:
                            # Role with color
                            role_colors = {
                                "Super Admin": "#8b5cf6",
                                "Admin": "#3b82f6",
                                "HR": "#10b981",
                                "User": "#94a3b8"
                            }
                            role_color = role_colors.get(user['role'], "#94a3b8")
                            st.markdown(f'<span style="background: {role_color}; color: white; padding: 2px 10px; border-radius: 12px; font-size: 12px;">{user["role"]}</span>', unsafe_allow_html=True)
                        with col3:
                            st.write(user['created_at'][:10] if user['created_at'] else "N/A")
                        with col4:
                            st.write(user['email'] if user['email'] else "—")
                        with col5:
                            # Show Edit button for all users except current user
                            if user['username'] != st.session_state.user.get('username'):
                                if st.button(f"✏️", key=f"edit_{user['id']}", use_container_width=True):
                                    st.session_state.editing_user = user['id']
                                    st.rerun()
                            else:
                                st.write("—")
                        with col6:
                            # Show Password button for all users
                            if st.button(f"🔑", key=f"pwd_{user['id']}", use_container_width=True):
                                st.session_state.changing_password_for = user['id']
                                st.rerun()
                        with col7:
                            # Delete button (only for non-self)
                            if user['username'] != st.session_state.user.get('username'):
                                if st.button(f"🗑️", key=f"delete_{user['id']}", use_container_width=True):
                                    st.session_state.delete_target = user['id']
                                    st.session_state.delete_name = user['username']
                                    st.rerun()
                            else:
                                st.write("—")
                        
                        # Delete confirmation
                        if st.session_state.get('delete_target') == user['id']:
                            st.warning(f"⚠️ Are you sure you want to delete **{st.session_state.delete_name}**?")
                            col1, col2, col3 = st.columns([1, 1, 2])
                            with col1:
                                if st.button("✅ Yes, Delete", key=f"confirm_delete_{user['id']}", use_container_width=True):
                                    if is_cloud:
                                        cursor.execute("DELETE FROM users WHERE id = %s", (user['id'],))
                                    else:
                                        cursor.execute("DELETE FROM users WHERE id = ?", (user['id'],))
                                    conn.commit()
                                    log_audit(st.session_state.user['username'], "DELETE_USER", user['id'], f"Deleted user: {user['username']}", "Success")
                                    st.success(f"✅ User '{user['username']}' deleted!")
                                    st.session_state.delete_target = None
                                    st.session_state.delete_name = None
                                    st.rerun()
                            with col2:
                                if st.button("❌ Cancel", key=f"cancel_delete_{user['id']}", use_container_width=True):
                                    st.session_state.delete_target = None
                                    st.session_state.delete_name = None
                                    st.rerun()
                            st.markdown("---")
                        
                        st.markdown("---")
                
            else:
                st.info("No users found")
                
        except Exception as e:
            st.info("Users table ready. Create your first user below.")
    
    # =====================================================
    # CREATE NEW USER FORM (No Password - OTP will be sent)
    # =====================================================
    if st.session_state.get('show_create_form', False):
        st.markdown("---")
        st.subheader("➕ Create New User")
        st.info("📧 A verification OTP will be sent to the user's email. They will set their password on first login.")
        
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*", placeholder="Choose a username", key="create_username")
                new_email = st.text_input("Email*", placeholder="user@example.com", key="create_email", help="Required for OTP verification")
            with col2:
                new_phone = st.text_input("Phone Number", placeholder="0712345678", key="create_phone", help="Optional for SMS notifications")
                new_role = st.selectbox("Role*", ["User", "HR", "Admin", "Super Admin"], key="create_role")
            
            # Role description helper
            if new_role == "Super Admin":
                st.info("🔐 **Super Admin**: Full system access including Audit Trail, Backup & Restore, Test Data, and User Management")
            elif new_role == "Admin":
                st.info("📋 **Admin**: Can manage staff, process promotions, manage users, but cannot access Audit Trail, Backup & Restore, or Test Data")
            elif new_role == "HR":
                st.info("👔 **HR**: Can only access HR Functions module")
            else:
                st.info("👤 **User**: Basic access - view staff, register applicants, HR functions")
            
            st.caption("📧 An OTP will be sent to the user's email for verification. The user will set their password on first login.")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.form_submit_button("👤 Create User", use_container_width=True, type="primary"):
                    if not new_username or not new_email:
                        st.error("❌ Username and Email are required")
                    else:
                        success, otp = create_user(new_username, new_role, new_email, new_phone)
                        if success:
                            st.success(f"✅ User '{new_username}' created successfully with role: {new_role}!")
                            st.info(f"📧 Verification OTP sent to {new_email}")
                            st.caption("User will be prompted to verify their email and set password on first login.")
                            log_audit(
                                st.session_state.user['username'], 
                                "CREATE_USER", 
                                0, 
                                f"Created user: {new_username} with role: {new_role} | Email: {new_email} | Phone: {new_phone}", 
                                "Success"
                            )
                            st.session_state.show_create_form = False
                            st.rerun()
                        else:
                            st.error(f"❌ Username '{new_username}' may already exist")
            
            with col2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.show_create_form = False
                    st.rerun()
    
    conn.close()


# =========================================================
# CREATE USER FUNCTION (No Password Required - OTP Verification)
# =========================================================
def create_user(username, role, email, phone=None):
    """Create a new user with email verification OTP (no password set by admin)"""
    try:
        conn = get_conn()
        if conn is None:
            return False, None
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        username_lower = username.lower()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate a temporary random password (user will change this after verification)
        import secrets
        temp_password = secrets.token_urlsafe(8)
        hashed_temp_password = hash_password(temp_password)
        
        # Validate role - include HR
        valid_roles = ["Super Admin", "Admin", "HR", "User"]
        if role not in valid_roles:
            role = "User"
        
        # Generate verification OTP
        import random
        otp = str(random.randint(100000, 999999))
        otp_expiry = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if users table has the new columns
        try:
            if is_cloud:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name IN ('is_verified', 'verification_otp', 'verification_otp_expiry', 'temp_password')
                """)
                existing_cols = [row[0] for row in cursor.fetchall()]
            else:
                cursor.execute("PRAGMA table_info(users)")
                existing_cols = [row[1] for row in cursor.fetchall()]
        except:
            existing_cols = []
        
        # Build the INSERT query based on available columns
        if 'is_verified' in existing_cols and 'verification_otp' in existing_cols:
            if is_cloud:
                cursor.execute("""
                    INSERT INTO users (username, password, role, email, phone, created_at, 
                                       is_verified, temp_password, verification_otp, verification_otp_expiry)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (username_lower, hashed_temp_password, role, email, phone, created_at,
                      False, hashed_temp_password, otp, otp_expiry))
            else:
                cursor.execute("""
                    INSERT INTO users (username, password, role, email, phone, created_at, 
                                       is_verified, temp_password, verification_otp, verification_otp_expiry)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (username_lower, hashed_temp_password, role, email, phone, created_at,
                      False, hashed_temp_password, otp, otp_expiry))
            
            # Send OTP email
            if email:
                send_otp_email(email, otp, username, purpose="verification")
        else:
            # Fallback: create user without verification columns
            if is_cloud:
                cursor.execute("""
                    INSERT INTO users (username, password, role, email, phone, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (username_lower, hashed_temp_password, role, email, phone, created_at))
            else:
                cursor.execute("""
                    INSERT INTO users (username, password, role, email, phone, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username_lower, hashed_temp_password, role, email, phone, created_at))
        
        conn.commit()
        conn.close()
        return True, otp
        
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False, None


# =========================================================
# UPDATE USER FUNCTION
# =========================================================
def update_user(user_id, role):
    """Update user role"""
    try:
        conn = get_conn()
        if conn is None:
            return False
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        if is_cloud:
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
        else:
            cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error updating user: {e}")
        return False


# =========================================================
# CHANGE PASSWORD FUNCTION
# =========================================================
def change_password(user_id, new_password):
    """Change user password"""
    try:
        conn = get_conn()
        if conn is None:
            return False
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        hashed_password = hash_password(new_password)
        
        if is_cloud:
            cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
        else:
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error changing password: {e}")
        return False


# =========================================================
# DELETE USER FUNCTION
# =========================================================
def delete_user(user_id):
    """Delete a user"""
    try:
        conn = get_conn()
        if conn is None:
            return False
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        if is_cloud:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        else:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False
# =========================================================
# IMPORT EXCEL WITH DIRECT TEMPLATE SUPPORT
# =========================================================
def import_excel():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">📥 Import Applicant Data</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Import job applications based on advertised positions</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    if conn is None:
        st.error("Database connection failed")
        return
    
    # =========================================================
    # ADD THE convert_to_year FUNCTION HERE (at the top)
    # =========================================================
    def convert_to_year(value):
        """Convert various date/year formats to a 4-digit INTEGER year"""
        if value is None or value == '' or value == 'nan' or pd.isna(value):
            return None
        
        value_str = str(value).strip()
        
        # Handle 4-digit year (YYYY)
        if value_str.isdigit() and len(value_str) == 4:
            return int(value_str)
        
        # Handle 2-digit year (YY)
        if value_str.isdigit() and len(value_str) == 2:
            year = int(value_str)
            # Years 0-24 = 2000s, Years 25-99 = 1900s
            return 2000 + year if year <= 24 else 1900 + year
        
        # Handle DD/MM/YY or DD/MM/YYYY format
        if '/' in value_str:
            parts = value_str.split('/')
            if len(parts) >= 3:
                year_part = parts[2]
                if year_part.isdigit():
                    if len(year_part) == 2:
                        year = int(year_part)
                        return 2000 + year if year <= 24 else 1900 + year
                    elif len(year_part) == 4:
                        return int(year_part)
        
        # Handle DD-MM-YY or DD-MM-YYYY format
        if '-' in value_str:
            parts = value_str.split('-')
            if len(parts) >= 3:
                year_part = parts[2]
                if year_part.isdigit():
                    if len(year_part) == 2:
                        year = int(year_part)
                        return 2000 + year if year <= 24 else 1900 + year
                    elif len(year_part) == 4:
                        return int(year_part)
        
        return None
    
    # Step 1: Select advertised position
    st.subheader("Step 1: Select Advertised Position")
    
    # ... rest of your import code ...
    
    # Step 1: Select advertised position
    st.subheader("Step 1: Select Advertised Position")
    
    try:
        if is_cloud:
            positions_df = pd.read_sql("SELECT * FROM advertised_positions WHERE status = 'Open' ORDER BY id DESC", conn)
        else:
            positions_df = pd.read_sql("SELECT * FROM advertised_positions WHERE status = 'Open' ORDER BY id DESC", conn)
    except:
        positions_df = pd.DataFrame()
    
    if positions_df.empty:
        st.warning("⚠️ No open advertised positions found. Please create a position in Settings > Advertised Positions first.")
        if st.button("Go to Settings"):
            st.session_state.page = "⚙️ Settings"
            st.rerun()
        return
    
    selected_position = st.selectbox(
        "Select Position",
        positions_df['id'].tolist(),
        format_func=lambda x: f"{positions_df[positions_df['id']==x]['position_title'].iloc[0]} - {positions_df[positions_df['id']==x]['position_code'].iloc[0]} (Vacancies: {positions_df[positions_df['id']==x]['vacancies'].iloc[0]})"
    )
    
    selected_position_data = positions_df[positions_df['id'] == selected_position].iloc[0]
    selected_position_title = selected_position_data['position_title']
    selected_position_code = selected_position_data['position_code']
    
    st.info(f"**Position:** {selected_position_title} | **Code:** {selected_position_code} | **Vacancies:** {selected_position_data['vacancies']}")
    
    st.markdown("---")
    
    # Step 2: Download template
    st.subheader("Step 2: Download Template")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("Download the template with the correct column format")
        
        template_df = pd.DataFrame({
            'SNO': [1, 2],
            'NAME': ['John Doe', 'Jane Smith'],
            'GENDER': ['Male', 'Female'],
            'ID NUMBER': ['12345678', '87654321'],
            'YOB': [1990, 1992],
            'ETHINICITY': ['Kikuyu', 'Luo'],
            'DISABILITY': ['None', 'None'],
            'CONTACT': ['0712345678', '0723456789'],
            'KCSE/KCE': ['B+', 'A-'],
            'QUALIFICATIONS': ['Diploma in ECDE', 'Degree in ECDE'],
            'PRACTICING LICENCE': ['Yes - TSC No: 123456', 'No'],
            'SUB-COUNTY': ['Central', 'East'],
            'WARD': ['Ward 1', 'Ward 2'],
            'EXPERIENCE': ['5 years', '3 years'],
            'REMARKS': ['', '']
        })
        
        csv = template_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV Template", csv, "import_template.csv", "text/csv")
    
    with col2:
        st.markdown("""
        **Required Columns:**
        - `NAME` - Full name (Required)
        - `ID NUMBER` - National ID (Required)
        
        **Optional Columns:**
        - SNO, GENDER, YOB, ETHINICITY, DISABILITY
        - CONTACT, KCSE/KCE, QUALIFICATIONS
        - PRACTICING LICENCE, SUB-COUNTY, WARD
        - EXPERIENCE, REMARKS
        
        **Note:** Applicants can apply for multiple positions. 
        Duplicate ID/Name is allowed for DIFFERENT positions.
        """)
    
    st.markdown("---")
    
    # Step 3: Upload file
    st.subheader("Step 3: Upload Your Data")
    
    file = st.file_uploader("Choose Excel/CSV File", type=["xlsx", "xls", "csv"])
    
    # Initialize session state for import results
    if 'import_results' not in st.session_state:
        st.session_state.import_results = None
    if 'import_errors' not in st.session_state:
        st.session_state.import_errors = None
    if 'import_summary' not in st.session_state:
        st.session_state.import_summary = None
    
    if file is not None:
        try:
            # Read the file
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            st.success(f"✅ File loaded! Found {len(df)} rows")
            
            # Check if file matches template format
            file_columns = list(df.columns)
            has_name = any(col.upper() in ['NAME', 'FULL NAME', 'APPLICANT NAME'] for col in file_columns)
            has_id = any(col.upper() in ['ID NUMBER', 'ID', 'IDNO', 'NATIONAL ID'] for col in file_columns)
            
            if has_name and has_id:
                st.info("✅ Required columns (NAME and ID NUMBER) found. Direct import available!")
                
                # Show import rules
                st.info("""
                **📋 Import Rules:**
                - ✅ **NAME** - Required (cannot be empty)
                - ✅ **ID NUMBER** - Required (cannot be empty)
                - 📝 **Duplicate Check:** ID Number cannot be duplicated for the SAME position
                - 🔄 **Multiple Applications:** Same applicant can apply for DIFFERENT positions
                - 📝 All other fields are optional
                """)
                
                # Preview data
                with st.expander("📊 Preview data to import", expanded=True):
                    st.dataframe(df, use_container_width=True)
                    st.caption(f"Showing all {len(df)} rows")
                
                # Direct import button
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🚀 DIRECT IMPORT", use_container_width=True, type="primary"):
                        with st.spinner("Importing data..."):
                            c = conn.cursor()
                            inserted = 0
                            skipped = 0
                            errors = []
                            
                            # Track skip reasons
                            missing_name_count = 0
                            missing_id_count = 0
                            duplicate_in_position_count = 0
                            other_error_count = 0
                            
                            # Track IDs already imported in this batch for this position
                            imported_ids_in_batch = set()
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for idx, row in df.iterrows():
                                try:
                                    # Get values
                                    name = ''
                                    id_number = ''
                                    sno = idx + 1
                                    gender = ''
                                    yob = None
                                    ethnicity = ''
                                    disability = ''
                                    contact = ''
                                    kcse = ''
                                    qualifications = ''
                                    practicing_licence = ''
                                    subcounty = ''
                                    ward = ''
                                    experience = ''
                                    remarks = ''
                                    
                                    # Find NAME column
                                    for col in file_columns:
                                        if col.upper() in ['NAME', 'FULL NAME', 'APPLICANT NAME']:
                                            name = str(row[col]).strip() if pd.notna(row[col]) else ''
                                            break
                                    
                                    # Find ID NUMBER column
                                    for col in file_columns:
                                        if col.upper() in ['ID NUMBER', 'ID', 'IDNO', 'NATIONAL ID']:
                                            id_number = str(row[col]).strip() if pd.notna(row[col]) else ''
                                            break
                                    
                                    # Find other columns
                                    for col in file_columns:
                                        if col.upper() in ['SNO', 'S NO', 'SERIAL NO']:
                                            sno = int(row[col]) if pd.notna(row[col]) else idx + 1
                                        elif col.upper() in ['GENDER', 'SEX']:
                                            gender = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['YOB', 'YEAR OF BIRTH']:
                                            yob = convert_to_year(row.get('YOB'))
                                        elif col.upper() in ['ETHINICITY', 'ETHNICITY', 'TRIBE']:
                                            ethnicity = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['DISABILITY', 'DISABILITY STATUS']:
                                            disability = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['CONTACT', 'PHONE', 'MOBILE']:
                                            contact = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['KCSE', 'KCSE/KCE']:
                                            kcse = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['QUALIFICATIONS', 'QUALIFICATION']:
                                            qualifications = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['PRACTICING LICENCE', 'PRACTICE LICENSE']:
                                            practicing_licence = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['SUB-COUNTY', 'SUBCOUNTY']:
                                            subcounty = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['WARD']:
                                            ward = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['EXPERIENCE', 'YEARS OF EXPERIENCE']:
                                            experience = str(row[col]).strip() if pd.notna(row[col]) else ''
                                        elif col.upper() in ['REMARKS', 'REMARK', 'NOTES']:
                                            remarks = str(row[col]).strip() if pd.notna(row[col]) else ''
                                    
                                    # Validate required fields
                                    if not name or name == 'nan':
                                        missing_name_count += 1
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: Missing Name")
                                        continue
                                    
                                    if not id_number or id_number == 'nan':
                                        missing_id_count += 1
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: Missing ID Number")
                                        continue
                                    
                                    # Check for duplicate within the SAME position only
                                    # First, check if this ID already exists in the database for THIS position
                                    if is_cloud:
                                        c.execute("""
                                            SELECT id FROM staff 
                                            WHERE id_number = %s AND position_applied = %s
                                        """, (id_number, selected_position_title))
                                    else:
                                        c.execute("""
                                            SELECT id FROM staff 
                                            WHERE id_number = ? AND position_applied = ?
                                        """, (id_number, selected_position_title))
                                    
                                    if c.fetchone():
                                        duplicate_in_position_count += 1
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: ID {id_number} already applied for '{selected_position_title}'. Cannot apply twice for same position.")
                                        continue
                                    
                                    # Also check within the current batch being imported
                                    if id_number in imported_ids_in_batch:
                                        duplicate_in_position_count += 1
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: Duplicate ID {id_number} found in same import file for position '{selected_position_title}'")
                                        continue
                                    
                                    # Add to batch tracking
                                    imported_ids_in_batch.add(id_number)
                                    
                                    # Insert data
                                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    username = st.session_state.user['username']
                                    application_date = datetime.now().strftime("%Y-%m-%d")
                                    
                                    if is_cloud:
                                        c.execute("""
                                            INSERT INTO staff (
                                                sno, name, gender, id_number, yob, ethnicity, disability, contact,
                                                kcse, qualifications, practicing_licence, subcounty, ward, experience, remarks,
                                                position_applied, advertisement_ref, application_status,
                                                application_date, created_at, created_by
                                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """, (
                                            sno, name, gender if gender else None, id_number, 
                                            yob if yob else None, ethnicity if ethnicity else None, 
                                            disability if disability else None, contact if contact else None,
                                            kcse if kcse else None, qualifications if qualifications else None, 
                                            practicing_licence if practicing_licence else None, 
                                            subcounty if subcounty else None, ward if ward else None, 
                                            experience if experience else None, remarks if remarks else None,
                                            selected_position_title, selected_position_code, 'Pending',
                                            application_date, now, username
                                        ))
                                    else:
                                        c.execute("""
                                            INSERT INTO staff (
                                                sno, name, gender, id_number, yob, ethnicity, disability, contact,
                                                kcse, qualifications, practicing_licence, subcounty, ward, experience, remarks,
                                                position_applied, advertisement_ref, application_status,
                                                application_date, created_at, created_by
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            sno, name, gender if gender else None, id_number,
                                            yob if yob else None, ethnicity if ethnicity else None,
                                            disability if disability else None, contact if contact else None,
                                            kcse if kcse else None, qualifications if qualifications else None,
                                            practicing_licence if practicing_licence else None,
                                            subcounty if subcounty else None, ward if ward else None,
                                            experience if experience else None, remarks if remarks else None,
                                            selected_position_title, selected_position_code, 'Pending',
                                            application_date, now, username
                                        ))
                                    
                                    inserted += 1
                                    
                                except Exception as e:
                                    other_error_count += 1
                                    skipped += 1
                                    errors.append(f"Row {idx+2}: System Error - {str(e)[:100]}")
                                
                                # Update progress
                                progress_bar.progress((idx + 1) / len(df))
                                status_text.text(f"Processing: {idx+1}/{len(df)} | ✅ Inserted: {inserted} | ⚠️ Skipped: {skipped}")
                            
                            conn.commit()
                            
                            # Store results in session state
                            st.session_state.import_results = {
                                'total': len(df),
                                'inserted': inserted,
                                'skipped': skipped,
                                'missing_name': missing_name_count,
                                'missing_id': missing_id_count,
                                'duplicate_in_position': duplicate_in_position_count,
                                'other_errors': other_error_count,
                                'position': selected_position_title
                            }
                            st.session_state.import_errors = errors
                            st.session_state.import_summary = {
                                'success_rate': (inserted / len(df) * 100) if len(df) > 0 else 0
                            }
                            
                            # Clear progress indicators
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Force rerun to show results
                            st.rerun()
                
                # Display import results if they exist (PERSISTENT)
                if st.session_state.import_results is not None:
                    results = st.session_state.import_results
                    errors = st.session_state.import_errors
                    summary = st.session_state.import_summary
                    
                    st.markdown("---")
                    st.subheader("📊 Import Results")
                    st.info(f"**Position:** {results['position']}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📊 Total Records", results['total'])
                    with col2:
                        st.metric("✅ Inserted", results['inserted'])
                    with col3:
                        st.metric("⚠️ Skipped", results['skipped'])
                    with col4:
                        st.metric("📈 Success Rate", f"{summary['success_rate']:.1f}%")
                    
                    if results['skipped'] > 0:
                        st.subheader("📋 Detailed Skip Reasons")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if results['missing_name'] > 0:
                                st.warning(f"❌ Missing Name: {results['missing_name']}")
                            else:
                                st.info("✅ No missing names")
                        with col2:
                            if results['missing_id'] > 0:
                                st.warning(f"🆔 Missing ID Number: {results['missing_id']}")
                            else:
                                st.info("✅ No missing ID numbers")
                        with col3:
                            if results['duplicate_in_position'] > 0:
                                st.error(f"⚠️ Duplicate for Same Position: {results['duplicate_in_position']}")
                                st.caption(f"These applicants already applied for '{results['position']}'")
                            else:
                                st.info("✅ No duplicates for this position")
                        with col4:
                            if results['other_errors'] > 0:
                                st.error(f"💥 System Errors: {results['other_errors']}")
                            else:
                                st.info("✅ No system errors")
                        
                        if errors:
                            with st.expander(f"📄 View all {len(errors)} error details"):
                                for err in errors[:50]:
                                    if "Missing Name" in err:
                                        st.warning(f"⚠️ {err}")
                                    elif "Missing ID Number" in err:
                                        st.warning(f"⚠️ {err}")
                                    elif "already applied" in err or "Duplicate ID" in err:
                                        st.error(f"❌ {err}")
                                    else:
                                        st.info(f"ℹ️ {err}")
                                
                                if len(errors) > 50:
                                    st.info(f"... and {len(errors) - 50} more errors")
                    
                    # Add a clear button to dismiss results
                    if st.button("🗑️ Clear Results", use_container_width=True):
                        st.session_state.import_results = None
                        st.session_state.import_errors = None
                        st.session_state.import_summary = None
                        st.rerun()
                    
                    if results['inserted'] > 0:
                        st.balloons()
            
            else:
                # Manual column mapping section (similar changes would be needed)
                st.warning("Required columns (NAME and ID NUMBER) not found. Please map columns manually.")
                
                # ... (rest of manual mapping with same duplicate logic)
                
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
    
    conn.close()
# =========================================================
# MULTI-PANELIST SCORESHEET MODULE
# =========================================================
def scoresheet_module():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">📊 Interview Scoresheet</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Embu County Public Service Board - Multi-Panelist Scoring System</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    if conn is None:
        st.error("Database connection failed")
        return
    
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    cursor = conn.cursor()
    
    # Create or verify panelists table
    try:
        if is_cloud:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS panelists (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    role TEXT,
                    email TEXT,
                    phone TEXT,
                    is_active INTEGER DEFAULT 1,
                    display_order INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS panelists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    role TEXT,
                    email TEXT,
                    phone TEXT,
                    is_active INTEGER DEFAULT 1,
                    display_order INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
        
        # Check if panelists exist, if not insert defaults
        cursor.execute("SELECT COUNT(*) FROM panelists WHERE is_active = 1")
        if cursor.fetchone()[0] == 0:
            default_panelists = [
                ("Board Member 1", "Board Member", "", "", 1, 1),
                ("Board Member 2", "Board Member", "", "", 1, 2),
                ("Board Member 3", "Board Member", "", "", 1, 3),
                ("Board Member 4", "Board Member", "", "", 1, 4),
                ("Board Member 5", "Board Member", "", "", 1, 5),
                ("Board Member 6", "Board Member", "", "", 1, 6),
                ("Board Member 7", "Board Member", "", "", 1, 7),
                ("Technical Officer", "Technical Officer", "", "", 1, 8)
            ]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for name, role, email, phone, active, order in default_panelists:
                if is_cloud:
                    cursor.execute("""
                        INSERT INTO panelists (name, role, email, phone, is_active, display_order, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (name, role, email, phone, active, order, now))
                else:
                    cursor.execute("""
                        INSERT INTO panelists (name, role, email, phone, is_active, display_order, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (name, role, email, phone, active, order, now))
            conn.commit()
    except Exception as e:
        st.error(f"Error initializing panelists: {e}")
    
    # Create scores table
    try:
        if is_cloud:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS panelist_scores (
                    id SERIAL PRIMARY KEY,
                    candidate_id INTEGER,
                    panelist_id INTEGER,
                    academic_score INTEGER,
                    hr_knowledge_score INTEGER,
                    procurement_score INTEGER,
                    gov_structure_score INTEGER,
                    leadership_score INTEGER,
                    communication_score INTEGER,
                    general_knowledge_score INTEGER,
                    technical_score INTEGER,
                    total_score REAL,
                    timestamp TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS panelist_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    panelist_id INTEGER,
                    academic_score INTEGER,
                    hr_knowledge_score INTEGER,
                    procurement_score INTEGER,
                    gov_structure_score INTEGER,
                    leadership_score INTEGER,
                    communication_score INTEGER,
                    general_knowledge_score INTEGER,
                    technical_score INTEGER,
                    total_score REAL,
                    timestamp TEXT
                )
            """)
        conn.commit()
    except Exception as e:
        st.error(f"Error creating scores table: {e}")
    
    # Get scoring criteria from database
    try:
        criteria_df = pd.read_sql("""
            SELECT criteria_key, criteria_name, max_score, description 
            FROM scoring_criteria 
            WHERE is_active = 1 
            ORDER BY id
        """, conn)
        
        if criteria_df.empty:
            st.warning("⚠️ No scoring criteria found. Please configure in System Settings > Scoring Criteria")
            # Use default criteria
            criteria = {
                "academic": {"name": "Academic and Professional Qualifications", "max_score": 10},
                "hr_knowledge": {"name": "Knowledge on Human Resource Management", "max_score": 15},
                "procurement": {"name": "Knowledge of Public Finance/Procurement", "max_score": 15},
                "gov_structure": {"name": "Government Structure & Organization Functions", "max_score": 10},
                "leadership": {"name": "Strategic Leadership Capability & Potential", "max_score": 15},
                "communication": {"name": "Communication Skills", "max_score": 5},
                "general_knowledge": {"name": "General Knowledge", "max_score": 10},
                "technical": {"name": "Knowledge/Experience in Technical Area", "max_score": 20}
            }
        else:
            # Build criteria dictionary from database
            criteria = {}
            for _, row in criteria_df.iterrows():
                criteria[row['criteria_key']] = {
                    "name": row['criteria_name'],
                    "max_score": row['max_score']
                }
    except Exception as e:
        st.error(f"Error loading scoring criteria: {e}")
        criteria = {
            "academic": {"name": "Academic and Professional Qualifications", "max_score": 10},
            "hr_knowledge": {"name": "Knowledge on Human Resource Management", "max_score": 15},
            "procurement": {"name": "Knowledge of Public Finance/Procurement", "max_score": 15},
            "gov_structure": {"name": "Government Structure & Organization Functions", "max_score": 10},
            "leadership": {"name": "Strategic Leadership Capability & Potential", "max_score": 15},
            "communication": {"name": "Communication Skills", "max_score": 5},
            "general_knowledge": {"name": "General Knowledge", "max_score": 10},
            "technical": {"name": "Knowledge/Experience in Technical Area", "max_score": 20}
        }
    
    # Get all shortlisted candidates
    try:
        shortlisted_df = pd.read_sql("""
            SELECT id, name, id_number, qualifications, experience_years, 
                   position_applied, application_status, email, contact
            FROM staff 
            WHERE application_status = 'Shortlisted' 
            ORDER BY name
        """, conn)
    except Exception as e:
        st.error(f"Error loading shortlisted candidates: {e}")
        shortlisted_df = pd.DataFrame()
    
    if shortlisted_df.empty:
        st.info("📋 No shortlisted candidates found. Please shortlist candidates first using the Shortlist Management module.")
        conn.close()
        return
    
    # Get panelists
    try:
        panelists_df = pd.read_sql("SELECT id, name, role FROM panelists WHERE is_active = 1 ORDER BY display_order", conn)
    except Exception as e:
        st.error(f"Error loading panelists: {e}")
        panelists_df = pd.DataFrame()
    
    if panelists_df.empty:
        st.warning("⚠️ No panelists found. Please add panelists in System Settings > Board Members.")
        conn.close()
        return
    
    # Create tabs - NOW WITH 5 TABS
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Select Candidate", 
        "✏️ Panelist Scoring", 
        "📊 Panelist Summary", 
        "🏆 Final Rankings",
        "✅ Successful Candidates"  # NEW TAB
    ])
    
    # Session state for selected candidate
    if 'selected_candidate_id' not in st.session_state:
        st.session_state.selected_candidate_id = None
    
    # ==================== TAB 1: SELECT CANDIDATE ====================
    with tab1:
        st.subheader("🎯 Select Candidate to Score")
        
        # Create a unique key for the selectbox to force refresh
        selected_candidate = st.selectbox(
            "Choose Candidate",
            shortlisted_df['id'].tolist(),
            format_func=lambda x: f"{shortlisted_df[shortlisted_df['id']==x]['name'].iloc[0]} - {shortlisted_df[shortlisted_df['id']==x]['position_applied'].iloc[0]}",
            key="candidate_selector_main"
        )
        
        # ALWAYS update session state when selection changes
        if st.session_state.selected_candidate_id != selected_candidate:
            st.session_state.selected_candidate_id = selected_candidate
            st.rerun()
        
        # Get the current candidate from the selectbox value, NOT from session state
        current_candidate_id = selected_candidate
        candidate = shortlisted_df[shortlisted_df['id'] == current_candidate_id].iloc[0]
        
        # Display candidate info
        st.markdown("---")
        st.subheader("📋 Candidate Information")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Name", value=candidate['name'], disabled=True, key="cand_name_display")
            st.text_input("ID Number", value=candidate['id_number'], disabled=True, key="cand_id_display")
            st.text_input("Email", value=candidate['email'] if candidate['email'] else "Not provided", disabled=True, key="cand_email")
        with col2:
            st.text_input("Position Applied", value=candidate['position_applied'], disabled=True, key="cand_position_display")
            st.text_input("Experience", value=f"{candidate['experience_years']} years" if candidate['experience_years'] else "0 years", disabled=True, key="cand_exp")
            st.text_input("Contact", value=candidate['contact'] if candidate['contact'] else "Not provided", disabled=True, key="cand_contact")
        with col3:
            st.text_input("Qualifications", value=candidate['qualifications'][:100] if candidate['qualifications'] else "N/A", disabled=True, key="cand_qual")
            st.text_input("Status", value=candidate['application_status'], disabled=True, key="cand_status")
        
        # Check scoring progress
        if is_cloud:
            cursor.execute("""
                SELECT COUNT(DISTINCT panelist_id) as scored_count, 
                       (SELECT COUNT(*) FROM panelists WHERE is_active = 1) as total_panelists
                FROM panelist_scores 
                WHERE candidate_id = %s
            """, (current_candidate_id,))
        else:
            cursor.execute("""
                SELECT COUNT(DISTINCT panelist_id) as scored_count, 
                       (SELECT COUNT(*) FROM panelists WHERE is_active = 1) as total_panelists
                FROM panelist_scores 
                WHERE candidate_id = ?
            """, (current_candidate_id,))
        result = cursor.fetchone()
        scored_count = result[0] if result[0] else 0
        total_panelists = result[1] if result[1] else len(panelists_df)
        
        st.info(f"📊 Scoring Progress: {scored_count}/{total_panelists} panelists have scored this candidate")
        
        if scored_count == total_panelists and total_panelists > 0:
            st.success("✅ All panelists have completed scoring for this candidate!")
    # ==================== TAB 2: PANELIST SCORING ====================
    with tab2:
        st.subheader("✏️ Panelist Scoring")
        
        if st.session_state.selected_candidate_id is None:
            st.warning("⚠️ Please select a candidate in the 'Select Candidate' tab first.")
        else:
            candidate_id = st.session_state.selected_candidate_id
            
            # Get candidate name
            candidate_row = shortlisted_df[shortlisted_df['id'] == candidate_id]
            if not candidate_row.empty:
                candidate_name = candidate_row['name'].iloc[0]
                st.info(f"**Scoring for:** {candidate_name}")
            
            # Calculate total max score (defined at the beginning)
            total_max_score = sum(criterion['max_score'] for criterion in criteria.values())
            
            # Get panelists who haven't scored this candidate yet
            if is_cloud:
                cursor.execute("""
                    SELECT p.id, p.name, p.role
                    FROM panelists p
                    WHERE p.id NOT IN (
                        SELECT panelist_id FROM panelist_scores WHERE candidate_id = %s
                    ) AND p.is_active = 1
                    ORDER BY p.display_order
                """, (candidate_id,))
            else:
                cursor.execute("""
                    SELECT p.id, p.name, p.role
                    FROM panelists p
                    WHERE p.id NOT IN (
                        SELECT panelist_id FROM panelist_scores WHERE candidate_id = ?
                    ) AND p.is_active = 1
                    ORDER BY p.display_order
                """, (candidate_id,))
            
            available_panelists = cursor.fetchall()
            
            # Get panelists who have already scored
            if is_cloud:
                cursor.execute("""
                    SELECT p.id, p.name, p.role, ps.total_score
                    FROM panelists p
                    JOIN panelist_scores ps ON p.id = ps.panelist_id
                    WHERE ps.candidate_id = %s
                    ORDER BY ps.total_score DESC
                """, (candidate_id,))
            else:
                cursor.execute("""
                    SELECT p.id, p.name, p.role, ps.total_score
                    FROM panelists p
                    JOIN panelist_scores ps ON p.id = ps.panelist_id
                    WHERE ps.candidate_id = ?
                    ORDER BY ps.total_score DESC
                """, (candidate_id,))
            completed_panelists = cursor.fetchall()
            
            if available_panelists:
                st.markdown("### Select Panelist to Score")
                panelist_options = {p[0]: f"{p[1]} ({p[2]})" for p in available_panelists}
                selected_panelist = st.selectbox(
                    "Panelist",
                    list(panelist_options.keys()),
                    format_func=lambda x: panelist_options[x],
                    key="panelist_selector"
                )
                
                if selected_panelist:
                    panelist_name = panelist_options[selected_panelist]
                    
                    st.markdown("---")
                    st.markdown(f"### 📝 Scoring by: {panelist_name}")
                    
                    # Scoring Criteria Section - USING DATABASE VALUES
                    st.markdown("#### Detailed Criteria Assessment")
                    st.info("Rate each criterion based on the candidate's performance")
                    
                    scores = {}
                    total_panelist_score = 0
                    
                    # Display total max score
                    st.markdown(f"**Total Possible Score: {total_max_score} points**")
                    st.markdown("---")
                    
                    # Create columns for criteria
                    col1, col2 = st.columns(2)
                    
                    # Display each criterion
                    for idx, (key, criterion) in enumerate(criteria.items()):
                        with col1 if idx % 2 == 0 else col2:
                            st.markdown(f"**{criterion['name']}**")
                            st.caption(f"Max: {criterion['max_score']} points")
                            
                            score = st.number_input(
                                f"Score for {criterion['name'][:30]}",
                                min_value=0,
                                max_value=criterion['max_score'],
                                value=0,
                                step=1,
                                key=f"{key}_{candidate_id}_{selected_panelist}",
                                label_visibility="collapsed"
                            )
                            
                            scores[key] = score
                            total_panelist_score += score
                            
                            # Show rating
                            percentage = (score / criterion['max_score']) * 100 if criterion['max_score'] > 0 else 0
                            if percentage >= 70:
                                st.markdown("🟢 Good")
                            elif percentage >= 50:
                                st.markdown("🟡 Average")
                            else:
                                st.markdown("🔴 Limited")
                            
                            st.markdown("---")
                    
                    # Display total for this panelist
                    st.subheader(f"📊 {panelist_name}'s Total Score")
                    st.metric("Panelist Score", f"{total_panelist_score}/{total_max_score}")
                    
                    # Submit button
                    if st.button(f"💾 Submit {panelist_name}'s Scores", use_container_width=True, type="primary"):
                        if is_cloud:
                            cursor.execute("""
                                INSERT INTO panelist_scores (
                                    candidate_id, panelist_id, academic_score, hr_knowledge_score,
                                    procurement_score, gov_structure_score, leadership_score,
                                    communication_score, general_knowledge_score, technical_score,
                                    total_score, timestamp
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                candidate_id, selected_panelist,
                                scores.get('academic', 0), scores.get('hr_knowledge', 0),
                                scores.get('procurement', 0), scores.get('gov_structure', 0),
                                scores.get('leadership', 0), scores.get('communication', 0),
                                scores.get('general_knowledge', 0), scores.get('technical', 0),
                                total_panelist_score,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ))
                        else:
                            cursor.execute("""
                                INSERT INTO panelist_scores (
                                    candidate_id, panelist_id, academic_score, hr_knowledge_score,
                                    procurement_score, gov_structure_score, leadership_score,
                                    communication_score, general_knowledge_score, technical_score,
                                    total_score, timestamp
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                candidate_id, selected_panelist,
                                scores.get('academic', 0), scores.get('hr_knowledge', 0),
                                scores.get('procurement', 0), scores.get('gov_structure', 0),
                                scores.get('leadership', 0), scores.get('communication', 0),
                                scores.get('general_knowledge', 0), scores.get('technical', 0),
                                total_panelist_score,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ))
                        conn.commit()
                        
                        st.success(f"✅ Scores submitted for {panelist_name}!")
                        st.balloons()
                        st.rerun()
            
            elif completed_panelists:
                st.info("✅ All panelists have already scored this candidate!")
                st.markdown("### 📋 Completed Panelists:")
                for p in completed_panelists:
                    st.write(f"- {p[1]} ({p[2]}): Score = {p[3]}/{total_max_score}")
            else:
                st.warning("No panelists available. Please add panelists in System Settings > Board Members.")
    
    # ==================== TAB 3: PANELIST SUMMARY ====================
    with tab3:
        st.subheader("📊 Panelist Scores Summary")
        
        if st.session_state.selected_candidate_id is None:
            st.warning("⚠️ Please select a candidate in the 'Select Candidate' tab first.")
        else:
            candidate_id = st.session_state.selected_candidate_id
            candidate_name = shortlisted_df[shortlisted_df['id'] == candidate_id]['name'].iloc[0]
            
            st.info(f"**Scores for:** {candidate_name}")
            
            try:
                scores_df = pd.read_sql(f"""
                    SELECT p.name as panelist_name, p.role,
                           ps.academic_score, ps.hr_knowledge_score, ps.procurement_score,
                           ps.gov_structure_score, ps.leadership_score, ps.communication_score,
                           ps.general_knowledge_score, ps.technical_score, ps.total_score,
                           ps.timestamp
                    FROM panelist_scores ps
                    JOIN panelists p ON ps.panelist_id = p.id
                    WHERE ps.candidate_id = {candidate_id}
                    ORDER BY ps.total_score DESC
                """, conn)
                
                if scores_df.empty:
                    st.info("No scores have been submitted yet.")
                else:
                    st.markdown("### Individual Panelist Scores")
                    
                    for idx, row in scores_df.iterrows():
                        with st.expander(f"{row['panelist_name']} ({row['role']}) - Score: {row['total_score']}/100"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Academic Qualifications:**", row['academic_score'])
                                st.write("**HR Knowledge:**", row['hr_knowledge_score'])
                                st.write("**Procurement Knowledge:**", row['procurement_score'])
                                st.write("**Government Structure:**", row['gov_structure_score'])
                            with col2:
                                st.write("**Leadership:**", row['leadership_score'])
                                st.write("**Communication:**", row['communication_score'])
                                st.write("**General Knowledge:**", row['general_knowledge_score'])
                                st.write("**Technical Knowledge:**", row['technical_score'])
                            st.caption(f"Submitted: {row['timestamp']}")
                    
                    st.markdown("---")
                    st.subheader("🎯 Overall Candidate Score")
                    
                    panelist_scores_list = scores_df['total_score'].tolist()
                    overall_score = sum(panelist_scores_list) / len(panelist_scores_list)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Number of Panelists", len(panelist_scores_list))
                    with col2:
                        st.metric("Highest Score", max(panelist_scores_list))
                    with col3:
                        st.metric("Lowest Score", min(panelist_scores_list))
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0f2b42 100%); 
                                padding: 2rem; border-radius: 12px; text-align: center; margin: 1rem 0;">
                        <h2 style="color: white; margin: 0;">Overall Candidate Score</h2>
                        <h1 style="color: white; font-size: 4rem; margin: 0;">{overall_score:.1f}</h1>
                        <p style="color: rgba(255,255,255,0.8);">out of 100</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Update both interview_score AND application_status
                    if is_cloud:
                        cursor.execute("""
                            UPDATE staff 
                            SET interview_score = %s, 
                                application_status = 'Interviewed'
                            WHERE id = %s
                        """, (overall_score, candidate_id))
                    else:
                        cursor.execute("""
                            UPDATE staff 
                            SET interview_score = ?, 
                                application_status = 'Interviewed'
                            WHERE id = ?
                        """, (overall_score, candidate_id))
                    conn.commit()
                    
                    st.success(f"✅ Candidate status updated to 'Interviewed' with score: {overall_score:.1f}")
                    
                    csv = scores_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Panelist Scores",
                        csv,
                        f"panelist_scores_{candidate_id}.csv",
                        "text/csv"
                    )
            except Exception as e:
                st.error(f"Error loading scores: {e}")
    
    # ==================== TAB 4: FINAL RANKINGS ====================
    with tab4:
        st.subheader("🏆 Final Candidate Rankings")
        
        try:
            # Fixed query for PostgreSQL - cast to NUMERIC before rounding
            ranked_df = pd.read_sql("""
                SELECT 
                    s.id, 
                    s.name, 
                    s.id_number, 
                    s.position_applied, 
                    'Interviewed' as application_status,
                    ROUND(CAST(AVG(ps.total_score) AS NUMERIC), 2) as interview_score
                FROM staff s
                INNER JOIN panelist_scores ps ON s.id = ps.candidate_id
                GROUP BY s.id, s.name, s.id_number, s.position_applied
                ORDER BY interview_score DESC
            """, conn)
            
            if ranked_df.empty:
                st.info("No candidates have been scored yet.")
            else:
                ranked_df['Rank'] = ranked_df['interview_score'].rank(method='min', ascending=False).astype(int)
                
                st.dataframe(
                    ranked_df[['Rank', 'name', 'id_number', 'position_applied', 'interview_score', 'application_status']],
                    use_container_width=True,
                    height=600
                )
                
                # Export rankings
                csv = ranked_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Final Rankings (CSV)",
                    csv,
                    f"final_rankings_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        except Exception as e:
            st.error(f"Error loading rankings: {e}")
    # ==================== TAB 5: SUCCESSFUL CANDIDATES ====================
    with tab5:
        st.subheader("✅ Successful Candidates")
        st.info("Candidates recommended for appointment based on final rankings and available vacancies")
        
        try:
            # Get the position of the selected candidate to determine vacancies
            if st.session_state.selected_candidate_id is not None:
                current_candidate_id = st.session_state.selected_candidate_id
                # Get position title from the candidate
                pos_query = f"SELECT position_applied FROM staff WHERE id = {current_candidate_id}"
                position_result = pd.read_sql(pos_query, conn)
                if not position_result.empty:
                    position_title = position_result.iloc[0]['position_applied']
                else:
                    position_title = None
            else:
                # If no candidate selected, try to get from first shortlisted candidate
                if not shortlisted_df.empty:
                    position_title = shortlisted_df.iloc[0]['position_applied']
                else:
                    position_title = None
            
            # Get the number of vacancies for this position
            vacancies = 1  # Default
            if position_title:
                try:
                    vac_query = """
                        SELECT vacancies FROM advertised_positions 
                        WHERE position_title = %s AND status = 'Open'
                        ORDER BY id DESC LIMIT 1
                    """
                    if is_cloud:
                        vac_df = pd.read_sql(vac_query, conn, params=(position_title,))
                    else:
                        vac_df = pd.read_sql(vac_query.replace('%s', '?'), conn, params=(position_title,))
                    
                    if not vac_df.empty:
                        vacancies = int(vac_df.iloc[0]['vacancies'])
                except:
                    vacancies = 1
            
            st.info(f"📊 **Position:** {position_title if position_title else 'N/A'} | **Number of Vacancies:** {vacancies}")
            
            # Get ranked candidates
            ranked_df = pd.read_sql("""
                SELECT 
                    s.id, 
                    s.name, 
                    s.id_number, 
                    s.position_applied, 
                    s.contact,
                    s.email,
                    ROUND(CAST(AVG(ps.total_score) AS NUMERIC), 2) as interview_score
                FROM staff s
                INNER JOIN panelist_scores ps ON s.id = ps.candidate_id
                GROUP BY s.id, s.name, s.id_number, s.position_applied, s.contact, s.email
                ORDER BY interview_score DESC
            """, conn)
            
            if ranked_df.empty:
                st.info("No candidates have been scored yet. Please complete scoring in the tabs above.")
            else:
                # Add rank
                ranked_df['Rank'] = ranked_df['interview_score'].rank(method='min', ascending=False).astype(int)
                
                # Get successful candidates (top N based on vacancies)
                successful_df = ranked_df.head(vacancies).copy()
                
                # Display summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Candidates Interviewed", len(ranked_df))
                with col2:
                    st.metric("Number of Vacancies", vacancies)
                with col3:
                    st.metric("Successful Candidates", len(successful_df))
                
                st.markdown("---")
                
                if not successful_df.empty:
                    st.success(f"✅ **RECOMMENDED FOR APPOINTMENT** - Top {len(successful_df)} Candidate(s)")
                    
                    # Display successful candidates in a nice format
                    for idx, row in successful_df.iterrows():
                        with st.container():
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, #1e3a5f 0%, #0f2b42 100%);
                                padding: 1rem;
                                border-radius: 12px;
                                margin-bottom: 1rem;
                                border-left: 5px solid #10b981;
                            ">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <h3 style="color: white; margin: 0;">🥇 Rank #{row['Rank']} - {row['name']}</h3>
                                        <p style="color: #cbd5e1; margin: 0.5rem 0 0 0;">
                                            📧 {row['email'] if row['email'] else 'No email'} | 📞 {row['contact'] if row['contact'] else 'No phone'}
                                        </p>
                                    </div>
                                    <div style="text-align: right;">
                                        <p style="color: #10b981; font-size: 1.5rem; font-weight: bold; margin: 0;">{row['interview_score']}%</p>
                                        <p style="color: #94a3b8; margin: 0;">Score</p>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Display table format
                    st.markdown("### 📋 Successful Candidates List")
                    st.dataframe(
                        successful_df[['Rank', 'name', 'id_number', 'contact', 'email', 'interview_score']],
                        use_container_width=True
                    )
                    
                    # Update their status to 'Recommended'
                    for idx, row in successful_df.iterrows():
                        if is_cloud:
                            cursor.execute("""
                                UPDATE staff 
                                SET application_status = 'Recommended'
                                WHERE id = %s AND application_status != 'Recommended'
                            """, (row['id'],))
                        else:
                            cursor.execute("""
                                UPDATE staff 
                                SET application_status = 'Recommended'
                                WHERE id = ? AND application_status != 'Recommended'
                            """, (row['id'],))
                    conn.commit()
                    
                    st.success(f"✅ {len(successful_df)} candidate(s) have been marked as 'Recommended'")
                    
                    # Export successful candidates
                    csv = successful_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Successful Candidates (CSV)",
                        csv,
                        f"successful_candidates_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )
                else:
                    st.warning("No successful candidates to display.")
                    
                # Show remaining candidates (not successful)
                if len(ranked_df) > vacancies:
                    remaining_df = ranked_df.iloc[vacancies:].copy()
                    with st.expander(f"📋 Other Candidates ({len(remaining_df)} not recommended)"):
                        st.dataframe(
                            remaining_df[['Rank', 'name', 'id_number', 'contact', 'interview_score']],
                            use_container_width=True
                        )
                        
        except Exception as e:
            st.error(f"Error loading successful candidates: {e}")
# =========================================================
# CREATE MISSING TABLES FOR SCORESHEET
# =========================================================
def create_scoresheet_tables():
    """Create all tables needed for the scoresheet module - PostgreSQL & SQLite compatible"""
    conn = get_conn()
    if conn is None:
        return
    
    c = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    if is_cloud:
        # ===========================================
        # POSTGRESQL SYNTAX
        # ===========================================
        
        # Create panelists table
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelists (
            id SERIAL PRIMARY KEY,
            name TEXT,
            role TEXT,
            email TEXT,
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
        
        # Add missing columns to panelists if they don't exist
        try:
            c.execute("ALTER TABLE panelists ADD COLUMN IF NOT EXISTS email TEXT")
        except:
            pass
        try:
            c.execute("ALTER TABLE panelists ADD COLUMN IF NOT EXISTS phone TEXT")
        except:
            pass
        
        # Create scoring_criteria table
        c.execute("""
        CREATE TABLE IF NOT EXISTS scoring_criteria (
            id SERIAL PRIMARY KEY,
            criteria_key TEXT UNIQUE,
            criteria_name TEXT,
            max_score INTEGER,
            description TEXT,
            is_active INTEGER DEFAULT 1
        )
        """)
        
        # Create scoring_parameters table
        c.execute("""
        CREATE TABLE IF NOT EXISTS scoring_parameters (
            id SERIAL PRIMARY KEY,
            param_key TEXT UNIQUE,
            param_name TEXT,
            param_value TEXT,
            description TEXT
        )
        """)
        
        # Create panelist_scores table
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelist_scores (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER,
            panelist_id INTEGER,
            academic_score INTEGER,
            hr_knowledge_score INTEGER,
            procurement_score INTEGER,
            gov_structure_score INTEGER,
            leadership_score INTEGER,
            communication_score INTEGER,
            general_knowledge_score INTEGER,
            technical_score INTEGER,
            total_score REAL,
            timestamp TEXT
        )
        """)
        
        # Check if panelists exist, if not insert defaults
        c.execute("SELECT COUNT(*) FROM panelists")
        if c.fetchone()[0] == 0:
            default_panelists = [
                ("Board Member 1", "Board Member", "", "", 1, 1),
                ("Board Member 2", "Board Member", "", "", 1, 2),
                ("Board Member 3", "Board Member", "", "", 1, 3),
                ("Board Member 4", "Board Member", "", "", 1, 4),
                ("Board Member 5", "Board Member", "", "", 1, 5),
                ("Board Member 6", "Board Member", "", "", 1, 6),
                ("Board Member 7", "Board Member", "", "", 1, 7),
                ("Technical Officer", "Technical Officer", "", "", 1, 8)
            ]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for name, role, email, phone, active, order in default_panelists:
                c.execute("""
                    INSERT INTO panelists (name, role, email, phone, is_active, display_order, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (name, role, email, phone, active, order, now))
        
        # Check if scoring_criteria exist, if not insert defaults
        c.execute("SELECT COUNT(*) FROM scoring_criteria")
        if c.fetchone()[0] == 0:
            default_criteria = [
                ("academic", "Academic and Professional Qualifications", 5, "Degree, Certificate, Form Four, Computer skills"),
                ("hr_knowledge", "Knowledge on Human Resource Management", 15, "Understanding of HR principles and practices"),
                ("procurement", "Knowledge of Public Finance/Procurement", 15, "Understanding of PPADA and public finance"),
                ("gov_structure", "Government Structure & Organization Functions", 10, "Knowledge of county and national government"),
                ("leadership", "Strategic Leadership Capability & Potential", 10, "Leadership qualities and strategic thinking"),
                ("communication", "Communication Skills", 5, "Verbal and written communication abilities"),
                ("general_knowledge", "General Knowledge (National, Regional & Global)", 5, "Awareness of current affairs"),
                ("technical", "Knowledge/Experience in Technical Area", 35, "Specialized expertise for the position")
            ]
            for criteria in default_criteria:
                c.execute("""
                    INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
                    VALUES (%s, %s, %s, %s, 1)
                """, criteria)
        
        # Check if scoring_parameters exist, if not insert defaults
        c.execute("SELECT COUNT(*) FROM scoring_parameters")
        if c.fetchone()[0] == 0:
            default_params = [
                ("pass_mark", "Passing Score", "70", "Minimum score required to be considered for hiring"),
                ("distinction_mark", "Distinction Score", "85", "Score for exceptional performance"),
                ("interview_weight", "Interview Weight (%)", "70", "Weight of interview score in final calculation"),
                ("criteria_weight", "Criteria Weight (%)", "30", "Weight of criteria score in final calculation"),
                ("max_panelists", "Maximum Panelists", "8", "Number of panelists expected to score"),
                ("min_panelists_required", "Minimum Panelists Required", "5", "Minimum panelists needed for valid score"),
                ("shortlist_score", "Auto-Shortlist Score", "70", "Score above which candidates are auto-shortlisted"),
                ("reject_score", "Auto-Reject Score", "40", "Score below which candidates are auto-rejected")
            ]
            for param in default_params:
                c.execute("""
                    INSERT INTO scoring_parameters (param_key, param_name, param_value, description)
                    VALUES (%s, %s, %s, %s)
                """, param)
    
    else:
        # ===========================================
        # SQLITE SYNTAX (for local development)
        # ===========================================
        
        # Create panelists table
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            email TEXT,
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
        
        # Create scoring_criteria table
        c.execute("""
        CREATE TABLE IF NOT EXISTS scoring_criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            criteria_key TEXT UNIQUE,
            criteria_name TEXT,
            max_score INTEGER,
            description TEXT,
            is_active INTEGER DEFAULT 1
        )
        """)
        
        # Create scoring_parameters table
        c.execute("""
        CREATE TABLE IF NOT EXISTS scoring_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            param_key TEXT UNIQUE,
            param_name TEXT,
            param_value TEXT,
            description TEXT
        )
        """)
        
        # Create panelist_scores table
        c.execute("""
        CREATE TABLE IF NOT EXISTS panelist_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            panelist_id INTEGER,
            academic_score INTEGER,
            hr_knowledge_score INTEGER,
            procurement_score INTEGER,
            gov_structure_score INTEGER,
            leadership_score INTEGER,
            communication_score INTEGER,
            general_knowledge_score INTEGER,
            technical_score INTEGER,
            total_score REAL,
            timestamp TEXT
        )
        """)
        
        # Check if panelists exist, if not insert defaults
        c.execute("SELECT COUNT(*) FROM panelists")
        if c.fetchone()[0] == 0:
            default_panelists = [
                ("Board Member 1", "Board Member", "", "", 1, 1),
                ("Board Member 2", "Board Member", "", "", 1, 2),
                ("Board Member 3", "Board Member", "", "", 1, 3),
                ("Board Member 4", "Board Member", "", "", 1, 4),
                ("Board Member 5", "Board Member", "", "", 1, 5),
                ("Board Member 6", "Board Member", "", "", 1, 6),
                ("Board Member 7", "Board Member", "", "", 1, 7),
                ("Technical Officer", "Technical Officer", "", "", 1, 8)
            ]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for name, role, email, phone, active, order in default_panelists:
                c.execute("""
                    INSERT INTO panelists (name, role, email, phone, is_active, display_order, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, role, email, phone, active, order, now))
        
        # Check if scoring_criteria exist, if not insert defaults
        c.execute("SELECT COUNT(*) FROM scoring_criteria")
        if c.fetchone()[0] == 0:
            default_criteria = [
                ("academic", "Academic and Professional Qualifications", 5, "Degree, Certificate, Form Four, Computer skills"),
                ("hr_knowledge", "Knowledge on Human Resource Management", 15, "Understanding of HR principles and practices"),
                ("procurement", "Knowledge of Public Finance/Procurement", 15, "Understanding of PPADA and public finance"),
                ("gov_structure", "Government Structure & Organization Functions", 10, "Knowledge of county and national government"),
                ("leadership", "Strategic Leadership Capability & Potential", 10, "Leadership qualities and strategic thinking"),
                ("communication", "Communication Skills", 5, "Verbal and written communication abilities"),
                ("general_knowledge", "General Knowledge (National, Regional & Global)", 5, "Awareness of current affairs"),
                ("technical", "Knowledge/Experience in Technical Area", 35, "Specialized expertise for the position")
            ]
            for criteria in default_criteria:
                c.execute("""
                    INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, criteria)
        
        # Check if scoring_parameters exist, if not insert defaults
        c.execute("SELECT COUNT(*) FROM scoring_parameters")
        if c.fetchone()[0] == 0:
            default_params = [
                ("pass_mark", "Passing Score", "70", "Minimum score required to be considered for hiring"),
                ("distinction_mark", "Distinction Score", "85", "Score for exceptional performance"),
                ("interview_weight", "Interview Weight (%)", "70", "Weight of interview score in final calculation"),
                ("criteria_weight", "Criteria Weight (%)", "30", "Weight of criteria score in final calculation"),
                ("max_panelists", "Maximum Panelists", "8", "Number of panelists expected to score"),
                ("min_panelists_required", "Minimum Panelists Required", "5", "Minimum panelists needed for valid score"),
                ("shortlist_score", "Auto-Shortlist Score", "70", "Score above which candidates are auto-shortlisted"),
                ("reject_score", "Auto-Reject Score", "40", "Score below which candidates are auto-rejected")
            ]
            for param in default_params:
                c.execute("""
                    INSERT INTO scoring_parameters (param_key, param_name, param_value, description)
                    VALUES (?, ?, ?, ?)
                """, param)
    
    conn.commit()
    conn.close()
    print("✅ Scoresheet tables created successfully!")

def fix_missing_columns():
    """Fix missing columns in existing tables"""
    conn = get_conn()
    if conn is None:
        return
    
    c = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    if is_cloud:
        # PostgreSQL - Add missing columns to staff table
        columns_to_add = [
            ("advertisement_ref", "TEXT"),
            ("email", "TEXT"),
            ("kcse_grade", "TEXT"),
            ("institution", "TEXT"),
            ("graduation_year", "INTEGER"),
            ("professional_body", "TEXT"),
            ("experience_years", "INTEGER"),
            ("current_employer", "TEXT"),
            ("referee1_name", "TEXT"),
            ("referee1_contact", "TEXT"),
            ("referee2_name", "TEXT"),
            ("referee2_contact", "TEXT"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                c.execute(f"ALTER TABLE staff ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            except:
                pass
    else:
        # SQLite - Add missing columns
        c.execute("PRAGMA table_info(staff)")
        existing_cols = [col[1] for col in c.fetchall()]
        
        columns_to_add = [
            ("advertisement_ref", "TEXT"),
            ("email", "TEXT"),
            ("kcse_grade", "TEXT"),
            ("institution", "TEXT"),
            ("graduation_year", "INTEGER"),
            ("professional_body", "TEXT"),
            ("experience_years", "INTEGER"),
            ("current_employer", "TEXT"),
            ("referee1_name", "TEXT"),
            ("referee1_contact", "TEXT"),
            ("referee2_name", "TEXT"),
            ("referee2_contact", "TEXT"),
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_cols:
                try:
                    c.execute(f"ALTER TABLE staff ADD COLUMN {col_name} {col_type}")
                except:
                    pass
    
    conn.commit()
    conn.close()
    print("✅ Missing columns fixed!")

# Call this function in main() after init_db()
# =========================================================
# MAIN APPLICATION
# =========================================================
def main():
    import time
    app_start = time.time()
    
    apply_theme()
    
    # ============================================
    # HANDLE PASSWORD RESET TOKEN (UPDATED)
    # ============================================
    # Get query parameters using the latest Streamlit method
    query_params = st.query_params
    
    # Check if reset_token exists in URL
    if "reset_token" in query_params:
        token = query_params["reset_token"]
        
        st.markdown("""
        <div style="text-align: center; padding: 40px;">
            <h1 style="color: #1e3a5f;">🔐 Reset Password</h1>
            <p style="color: #64748b;">Enter your new password below</p>
        </div>
        """, unsafe_allow_html=True)
        
        conn = get_conn()
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        try:
            # Verify token
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if is_cloud:
                cursor.execute("""
                    SELECT username FROM users 
                    WHERE reset_token = %s AND reset_token_expiry > %s
                """, (token, current_time))
            else:
                cursor.execute("""
                    SELECT username FROM users 
                    WHERE reset_token = ? AND reset_token_expiry > ?
                """, (token, current_time))
            
            user = cursor.fetchone()
            
            if user:
                username = user[0]
                
                with st.form("reset_form"):
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        new_password = st.text_input("New Password", type="password", placeholder="Enter new password", key="reset_new_pwd")
                        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password", key="reset_confirm_pwd")
                        
                        submitted = st.form_submit_button("Reset Password", use_container_width=True, type="primary")
                        
                        if submitted:
                            if not new_password:
                                st.error("❌ Password cannot be empty")
                            elif len(new_password) < 4:
                                st.error("❌ Password must be at least 4 characters")
                            elif new_password != confirm_password:
                                st.error("❌ Passwords do not match")
                            else:
                                hashed_password = hash_password(new_password)
                                
                                if is_cloud:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET password = %s, reset_token = NULL, reset_token_expiry = NULL 
                                        WHERE username = %s
                                    """, (hashed_password, username))
                                else:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET password = ?, reset_token = NULL, reset_token_expiry = NULL 
                                        WHERE username = ?
                                    """, (hashed_password, username))
                                
                                conn.commit()
                                
                                log_audit(username, "PASSWORD_RESET", 0, "Password reset via link", "Success")
                                
                                st.success("✅ Password reset successfully!")
                                st.info("You can now login with your new password.")
                                
                                # Clear the URL parameter
                                st.query_params.clear()
                                
                                if st.button("Go to Login", use_container_width=True):
                                    st.rerun()
            else:
                st.error("❌ Invalid or expired reset link. Please request a new one.")
                if st.button("Request New Reset Link", use_container_width=True):
                    st.query_params.clear()
                    st.session_state.show_forgot_password = True
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            conn.close()
        
        return  # Stop here
    # ============================================
    # WHATSAPP WEBHOOK HANDLER (for Africa's Talking)
    # ============================================
    query_params = st.query_params
    
    if "webhook" in query_params and query_params["webhook"] == "africastalking":
        # This is a webhook request from Africa's Talking
        import json
        
        # Get parameters (adjust based on Africa's Talking format)
        phone_number = query_params.get("from", [""])[0]
        message = query_params.get("text", [""])[0]
        
        if phone_number and message:
            assistant = WhatsAppHRAssistant()
            response = assistant.process_message(phone_number, message)
            
            # Return response as JSON
            st.json({"response": response})
            return
    # ============================================
    # ONLY INIT DB ONCE PER SESSION
    # ============================================
    if 'db_initialized' not in st.session_state:
        st.session_state.db_initialized = False
    
    if not st.session_state.db_initialized:
        init_start = time.time()
        init_db()
        create_settings_tables()
        create_scoresheet_tables()      
        migrate_database()
        ensure_database_columns()
        create_default_admin()
        st.session_state.db_initialized = True
        print(f"✅ Database initialized (first run): {time.time() - init_start:.3f}s")
    else:
        print("⏭️ Database already initialized - skipping")
    
    # ============================================
    # KEEP-ALIVE MECHANISM (Prevents Neon from suspending)
    # ============================================
def main():
    import time
    app_start = time.time()
    
    apply_theme()
    
    # ============================================
    # HANDLE PASSWORD RESET TOKEN - FIXED VERSION
    # ============================================
    # Try multiple methods to get query parameters
    token = None
    
    # Method 1: Try st.query_params (Streamlit >= 1.30)
    try:
        if hasattr(st, 'query_params') and st.query_params:
            if 'reset_token' in st.query_params:
                token = st.query_params['reset_token']
    except:
        pass
    
    # Method 2: Try experimental_get_query_params (older versions)
    if not token:
        try:
            params = st.experimental_get_query_params()
            if 'reset_token' in params:
                token = params['reset_token'][0]
        except:
            pass
    
    # Method 3: Try reading from URL directly (fallback)
    if not token:
        import urllib.parse
        current_url = st.experimental_get_query_params() if hasattr(st, 'experimental_get_query_params') else {}
        if 'reset_token' in current_url:
            token = current_url['reset_token'][0]
    
    # If token exists, show reset form
    if token:
        st.markdown("""
        <div style="text-align: center; padding: 40px;">
            <h1 style="color: #1e3a5f;">🔐 Reset Password</h1>
            <p style="color: #64748b;">Enter your new password below</p>
        </div>
        """, unsafe_allow_html=True)
        
        conn = get_conn()
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Verify token
            if is_cloud:
                cursor.execute("""
                    SELECT username FROM users 
                    WHERE reset_token = %s AND reset_token_expiry > %s
                """, (token, current_time))
            else:
                cursor.execute("""
                    SELECT username FROM users 
                    WHERE reset_token = ? AND reset_token_expiry > ?
                """, (token, current_time))
            
            user = cursor.fetchone()
            
            if user:
                username = user[0]
                
                # Center the form
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    with st.form("reset_password_form"):
                        new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password")
                        
                        submitted = st.form_submit_button("Reset Password", use_container_width=True, type="primary")
                        
                        if submitted:
                            if not new_password:
                                st.error("❌ Password cannot be empty")
                            elif len(new_password) < 4:
                                st.error("❌ Password must be at least 4 characters")
                            elif new_password != confirm_password:
                                st.error("❌ Passwords do not match")
                            else:
                                hashed_password = hash_password(new_password)
                                
                                if is_cloud:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET password = %s, reset_token = NULL, reset_token_expiry = NULL 
                                        WHERE username = %s
                                    """, (hashed_password, username))
                                else:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET password = ?, reset_token = NULL, reset_token_expiry = NULL 
                                        WHERE username = ?
                                    """, (hashed_password, username))
                                
                                conn.commit()
                                
                                log_audit(username, "PASSWORD_RESET", 0, "Password reset via link", "Success")
                                
                                st.success("✅ Password reset successfully!")
                                st.info("You can now login with your new password. Click the link below to go to login.")
                                
                                # Clear the URL
                                try:
                                    st.query_params.clear()
                                except:
                                    pass
                                
                                # Create a login link instead of a button (avoids form issues)
                                st.markdown("""
                                <div style="text-align: center; margin-top: 20px;">
                                    <a href="https://embucountypublicserviceboardsystem.streamlit.app" target="_self" style="background: #4f7cff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px;">Go to Login</a>
                                </div>
                                """, unsafe_allow_html=True)
            else:
                st.error("❌ Invalid or expired reset link. Please request a new one.")
                if st.button("Request New Reset Link", use_container_width=True):
                    try:
                        st.query_params.clear()
                    except:
                        pass
                    st.session_state.show_forgot_password = True
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            conn.close()
        
        return  # STOP HERE
    
    # ============================================
    # REST OF YOUR MAIN() FUNCTION CONTINUES HERE
    # ============================================
    # ONLY INIT DB ONCE PER SESSION
    if 'db_initialized' not in st.session_state:
        st.session_state.db_initialized = False
    
    if not st.session_state.db_initialized:
        init_start = time.time()
        init_db()
        create_settings_tables()
        create_scoresheet_tables()      
        migrate_database()
        ensure_database_columns()
        create_default_admin()
        st.session_state.db_initialized = True
        print(f"✅ Database initialized: {time.time() - init_start:.3f}s")
    else:
        print("⏭️ Database already initialized - skipping")
    
    # Keep-alive mechanism
    def keep_alive():
        try:
            conn = get_conn()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
        except:
            pass
    
    keep_alive()
    
    # Check login status
    if "user" not in st.session_state or st.session_state.user is None:
        login()
        return
    
    # Sidebar toggle
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False
    
    sidebar_toggle_button()
    
    # Get menu
    menu = sidebar()
    
    if menu is None and 'selected_menu' in st.session_state:
        menu = st.session_state.selected_menu
    elif menu is not None:
        st.session_state.selected_menu = menu
    
    # Router
    if menu == "📊 Dashboard":
        dashboard()
    elif menu == "👥 Applicant Profile":
        applicant_profile()
    elif menu == "📝 Applicant Registration":
        data_entry()
    elif menu == "✏️ Edit Application":
        edit_applicant()
    elif menu == "⭐ Shortlist Management":
        shortlist_management()
    elif menu == "📊 Scoresheet":
        scoresheet_module()
    elif menu == "📈 Position Dashboard":
        position_dashboard()
    elif menu == "👔 HR Functions":  
        hr_dashboard()
    elif menu == "📥 Import Excel":
        import_excel()
    elif menu == "📋 Records":
        records()
    elif menu == "📈 Reports":
        reports()
    elif menu == "⭐ Review":
        review_module()
    elif menu == "📤 Export Center":
        export_center()
    elif menu == "✅ Data Quality":
        data_quality()
    elif menu == "🔒 Audit Trail":
        audit_trail()
    elif menu == "💾 Backup & Restore":
        backup_restore()
    elif menu == "🧪 Test Data":
        generate_test_data()
    elif menu == "⚙️ Settings":
        system_settings()
    elif menu == "👤 Users":
        users()
    else:
        dashboard()
    
    total_time = time.time() - app_start
    if total_time > 1.0 and not st.session_state.sidebar_collapsed:
        st.sidebar.markdown(f"---\n⏱️ **Load Time:** {total_time:.1f}s")


# =========================================================
# RUN APPLICATION
# =========================================================
if __name__ == "__main__":
    main()
