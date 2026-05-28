import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, timedelta, date  # ← Added 'date'
import traceback
import plotly.express as px
import plotly.graph_objects as go
import io
import shutil
import psycopg2  
import os
import random

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
    """Create default admin user if doesn't exist"""
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
            # Insert admin user with lowercase username
            admin_password = hash_password("cpsb123")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if is_cloud:
                c.execute("""
                    INSERT INTO users (username, password, role, created_at)
                    VALUES (%s, %s, %s, %s)
                """, ("admin", admin_password, "Admin", created_at))
            else:
                c.execute("""
                    INSERT INTO users (username, password, role, created_at)
                    VALUES (?, ?, ?, ?)
                """, ("admin", admin_password, "Admin", created_at))
            
            conn.commit()
            print("✅ Default admin user created (username: admin, password: cpsb123)")
    
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        conn.close()

def login_user(username, password):
    conn = get_conn()
    if conn is None:
        return None
    
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    
    # Convert username to lowercase for case-insensitive comparison
    username_lower = username.lower()
    
    # Check if using PostgreSQL (cloud) or SQLite (local)
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    try:
        if is_cloud:
            # PostgreSQL syntax - search by lowercase username
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = %s AND password = %s", (username_lower, hashed_password))
        else:
            # SQLite syntax - search by lowercase username
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = ? AND password = ?", (username_lower, hashed_password))
        
        user = cursor.fetchone()
        conn.close()
        return user
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
    
    # Create tabs for HR modules - UPDATED with 10 tabs
    hr_tab1, hr_tab2, hr_tab3, hr_tab4, hr_tab5, hr_tab6, hr_tab7, hr_tab8, hr_tab9, hr_tab10, hr_tab11 = st.tabs([
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
        "⚖️ Discipline Cases"
    ])
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    cursor = conn.cursor()
    
    # Create additional tables if not exists
    # Create additional tables if not exists
    def create_hr_tables():
        if is_cloud:
            # Translation of Terms table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_translation (
                    id SERIAL PRIMARY KEY,
                    staff_no TEXT,
                    old_designation TEXT,
                    new_designation TEXT,
                    effective_date TEXT,
                    reason TEXT,
                    approved_by TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            # Salary Harmonization table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_salary_harmonization (
                    id SERIAL PRIMARY KEY,
                    staff_no TEXT,
                    old_salary_grade TEXT,
                    new_salary_grade TEXT,
                    old_basic_pay NUMERIC,
                    new_basic_pay NUMERIC,
                    effective_date TEXT,
                    reason TEXT,
                    approved_by TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            # Unpaid Leave table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_unpaid_leave (
                    id SERIAL PRIMARY KEY,
                    staff_no TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    total_days INTEGER,
                    reason TEXT,
                    status TEXT DEFAULT 'Pending',
                    approved_by TEXT,
                    approval_date TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            # Confirmation in Appointment table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_confirmation (
                    id SERIAL PRIMARY KEY,
                    staff_no TEXT,
                    confirmation_date TEXT,
                    probation_period_months INTEGER,
                    performance_rating TEXT,
                    recommendation TEXT,
                    status TEXT DEFAULT 'Pending',
                    approved_by TEXT,
                    approval_date TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            # Discipline Cases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_discipline (
                    id SERIAL PRIMARY KEY,
                    staff_no TEXT,
                    case_number TEXT,
                    case_type TEXT,
                    incident_date TEXT,
                    description TEXT,
                    penalty TEXT,
                    status TEXT DEFAULT 'Under Investigation',
                    hearing_date TEXT,
                    decision_date TEXT,
                    action_taken TEXT,
                    closed_date TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            # Promotions table (add if not exists)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_promotions (
                    id SERIAL PRIMARY KEY,
                    staff_no TEXT,
                    old_designation TEXT,
                    new_designation TEXT,
                    old_job_group TEXT,
                    new_job_group TEXT,
                    effective_date TEXT,
                    reason TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            # Redesignation table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_redesignation (
                    id SERIAL PRIMARY KEY,
                    staff_no TEXT,
                    old_department TEXT,
                    new_department TEXT,
                    old_designation TEXT,
                    new_designation TEXT,
                    effective_date TEXT,
                    reason TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            # Contracts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee_contracts (
                    id SERIAL PRIMARY KEY,
                    staff_no TEXT,
                    contract_type TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    document_path TEXT,
                    status TEXT DEFAULT 'Active',
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
        else:
            # SQLite syntax for all tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_translation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_no TEXT,
                    old_designation TEXT,
                    new_designation TEXT,
                    effective_date TEXT,
                    reason TEXT,
                    approved_by TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_salary_harmonization (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_no TEXT,
                    old_salary_grade TEXT,
                    new_salary_grade TEXT,
                    old_basic_pay REAL,
                    new_basic_pay REAL,
                    effective_date TEXT,
                    reason TEXT,
                    approved_by TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_unpaid_leave (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_no TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    total_days INTEGER,
                    reason TEXT,
                    status TEXT DEFAULT 'Pending',
                    approved_by TEXT,
                    approval_date TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_confirmation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_no TEXT,
                    confirmation_date TEXT,
                    probation_period_months INTEGER,
                    performance_rating TEXT,
                    recommendation TEXT,
                    status TEXT DEFAULT 'Pending',
                    approved_by TEXT,
                    approval_date TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_discipline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_no TEXT,
                    case_number TEXT,
                    case_type TEXT,
                    incident_date TEXT,
                    description TEXT,
                    penalty TEXT,
                    status TEXT DEFAULT 'Under Investigation',
                    hearing_date TEXT,
                    decision_date TEXT,
                    action_taken TEXT,
                    closed_date TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_promotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_no TEXT,
                    old_designation TEXT,
                    new_designation TEXT,
                    old_job_group TEXT,
                    new_job_group TEXT,
                    effective_date TEXT,
                    reason TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_redesignation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_no TEXT,
                    old_department TEXT,
                    new_department TEXT,
                    old_designation TEXT,
                    new_designation TEXT,
                    effective_date TEXT,
                    reason TEXT,
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee_contracts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_no TEXT,
                    contract_type TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    document_path TEXT,
                    status TEXT DEFAULT 'Active',
                    chrmac_minutes TEXT,
                    chrmac_date TEXT,
                    cpsb_minute TEXT,
                    cpsb_date TEXT,
                    created_at TEXT,
                    created_by TEXT
                )
            """)
        
        conn.commit()
    
    # Call the function to create tables
    create_hr_tables()
    
    # ==================== TAB 1: HR ANALYTICS ====================
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
                            # Join with employees to get department
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
                    
                    # ==================== ROW 3: STAGNATION ANALYSIS (Overdue for Promotion) ====================
                    st.markdown("## ⏰ Stagnation Analysis (Overdue for Promotion)")
                    
                    # Calculate employees who haven't been promoted in over 5 years
                    if not promotions_df.empty and 'staff_no' in promotions_df.columns:
                        # Get latest promotion date per employee
                        latest_promo = promotions_df.groupby('staff_no')['effective_date'].max().reset_index()
                        latest_promo.columns = ['staff_no', 'last_promo_date']
                        latest_promo['last_promo_date'] = pd.to_datetime(latest_promo['last_promo_date'])
                        
                        # Calculate years since last promotion
                        latest_promo['years_since_promo'] = (datetime.now() - latest_promo['last_promo_date']).dt.days / 365.25
                        
                        # Get employees who are overdue (over 5 years since last promotion)
                        overdue_employees = latest_promo[latest_promo['years_since_promo'] > 5]
                        overdue_employees = pd.merge(overdue_employees, employees_df[['staff_no', 'name', 'department', 'current_designation']], 
                                                     on='staff_no', how='left')
                        
                        # Employees with no promotions ever (never promoted)
                        never_promoted = employees_df[~employees_df['staff_no'].isin(promotions_df['staff_no'].unique())]
                        never_promoted = never_promoted[['staff_no', 'name', 'department', 'current_designation']]
                        never_promoted['years_since_promo'] = 'Never Promoted'
                        
                        # Combine for display
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### 📊 Stagnation by Department")
                            if not overdue_employees.empty:
                                dept_stagnation = overdue_employees['department'].value_counts().reset_index()
                                dept_stagnation.columns = ['Department', 'Overdue Count']
                                fig_stagnation = px.bar(dept_stagnation, x='Department', y='Overdue Count',
                                                       title="Employees Overdue for Promotion (>5 years)",
                                                       color='Overdue Count',
                                                       color_continuous_scale='Reds')
                                fig_stagnation.update_layout(height=400)
                                st.plotly_chart(fig_stagnation, use_container_width=True)
                            else:
                                st.info("No employees overdue for promotion")
                        
                        with col2:
                            st.markdown("#### 📋 Overdue Employees List")
                            if not overdue_employees.empty:
                                st.dataframe(overdue_employees[['name', 'department', 'current_designation', 'years_since_promo']].head(10), 
                                            use_container_width=True)
                                st.caption(f"Showing top 10 of {len(overdue_employees)} overdue employees")
                            else:
                                st.info("No employees are overdue for promotion")
                        
                        # Never promoted employees
                        st.markdown("#### 📋 Employees Never Promoted")
                        if not never_promoted.empty:
                            st.dataframe(never_promoted[['name', 'department', 'current_designation']].head(10), 
                                        use_container_width=True)
                            st.caption(f"Showing top 10 of {len(never_promoted)} employees never promoted")
                        else:
                            st.info("All employees have received at least one promotion")
                    else:
                        st.info("No promotion data available to calculate stagnation")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 4: DISCIPLINE CASES ANALYSIS ====================
                    st.markdown("## ⚖️ Discipline Cases Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    # Chart 5: Discipline Cases by Department
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
                    
                    # Chart 6: Discipline Cases by Type
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
                    
                    # Chart 7: Age Distribution Histogram
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
                                
                                # Age group analysis
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
                    
                    # Chart 8: Department Average Age
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
                    
                    # ==================== ROW 6: MONTHLY ANALYSIS FOR ALL MODULES ====================
                    st.markdown("## 📅 Monthly Analysis (All Modules)")
                    
                    # Prepare monthly data for all modules
                    monthly_data = pd.DataFrame()
                    
                    # Employee growth
                    if 'created_at' in employees_df.columns:
                        employees_df['created_month'] = pd.to_datetime(employees_df['created_at']).dt.strftime('%Y-%m')
                        monthly_growth = employees_df.groupby('created_month').size().reset_index(name='New Employees')
                        monthly_data['month'] = monthly_growth['created_month']
                        monthly_data['New Employees'] = monthly_growth['New Employees']
                    
                    # Promotions monthly
                    if not promotions_df.empty and 'effective_date' in promotions_df.columns:
                        promotions_df['promo_month'] = pd.to_datetime(promotions_df['effective_date']).dt.strftime('%Y-%m')
                        monthly_promos = promotions_df.groupby('promo_month').size().reset_index(name='Promotions')
                        monthly_data = pd.merge(monthly_data, monthly_promos, left_on='month', right_on='promo_month', how='outer') if not monthly_data.empty else monthly_promos.rename(columns={'promo_month': 'month'})
                        monthly_data['Promotions'] = monthly_data['Promotions'].fillna(0)
                    
                    # Discipline cases monthly
                    if not discipline_df.empty and 'created_at' in discipline_df.columns:
                        discipline_df['disc_month'] = pd.to_datetime(discipline_df['created_at']).dt.strftime('%Y-%m')
                        monthly_disc = discipline_df.groupby('disc_month').size().reset_index(name='Discipline Cases')
                        monthly_data = pd.merge(monthly_data, monthly_disc, left_on='month', right_on='disc_month', how='outer') if not monthly_data.empty else monthly_disc.rename(columns={'disc_month': 'month'})
                        monthly_data['Discipline Cases'] = monthly_data['Discipline Cases'].fillna(0)
                    
                    # Leave cases monthly
                    if not leave_df.empty and 'created_at' in leave_df.columns:
                        leave_df['leave_month'] = pd.to_datetime(leave_df['created_at']).dt.strftime('%Y-%m')
                        monthly_leave = leave_df.groupby('leave_month').size().reset_index(name='Unpaid Leave')
                        monthly_data = pd.merge(monthly_data, monthly_leave, left_on='month', right_on='leave_month', how='outer') if not monthly_data.empty else monthly_leave.rename(columns={'leave_month': 'month'})
                        monthly_data['Unpaid Leave'] = monthly_data['Unpaid Leave'].fillna(0)
                    
                    # Confirmation monthly
                    confirm_df = pd.read_sql("SELECT * FROM hr_confirmation", conn) if table_exists else pd.DataFrame()
                    if not confirm_df.empty and 'created_at' in confirm_df.columns:
                        confirm_df['conf_month'] = pd.to_datetime(confirm_df['created_at']).dt.strftime('%Y-%m')
                        monthly_conf = confirm_df.groupby('conf_month').size().reset_index(name='Confirmations')
                        monthly_data = pd.merge(monthly_data, monthly_conf, left_on='month', right_on='conf_month', how='outer') if not monthly_data.empty else monthly_conf.rename(columns={'conf_month': 'month'})
                        monthly_data['Confirmations'] = monthly_data['Confirmations'].fillna(0)
                    
                    if not monthly_data.empty:
                        monthly_data = monthly_data.sort_values('month').fillna(0)
                        monthly_data = monthly_data.set_index('month')
                        
                        # Create multi-line chart
                        fig_monthly = px.line(monthly_data, x=monthly_data.index, y=monthly_data.columns,
                                             title="Monthly HR Activity Trends",
                                             markers=True,
                                             labels={'value': 'Count', 'variable': 'Module', 'month': 'Month'})
                        fig_monthly.update_layout(height=500, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
                        st.plotly_chart(fig_monthly, use_container_width=True)
                        
                        # Data table
                        with st.expander("📋 Monthly Data Table"):
                            st.dataframe(monthly_data, use_container_width=True)
                    else:
                        st.info("No monthly trend data available yet")
                    
                    st.markdown("---")
                    
                    # ==================== ROW 7: EMPLOYEE STATUS SUMMARY ====================
                    st.markdown("## 📋 Employee Status Summary")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Department wise summary
                        if 'department' in employees_df.columns:
                            dept_summary = employees_df.groupby('department').agg({
                                'staff_no': 'count',
                                'age': 'mean' if 'age' in employees_df.columns else None
                            }).reset_index()
                            dept_summary.columns = ['Department', 'Employee Count', 'Average Age'] if 'age' in employees_df.columns else ['Department', 'Employee Count']
                            
                            st.markdown("#### 📊 Department Summary")
                            st.dataframe(dept_summary, use_container_width=True)
                    
                    with col2:
                        # Career progression summary
                        st.markdown("#### 📈 Career Progression Summary")
                        if not promotions_df.empty:
                            promo_summary = promotions_df.groupby('staff_no').size().reset_index(name='promotion_count')
                            avg_promotions = promo_summary['promotion_count'].mean()
                            max_promotions = promo_summary['promotion_count'].max()
                            
                            st.metric("Average Promotions per Employee", f"{avg_promotions:.1f}")
                            st.metric("Highest Promotions (Single Employee)", max_promotions)
                            
                            # Promotion frequency
                            if 'effective_date' in promotions_df.columns:
                                promo_dates = pd.to_datetime(promotions_df['effective_date'])
                                if len(promo_dates) > 1:
                                    avg_interval = (promo_dates.max() - promo_dates.min()).days / len(promo_dates) / 30
                                    st.metric("Average Promotion Interval", f"{avg_interval:.0f} months")
                        else:
                            st.info("No promotion data available")
                    
                    # Download report button
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        # Create comprehensive report
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
    
    # ==================== TAB 2: STAFF REGISTRY ====================
    with hr_tab2:
        st.subheader("👥 Staff Registry")
        
        # Update employees table structure if needed
        def update_employees_table():
            """Add new columns to employees table if they don't exist"""
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
                        # Check if column exists in SQLite
                        cursor.execute("PRAGMA table_info(employees)")
                        existing_cols = [col[1] for col in cursor.fetchall()]
                        if col_name not in existing_cols:
                            cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
                except Exception as e:
                    pass
            conn.commit()
        
        # Call the function to update table structure
        update_employees_table()
        
        tab_add, tab_view = st.tabs(["➕ Add Staff", "📋 View Staff"])
        
        # ==================== ADD STAFF TAB ====================
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
                        ["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Other"],
                        key="hr_department")
                    
                    # NEW: Terms of Service field
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
                            # Update employees table with new column
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
                            
                            # Check if personal_no already exists
                            if is_cloud:
                                cursor.execute("SELECT personal_no FROM employees WHERE personal_no = %s", (personal_no,))
                            else:
                                cursor.execute("SELECT personal_no FROM employees WHERE personal_no = ?", (personal_no,))
                            
                            if cursor.fetchone():
                                # Update existing record
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
                                # Insert new record
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
                            st.balloons()
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error: {e}")
        
        # ==================== VIEW STAFF TAB ====================
        with tab_view:
            st.markdown("### 🔍 Search Staff")
            st.info("Search for staff members using any of the criteria below")
            
            # Search filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_name = st.text_input("Search by Name", placeholder="Enter full or partial name...", key="search_name")
                search_personal_no = st.text_input("Search by Personal No (ID)", placeholder="Enter ID number...", key="search_personal")
                search_terms = st.selectbox("Terms of Service", 
                    ["All", "Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"],
                    key="search_terms")
            
            with col2:
                search_department = st.selectbox("Filter by Department", 
                    ["All Departments", "Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Lands", "Trade", "Tourism", "Water", "Environment", "Gender", "Youth", "Cooperative", "Energy", "Transport", "Legal", "Audit", "Procurement", "Other"],
                    key="search_department")
                search_gender = st.selectbox("Filter by Gender", ["All", "Male", "Female", "Other"], key="search_gender")
                search_job_group = st.text_input("Search by Job Group", placeholder="e.g., JG H, JG M", key="search_job_group")
            
            with col3:
                search_designation = st.text_input("Search by Designation", placeholder="Enter designation...", key="search_designation")
                min_age = st.number_input("Minimum Age", min_value=18, max_value=100, value=18, key="min_age")
                max_age = st.number_input("Maximum Age", min_value=18, max_value=100, value=100, key="max_age")
            
            # Search button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                search_clicked = st.button("🔍 Search Staff", use_container_width=True, type="primary")
            
            # Clear search results button
            with col1:
                if st.button("🗑️ Clear Search", use_container_width=True):
                    if 'search_results' in st.session_state:
                        del st.session_state.search_results
                    if 'search_performed' in st.session_state:
                        del st.session_state.search_performed
                    st.rerun()
            
            # If search button is clicked, store results in session state
            if search_clicked:
                # Build query based on search criteria
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
                    
                    # Store results in session state
                    st.session_state.search_results = results_df
                    st.session_state.search_performed = True
                    
                    # Clear edit mode when new search is performed
                    if 'editing_staff' in st.session_state:
                        del st.session_state.editing_staff
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error searching staff: {e}")
                    st.session_state.search_results = pd.DataFrame()
                    st.session_state.search_performed = True
            
            # ==================== EDIT FORM ====================
            # Check if editing mode is active
            if 'editing_staff' in st.session_state and st.session_state.editing_staff:
                st.markdown("---")
                st.subheader("✏️ Edit Staff Details")
                
                # Get employee details by personal_no - clean the value
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
                            
                            # NEW: Terms of Service field
                            terms_of_service = st.selectbox("Terms of Service", 
                                ["Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"],
                                index=["Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"].index(emp['terms_of_service']) if emp['terms_of_service'] in ["Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"] else 0,
                                key="edit_terms_of_service")
                            
                            # Handle first appointment date - WIDE DATE RANGE (using datetime instead of date)
                            first_appointment_date = None
                            if emp['first_appointment_date'] and emp['first_appointment_date'] != 'None':
                                try:
                                    first_appointment_date = pd.to_datetime(emp['first_appointment_date']).date()
                                except:
                                    first_appointment_date = datetime.now().date()
                            else:
                                first_appointment_date = datetime.now().date()
                            
                            # FIXED: Using datetime instead of date to avoid NameError
                            first_appointment_date = st.date_input("First Date of Appointment", value=first_appointment_date, min_value=datetime(1900, 1, 1), max_value=datetime(2100, 12, 31), key="edit_appointment_date")
                            first_designation = st.text_input("First Designation", value=emp['first_designation'] if emp['first_designation'] else "", key="edit_first_designation")
                            first_job_group = st.text_input("First Appointment Job Group", value=emp['first_job_group'] if emp['first_job_group'] else "", key="edit_first_job_group")
                        
                        with col3:
                            # Handle current designation date - WIDE DATE RANGE (using datetime instead of date)
                            current_designation_date = None
                            if emp['current_designation_date'] and emp['current_designation_date'] != 'None':
                                try:
                                    current_designation_date = pd.to_datetime(emp['current_designation_date']).date()
                                except:
                                    current_designation_date = datetime.now().date()
                            else:
                                current_designation_date = datetime.now().date()
                            
                            # FIXED: Using datetime instead of date to avoid NameError
                            current_designation_date = st.date_input("Date of Current Designation", value=current_designation_date, min_value=datetime(1900, 1, 1), max_value=datetime(2100, 12, 31), key="edit_current_date")
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
                                    st.success(f"✅ Employee {name} updated successfully!")
                                    # Clear edit mode and refresh search results
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
            
            # ==================== DISPLAY SEARCH RESULTS ====================
            # Check if we have search results to display
            if 'search_results' in st.session_state and st.session_state.search_performed:
                results_df = st.session_state.search_results
                
                if results_df.empty:
                    st.warning("No staff records found matching your search criteria.")
                else:
                    st.markdown("---")
                    st.subheader("📋 Search Results")
                    st.success(f"✅ Found {len(results_df)} staff record(s)")
                    
                    # Display each result with edit and delete buttons
                    for idx, row in results_df.iterrows():
                        # Clean personal_no for display
                        personal_no_clean = str(row['personal_no']).split('.')[0] if row['personal_no'] else ''
                        
                        with st.container():
                            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1.5, 1, 1, 1.5, 0.8, 0.8])
                            with col1:
                                st.write(f"**{row['name']}**")
                            with col2:
                                st.write(f"ID: {personal_no_clean}")
                            with col3:
                                st.write(f"Age: {int(float(row['age'])) if row['age'] else 'N/A'}")
                            with col4:
                                st.write(f"Gender: {row['gender'] if row['gender'] else 'N/A'}")
                            with col5:
                                st.write(f"Department: {row['department'] if row['department'] else 'N/A'}")
                            with col6:
                                if st.button("✏️ Edit", key=f"edit_{row['personal_no']}_{idx}", use_container_width=True):
                                    st.session_state.editing_staff = row['personal_no']
                                    st.rerun()
                            with col7:
                                if st.button("🗑️ Delete", key=f"delete_{row['personal_no']}_{idx}", use_container_width=True):
                                    # Show delete confirmation
                                    confirm_key = f"confirm_delete_{row['personal_no']}"
                                    if confirm_key not in st.session_state:
                                        st.session_state[confirm_key] = False
                                    
                                    if not st.session_state[confirm_key]:
                                        st.session_state[confirm_key] = True
                                        st.warning(f"⚠️ Are you sure you want to delete {row['name']}?")
                                        col_yes, col_no = st.columns(2)
                                        with col_yes:
                                            if st.button("✅ Yes, Delete", key=f"yes_{row['personal_no']}"):
                                                if is_cloud:
                                                    cursor.execute("DELETE FROM employees WHERE personal_no::TEXT = %s", (str(row['personal_no']).split('.')[0],))
                                                else:
                                                    cursor.execute("DELETE FROM employees WHERE personal_no = ?", (str(row['personal_no']).split('.')[0],))
                                                conn.commit()
                                                st.success(f"✅ Employee {row['name']} deleted successfully!")
                                                # Refresh search results
                                                del st.session_state.search_results
                                                st.rerun()
                                        with col_no:
                                            if st.button("❌ Cancel", key=f"no_{row['personal_no']}"):
                                                del st.session_state[confirm_key]
                                                st.rerun()
                                    else:
                                        # Reset confirmation after showing
                                        del st.session_state[confirm_key]
                            st.divider()
                    
                    # Also provide a dataframe view option
                    with st.expander("📊 View as Table"):
                        # Select columns to display in table view
                        display_cols = ['personal_no', 'name', 'gender', 'age', 'department', 'terms_of_service', 
                                       'current_designation', 'current_job_group', 'first_appointment_date']
                        available_cols = [col for col in display_cols if col in results_df.columns]
                        display_df = results_df[available_cols].copy()
                        
                        # Rename columns for display
                        column_rename = {
                            'personal_no': 'Personal No',
                            'name': 'Name',
                            'gender': 'Gender',
                            'age': 'Age',
                            'department': 'Department',
                            'terms_of_service': 'Terms of Service',
                            'current_designation': 'Current Designation',
                            'current_job_group': 'Current Job Group',
                            'first_appointment_date': 'First Appointment Date'
                        }
                        display_df = display_df.rename(columns={k: v for k, v in column_rename.items() if k in display_df.columns})
                        
                        # Clean personal_no
                        if 'Personal No' in display_df.columns:
                            display_df['Personal No'] = display_df['Personal No'].apply(lambda x: str(x).split('.')[0] if x else '')
                        
                        st.dataframe(display_df, use_container_width=True)
                        
                        # Export results
                        csv = results_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download Search Results (CSV)",
                            csv,
                            f"staff_search_results_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv"
                        )
            
            elif 'search_performed' not in st.session_state and 'editing_staff' not in st.session_state:
                st.info("👆 Use the search filters above to find staff members. Click the Edit button to modify staff details or Delete to remove a record.")
            
            # ==================== EDIT FORM ====================
            # Check if editing mode is active
            if 'editing_staff' in st.session_state and st.session_state.editing_staff:
                st.markdown("---")
                st.subheader("✏️ Edit Staff Details")
                
                # Get employee details by personal_no - clean the value
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
                            
                            # NEW: Terms of Service field
                            terms_of_service = st.selectbox("Terms of Service", 
                                ["Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"],
                                index=["Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"].index(emp['terms_of_service']) if emp['terms_of_service'] in ["Permanent", "Contract", "Temporary", "Internship", "Secondment", "Volunteer", "Probation"] else 0,
                                key="edit_terms_of_service")
                            
                            # Handle first appointment date - WIDE DATE RANGE
                            from datetime import date
                            first_appointment_date = None
                            if emp['first_appointment_date'] and emp['first_appointment_date'] != 'None':
                                try:
                                    first_appointment_date = pd.to_datetime(emp['first_appointment_date']).date()
                                except:
                                    first_appointment_date = date.today()
                            else:
                                first_appointment_date = date.today()
                            
                            # FIXED: Wide date range from 1900 to 2100
                            first_appointment_date = st.date_input("First Date of Appointment", value=first_appointment_date, min_value=datetime(1900, 1, 1).date(), max_value=datetime(2100, 12, 31).date(), key="edit_appointment_date")
                            first_designation = st.text_input("First Designation", value=emp['first_designation'] if emp['first_designation'] else "", key="edit_first_designation")
                            first_job_group = st.text_input("First Appointment Job Group", value=emp['first_job_group'] if emp['first_job_group'] else "", key="edit_first_job_group")
                        
                        with col3:
                            # Handle current designation date - WIDE DATE RANGE
                            current_designation_date = None
                            if emp['current_designation_date'] and emp['current_designation_date'] != 'None':
                                try:
                                    current_designation_date = pd.to_datetime(emp['current_designation_date']).date()
                                except:
                                    current_designation_date = date.today()
                            else:
                                current_designation_date = date.today()
                            
                            # FIXED: Wide date range from 1900 to 2100
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
                                    st.success(f"✅ Employee {name} updated successfully!")
                                    # Clear edit mode and refresh search results
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
            
            # ==================== DISPLAY SEARCH RESULTS ====================
            # Check if we have search results to display
            if 'search_results' in st.session_state and st.session_state.search_performed:
                results_df = st.session_state.search_results
                
                if results_df.empty:
                    st.warning("No staff records found matching your search criteria.")
                else:
                    st.markdown("---")
                    st.subheader("📋 Search Results")
                    st.success(f"✅ Found {len(results_df)} staff record(s)")
                    
                    # Display each result with edit and delete buttons
                    for idx, row in results_df.iterrows():
                        # Clean personal_no for display
                        personal_no_clean = str(row['personal_no']).split('.')[0] if row['personal_no'] else ''
                        
                        # Create unique keys using multiple identifiers to avoid duplicates
                        unique_suffix = f"{idx}_{hash(row['name'])}_{hash(personal_no_clean)}"
                        edit_key = f"edit_{unique_suffix}"
                        delete_key = f"delete_{unique_suffix}"
                        confirm_key = f"confirm_{unique_suffix}"
                        
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
                                    # Store delete target in session state
                                    st.session_state.delete_target = row['personal_no']
                                    st.session_state.delete_name = row['name']
                                    st.rerun()
                            st.divider()
                    
                    # Handle delete confirmation outside the loop
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
                                    # Clear delete session state
                                    del st.session_state.delete_target
                                    del st.session_state.delete_name
                                    # Refresh search results
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
                    
                    # Also provide a dataframe view option
                    with st.expander("📊 View as Table"):
                        # Select columns to display
                        display_cols = ['personal_no', 'name', 'gender', 'age', 'department', 'terms_of_service', 
                                       'current_designation', 'current_job_group', 'first_appointment_date']
                        available_cols = [col for col in display_cols if col in results_df.columns]
                        display_df = results_df[available_cols].copy()
                        
                        # Clean personal_no
                        if 'personal_no' in display_df.columns:
                            display_df['personal_no'] = display_df['personal_no'].apply(lambda x: str(x).split('.')[0] if x else '')
                        
                        # Rename columns for display
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
                        
                        # Export results
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
        
        # Download template with Personal No as identifier
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
                # Read the file
                if uploaded_file.name.endswith('.csv'):
                    import_df = pd.read_csv(uploaded_file)
                else:
                    import_df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ File loaded! {len(import_df)} rows found")
                
                with st.expander("📊 Preview uploaded data"):
                    st.dataframe(import_df.head(10), use_container_width=True)
                
                # Map columns (case-insensitive)
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
                
                # Rename columns
                import_df.columns = import_df.columns.str.lower().str.strip()
                for col in import_df.columns:
                    if col in column_mapping:
                        import_df = import_df.rename(columns={col: column_mapping[col]})
                
                # Check required columns
                if 'personal_no' not in import_df.columns or 'name' not in import_df.columns:
                    st.error("❌ Required columns 'Personal No' and 'Name' not found in the file!")
                    st.info("Please ensure your file has columns: Personal No (National ID) and Name")
                else:
                    # Preview required fields
                    preview_df = import_df[['personal_no', 'name']].copy()
                    st.write("**Preview of required fields:**")
                    st.dataframe(preview_df.head(10), use_container_width=True)
                    
                    # Import button
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
                                    
                                    # Get optional values
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
                                    
                                    # Check if personal_no already exists
                                    if is_cloud:
                                        cursor.execute("SELECT personal_no FROM employees WHERE personal_no = %s", (personal_no,))
                                    else:
                                        cursor.execute("SELECT personal_no FROM employees WHERE personal_no = ?", (personal_no,))
                                    
                                    if cursor.fetchone():
                                        # Update existing record
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
                                        # Insert new record
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
                            
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
                st.info("Please make sure your file matches the template format.")
    
    # ==================== TAB 4: PROMOTIONS ====================
    with hr_tab4:
        st.subheader("📈 Promotions Management")
        
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
                                # Update employee record
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
                                
                                # Save to promotions table
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
                                
                                st.success(f"✅ Promotion processed for {employee['name']}!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.warning("Please enter the new designation")
            else:
                st.warning("No employees found. Please add employees in Staff Registry first.")
        except Exception as e:
            st.info(f"Add employees to enable promotions. ({e})")
    
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
                                
                                # Save to redesignation table
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
                                # Update employee record
                                if is_cloud:
                                    cursor.execute("UPDATE employees SET current_designation = %s WHERE staff_no = %s", (new_designation, staff_no))
                                else:
                                    cursor.execute("UPDATE employees SET current_designation = ? WHERE staff_no = ?", (new_designation, staff_no))
                                conn.commit()
                                
                                # Save to translation table
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
                                
                                st.success(f"✅ Translation of terms processed for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please enter the new designation")
                    
                    # Display translation history
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
                                # Update employee record
                                if new_salary_grade:
                                    if is_cloud:
                                        cursor.execute("UPDATE employees SET current_job_group = %s WHERE staff_no = %s", (new_salary_grade, staff_no))
                                    else:
                                        cursor.execute("UPDATE employees SET current_job_group = ? WHERE staff_no = ?", (new_salary_grade, staff_no))
                                
                                # Save to harmonization table
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
                                
                                st.success(f"✅ Salary harmonization processed for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please enter new salary grade or new basic pay")
            else:
                st.warning("No employees found.")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # ==================== TAB 9: UNPAID LEAVE / LEAVE OF ABSENCE ====================
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
                                
                                st.success(f"✅ Leave request submitted for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please fill in all required fields")
                    
                    # Display leave history
                    st.markdown("---")
                    st.subheader("📋 Leave History")
                    history_df = pd.read_sql(f"SELECT * FROM hr_unpaid_leave WHERE staff_no = '{staff_no}' ORDER BY start_date DESC", conn)
                    if not history_df.empty:
                        st.dataframe(history_df[['start_date', 'end_date', 'total_days', 'reason', 'status', 'chrmac_minutes', 'cpsb_minute', 'created_at']], use_container_width=True)
            else:
                st.warning("No employees found.")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # ==================== TAB 10: CONFIRMATION IN APPOINTMENT ====================
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
                                
                                # Update employee status if confirmed
                                if status == "Approved" and recommendation == "Confirm":
                                    if is_cloud:
                                        cursor.execute("UPDATE employees SET status = 'Confirmed' WHERE staff_no = %s", (staff_no,))
                                    else:
                                        cursor.execute("UPDATE employees SET status = 'Confirmed' WHERE staff_no = ?", (staff_no,))
                                    conn.commit()
                                
                                st.success(f"✅ Confirmation processed for {employee['name']}!")
                                st.rerun()
                            else:
                                st.warning("Please select confirmation date")
                    
                    # Display confirmation history
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
                
                case_type = st.selectbox("Case Type", 
                    ["Absenteeism", "Misconduct", "Gross Misconduct", "Insubordination", "Corruption", "Theft", "Other"], 
                    key="case_type")
                incident_date = st.date_input("Incident Date", key="incident_date")
            with col2:
                case_number = st.text_input("Case Number", placeholder="e.g., DISC/2024/001", key="case_number")
                status = st.selectbox("Status", 
                    ["Under Investigation", "Hearing Scheduled", "Decision Pending", "Closed", "Appealed"], 
                    key="discipline_status")
            
            description = st.text_area("Case Description", height=100, key="case_description")
            penalty = st.text_area("Penalty/Action Taken", height=80, key="penalty")
            
            st.markdown("### 📋 Approval Minutes")
            col1, col2 = st.columns(2)
            with col1:
                chrmac_minutes = st.text_input("CHRMAC Minutes Reference", placeholder="e.g., CHRMAC/2024/001", key="discipline_chrmac_min")
                chrmac_date = st.date_input("Date of CHRMAC", key="discipline_chrmac_date")
            with col2:
                cpsb_minute = st.text_input("CPSB Minute Reference", placeholder="e.g., CPSB/2024/001", key="discipline_cpsb_min")
                cpsb_date = st.date_input("Date of CPSB", key="discipline_cpsb_date")
            
            if st.form_submit_button("Record Case", use_container_width=True, type="primary"):
                if selected_employee != "Select employee..." and case_number and description:
                    staff_no = selected_employee.split(" - ")[0]
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    chrmac_date_str = chrmac_date.strftime("%Y-%m-%d") if chrmac_date else None
                    cpsb_date_str = cpsb_date.strftime("%Y-%m-%d") if cpsb_date else None
                    
                    if is_cloud:
                        cursor.execute("""
                            INSERT INTO hr_discipline (
                                staff_no, case_number, case_type, incident_date, description, penalty, status,
                                chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                created_at, created_by
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (staff_no, case_number, case_type, incident_date.strftime("%Y-%m-%d"), description, penalty, status,
                              chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                              now, st.session_state.user['username']))
                    else:
                        cursor.execute("""
                            INSERT INTO hr_discipline (
                                staff_no, case_number, case_type, incident_date, description, penalty, status,
                                chrmac_minutes, chrmac_date, cpsb_minute, cpsb_date,
                                created_at, created_by
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (staff_no, case_number, case_type, incident_date.strftime("%Y-%m-%d"), description, penalty, status,
                              chrmac_minutes, chrmac_date_str, cpsb_minute, cpsb_date_str,
                              now, st.session_state.user['username']))
                    conn.commit()
                    st.success(f"✅ Discipline case recorded!")
                    st.rerun()
                else:
                    st.warning("Please select employee and enter case number and description")
        
        # Display discipline cases history
        st.markdown("---")
        st.subheader("📋 Discipline Cases History")
        
        try:
            cases_df = pd.read_sql("""
                SELECT d.*, e.name as employee_name 
                FROM hr_discipline d
                JOIN employees e ON d.staff_no = e.staff_no
                ORDER BY d.id DESC
            """, conn)
            if not cases_df.empty:
                st.dataframe(cases_df[['case_number', 'employee_name', 'case_type', 'incident_date', 'status', 'penalty', 'chrmac_minutes', 'cpsb_minute', 'created_at']], use_container_width=True)
            else:
                st.info("No discipline cases recorded yet.")
        except Exception as e:
            st.info("Discipline cases will appear here once recorded.")
    
    conn.close()
# =========================================================
# PROFESSIONAL UI THEME (STABLE SIDEBAR VERSION)
# =========================================================
# =========================================================
# PROFESSIONAL ENTERPRISE THEME
# EMBU COUNTY PUBLIC SERVICE BOARD HR SYSTEM
# =========================================================

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
    </style>
    
    <script>
    // JavaScript to hide any remaining toggle buttons
    setTimeout(function() {
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            const text = button.innerText || button.textContent;
            if (text === '<<<' || text === '>' || text === '<' || text === '☰') {
                button.style.display = 'none';
            }
        });
    }, 100);
    </script>
    """, unsafe_allow_html=True)
# =========================================================
# PROFESSIONAL LOGIN PAGE - STREAMLIT (FULL INTEGRATION)
# =========================================================

def login():
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
    </style>
    """, unsafe_allow_html=True)
    
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
        st.markdown("""
        <div class="right-panel">
            <div class="form-title">Welcome Back</div>
            <div class="form-sub">Sign in to continue to your account</div>
        """, unsafe_allow_html=True)
        
        # Username field
        username = st.text_input("", placeholder="Username", label_visibility="collapsed", key="login_username")
        
        # Password field
        password = st.text_input("", placeholder="Password", type="password", label_visibility="collapsed", key="login_password")
        
        # Remember me row
        col_a, col_b = st.columns([1, 1])
        with col_a:
            remember = st.checkbox("Remember me", value=False)
        with col_b:
            st.markdown("<div style='text-align: right; margin-top: 8px;'><a href='#' style='color: #4f7cff; text-decoration: none;'>Forgot password?</a></div>", unsafe_allow_html=True)
        
        # Login button
        login_btn = st.button("Login", use_container_width=True, type="primary")
        
        # Divider
        st.markdown('<div class="divider"><span>or continue with</span></div>', unsafe_allow_html=True)
        
        # Social buttons
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.button("🔗 LinkedIn", use_container_width=True, key="linkedin_btn")
        with col_s2:
            st.button("🐦 X", use_container_width=True, key="x_btn")
        with col_s3:
            st.button("💼 Workday", use_container_width=True, key="workday_btn")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Login logic
    if login_btn:
        user = login_user(username, password)
        if user:
            st.session_state.user = {
                "id": user[0],
                "username": user[1],
                "role": user[3]
            }
            log_audit(user[1], "LOGIN", user[0], "User logged in")
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid credentials")
# =========================================================
# AUDIT LOG FUNCTION
# =========================================================
def log_audit(username, action, record_id, details):
    try:
        conn = get_conn()
        c = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        if is_cloud:
            c.execute("""
                INSERT INTO audit_log (username, action, record_id, details, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, action, record_id, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        else:
            c.execute("""
                INSERT INTO audit_log (username, action, record_id, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (username, action, record_id, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")


# =========================================================
# SIDEBAR
# =========================================================
def sidebar():
    # Initialize sidebar state
    if 'show_sidebar' not in st.session_state:
        st.session_state.show_sidebar = True
    
    # If sidebar is hidden, return None (nothing to display)
    if not st.session_state.show_sidebar:
        return None
    
    with st.sidebar:
        
        # =====================================================
        # CACHED DATABASE STATS (Single connection, cached)
        # =====================================================
        @st.cache_data(ttl=60)
        def get_stats():
            conn = get_conn()
            c = conn.cursor()
            
            # Get all counts in one go
            c.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN application_status='Shortlisted' THEN 1 ELSE 0 END) as shortlisted,
                    SUM(CASE WHEN interview_score IS NOT NULL AND interview_score > 0 THEN 1 ELSE 0 END) as interviewed,
                    SUM(CASE WHEN application_status='Recommended' THEN 1 ELSE 0 END) as successful
                FROM staff
            """)
            result = c.fetchone()
            conn.close()
            
            return result[0], result[1], result[2], result[3]
        
        total_applicants, shortlisted_count, interviewed_count, successful_count = get_stats()

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
                            {st.session_state.user.get('username', 'User')}
                        </div>
                        <div style="margin-top: 4px;">
                            <span style="
                                background: #10b981;
                                padding: 4px 10px;
                                border-radius: 20px;
                                font-size: 11px;
                                color: white;
                                font-weight: 600;
                            ">
                                {st.session_state.user.get('role', 'User')}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # =====================================================
        # SIDEBAR STATS DISPLAY (Only ONE - Updated metrics)
        # =====================================================
        st.markdown(f"""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:18px;">
            <div style="background:rgba(255,255,255,0.08); padding:12px; border-radius:12px; text-align:center;">
                <div style="font-size:11px; color:#cbd5e1;">Total</div>
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
        # NAVIGATION MENU
        # =====================================================
        menu_options = {
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
            list(menu_options.keys()),
            label_visibility="collapsed"
        )

        # =====================================================
        # MENU DESCRIPTION
        # =====================================================
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
            {menu_options[menu]}
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
# SIDEBAR TOGGLE BUTTON (Place in Main Dashboard)
# =========================================================
def sidebar_toggle_button():
    """Create a toggle button in the main dashboard area"""
    
    # Initialize sidebar state if not exists
    if 'show_sidebar' not in st.session_state:
        st.session_state.show_sidebar = True
    
    # Create styled button container
    if st.session_state.show_sidebar:
        button_label = "◀ Hide Sidebar"
        button_help = "Click to hide the sidebar panel"
    else:
        button_label = "☰ Show Sidebar"
        button_help = "Click to show the sidebar panel"
    
    # Create a small column for the toggle button
    col1, col2, col3 = st.columns([1, 10, 1])
    with col1:
        if st.button(button_label, help=button_help, use_container_width=True):
            st.session_state.show_sidebar = not st.session_state.show_sidebar
            st.rerun()
# =========================================================
# DASHBOARD
# =========================================================
def dashboard():
    # Display the main dashboard with KPIs, filters, and charts
    # (This comment will NOT appear in the UI)
    sidebar_toggle_button()
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
    # 2. FETCH DATA (Using cached version)
    # ======================================================
    def get_data():
        """Fetch staff data from database (cached)"""
        try:
            return get_cached_staff_data()
        except Exception as e:
            return pd.DataFrame(columns=['application_status', 'subcounty', 'gender', 'yob', 'created_at', 'disability', 'ethnicity', 'interview_score'])
    
    df = get_data()
    
    # Calculate stats
    total_staff = len(df)
    pending = len(df[df['application_status'] == 'Pending']) if 'application_status' in df.columns else 0
    shortlisted = len(df[df['application_status'] == 'Shortlisted']) if 'application_status' in df.columns else 0
    hired = len(df[df['application_status'] == 'Hired']) if 'application_status' in df.columns else 0
    
    # ======================================================
    # 3. HEADER
    # ======================================================
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown('<div class="main-title">Embu County Public Service Board</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title">Real-time overview of Recruitment Process</div>', unsafe_allow_html=True)
    
    with col2:
        if st.button("📤 Export Report", use_container_width=True):
            if not df.empty:
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
    # 4. KPI CARDS
    # ======================================================
    # KPI CARDS (Updated labels)
    cards = st.columns(4)
    
    # Calculate stats
    total_applicants = len(df)
    shortlisted = len(df[df['application_status'] == 'Shortlisted']) if 'application_status' in df.columns else 0
    interviewed = len(df[df['interview_score'].notna() & (df['interview_score'] > 0)]) if 'interview_score' in df.columns else 0
    successful = len(df[df['application_status'] == 'Recommended']) if 'application_status' in df.columns else 0
    
    kpi_data = [
        ("📊 ALL APPLICANTS", str(total_applicants), "Total Applications"),
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
    # 5. FILTER SECTION
    # ======================================================
    st.markdown("""
    <div class="section-card">
        <div class="chart-title">🔍 Filter Data</div>
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
            st.slider("Year of Birth", 1960, 2000, (1960, 2000), key="year_filter_dummy")
    
    # Apply filters
    filtered_df = df.copy()
    if 'subcounty' in filtered_df.columns and subcounty_filter != 'All Sub-Counties':
        filtered_df = filtered_df[filtered_df['subcounty'] == subcounty_filter]
    if 'gender' in filtered_df.columns and gender_filter != 'All Genders':
        filtered_df = filtered_df[filtered_df['gender'] == gender_filter]
    if 'yob' in filtered_df.columns and 'year_range' in locals():
        filtered_df = filtered_df[(filtered_df['yob'] >= year_range[0]) & (filtered_df['yob'] <= year_range[1])]
    
    # ======================================================
    # 6. CHARTS
    # ======================================================
    c1, c2 = st.columns(2)
    
    # Bar Chart - Sub-County Distribution
    with c1:
        st.markdown("""
        <div class="section-card">
            <div class="chart-title">📍 Staff Distribution by Sub-County</div>
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
                    xaxis_title="Number of Staff",
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
    # NEW: Successful Candidates Analysis (Disability & Ethnicity)
    # ======================================================
    
    # Get successful candidates (Recommended)
    successful_df = df[df['application_status'] == 'Recommended'] if 'application_status' in df.columns else pd.DataFrame()
    
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
                # Count candidates with disability
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
        st.info("🏆 No successful candidates (Recommended) yet. Complete the scoring process to see analysis.")
    
    # ======================================================
    # 7. LOWER SECTION
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
                    yaxis_title="Number of Staff",
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
            <div class="chart-title">📈 Staff Growth Trend</div>
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
                    xaxis_title="Date",
                    yaxis_title="New Staff Added",
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No growth data available for selected filters")
        else:
            st.info("No growth data available")
        st.markdown("</div>", unsafe_allow_html=True)
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
# =========================================================
# APPLICANT REGISTRATION (RECRUITMENT)
# =========================================================
# =========================================================
# APPLICANT REGISTRATION (RECRUITMENT)
# =========================================================
def data_entry():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">📝 Job Application Form</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Dear Applicant, kindly complete the application form here.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # =====================================================
    # FETCH ADVERTISED POSITIONS FROM DATABASE
    # =====================================================
    conn = get_conn()
    advertised_positions_list = []
    positions_df = pd.DataFrame()
    
    if conn:
        try:
            is_cloud = st.secrets.get("DATABASE_URL") is not None
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
            placeholder="e.g., ECDE/2024/001",
            help="Enter the position code from the job advertisement"
        )
    
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    # Variable to store found position
    found_position = None
    selected_position = None
    
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
    # APPLICATION FORM - WRAPPED IN st.form()
    # =====================================================
    st.subheader("📝 Application Form")
    
    # WRAP EVERYTHING IN A FORM - THIS IS THE KEY FIX
    with st.form(key="application_form"):
        
        # Create tabs for better organization
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Position", "👤 Personal Information", "📚 Education", "📍 Location", "📎 Documents"])
        
        # Initialize variables
        application_date = datetime.now().strftime("%Y-%m-%d")
        name = ""
        gender = "Male"
        id_number = ""
        yob = 1990
        ethnicity = ""
        disability = ""
        contact = ""
        email = ""
        kcse_year = 0
        kcse_grade = ""
        qualifications = ""
        institution = ""
        graduation_year = 0
        subcounty = ""
        ward = ""
        experience_years = 0
        current_employer = ""
        remarks = ""
        
        with tab1:
            st.markdown("### 📋 Position Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if selected_position:
                    position_applied = selected_position['title']
                    advertisement_ref = selected_position['code']
                    st.text_input("🎯 Position Applied For*", value=position_applied, disabled=True, help="Auto-filled from selected position")
                    st.text_input("📢 Advertisement Reference Number", value=advertisement_ref, disabled=True, help="Auto-filled from selected position")
                elif found_position:
                    position_applied = found_position['title']
                    advertisement_ref = found_position['code']
                    st.text_input("🎯 Position Applied For*", value=position_applied, disabled=True, help="Auto-filled from searched position")
                    st.text_input("📢 Advertisement Reference Number", value=advertisement_ref, disabled=True, help="Auto-filled from searched position")
                else:
                    position_applied = st.selectbox("🎯 Position Applied For*", 
                        ["Select Position"] + [p['title'] for p in advertised_positions_list] if advertised_positions_list else ["Select Position"],
                        help="Select the position you wish to apply for")
                    advertisement_ref = st.text_input("📢 Advertisement Reference Number", 
                                                      placeholder="e.g., ECDE/01/2024",
                                                      help="Reference number from the job advertisement")
            
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
        
        with tab2:
            st.markdown("### 👤 Personal Information")
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("👨‍🏫 Full Name (as per ID)*", placeholder="Enter your full name", help="Required field")
                gender = st.selectbox("⚧ Gender*", ["Male", "Female", "Other"], help="Required field")
                id_number = st.text_input("🆔 National ID Number*", placeholder="Enter ID number (e.g., 12345678)", help="Required field - Must be unique")
                yob = st.number_input("🎂 Year of Birth", step=1, min_value=1950, max_value=2026, help="Select year of birth")
                
            with col2:
                age = datetime.now().year - yob if yob else 0
                if age > 0:
                    if age < 18:
                        st.warning(f"⚠️ Age: {age} years - Below minimum recruitment age (18+)")
                    elif age > 55:
                        st.warning(f"⚠️ Age: {age} years - Check if within retirement requirements")
                    else:
                        st.success(f"✅ Age: {age} years")
                
                ethnicity = st.selectbox("🌍 Ethnicity (Optional)", [
                    "Select Ethnicity",
                    "Kikuyu", "Luo", "Luhya", "Kalenjin", "Kamba", "Kisii",
                    "Meru", "Mijikenda", "Turkana", "Maasai", "Taita", "Embu",
                    "Swahili", "Samburu", "Pokot", "Other"
                ], help="Optional - for diversity reporting")
                
                disability = st.selectbox("♿ Disability Status", [
                    "None",
                    "Physical Disability",
                    "Visual Impairment",
                    "Hearing Impairment",
                    "Learning Disability",
                    "Albinism",
                    "Other"
                ], help="Select if applicable - for equal opportunity employment")
        
        with tab3:
            st.markdown("### 📚 Education & Professional Qualifications")
            
            st.markdown("#### 📖 KCSE Results")
            col1, col2 = st.columns(2)
            with col1:
                kcse_year = st.number_input("KCSE Year", min_value=2000, max_value=2026, step=1, help="Year of KCSE completion")
            with col2:
                kcse_grade = st.selectbox("KCSE Mean Grade", [
                    "Select Grade",
                    "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-"
                ], help="Overall KCSE mean grade")
            
            st.markdown("#### 🎓 Highest Academic Qualification")
            col1, col2 = st.columns(2)
            with col1:
                qualifications = st.selectbox("Qualification Level", [
                    "Select Qualification",
                    "ECDE Certificate",
                    "ECDE Diploma",
                    "Bachelor's Degree in ECDE",
                    "Bachelor's Degree in Education (Early Childhood)",
                    "Postgraduate Diploma in ECDE",
                    "Master's Degree in ECDE",
                    "Master's Degree in Education",
                    "PhD in ECDE",
                    "Other"
                ], help="Select your highest qualification")
                
                if qualifications == "Other":
                    other_qual = st.text_input("Specify other qualification", placeholder="Enter your qualification")
            
            with col2:
                institution = st.text_input("🏛️ Institution Name", placeholder="e.g., Kenyatta University, Moi University")
                graduation_year = st.number_input("📅 Year of Graduation", min_value=1980, max_value=2026, step=1)
            
            st.markdown("#### 📜 Professional Certifications")
            professional_body = st.text_input("Professional Body Registration", 
                                             placeholder="e.g., TSC Registration Number",
                                             help="Teachers Service Commission registration number if registered")
            
            additional_certs = st.text_area("Other Certifications & Trainings", 
                                           placeholder="List any additional professional certifications, workshops, or short courses...",
                                           height=100)
        
        with tab4:
            st.markdown("### 📍 Location & Work Experience")
            
            st.markdown("#### 🏠 Current Residence")
            col1, col2 = st.columns(2)
            with col1:
                subcounty = st.text_input("🏢 Current Sub-County", placeholder="Enter your sub-county", help="Your current sub-county of residence")
            with col2:
                ward = st.text_input("🏘️ Current Ward", placeholder="Enter your ward", help="Your current ward of residence")
            
            st.markdown("#### 📞 Contact Information")
            col1, col2 = st.columns(2)
            with col1:
                contact = st.text_input("📱 Phone Number*", placeholder="07XXXXXXXX", help="Required - Format: 07XXXXXXXX")
            with col2:
                email = st.text_input("📧 Email Address", placeholder="youremail@example.com", help="For official communication")
            
            st.markdown("#### 💼 Work Experience")
            col1, col2 = st.columns(2)
            with col1:
                experience_years = st.number_input("Years of Experience", min_value=0, max_value=40, value=0, step=1, help="Total years of experience")
            with col2:
                current_employer = st.text_input("Current Employer (if any)", placeholder="School/Institution name")
            
            experience_details = st.text_area("Work Experience Details", 
                                             placeholder="Describe your previous positions:\n- Position held\n- Duration\n- Key responsibilities and achievements",
                                             height=150)
            
            earliest_start = st.date_input("📅 Earliest Start Date", help="When can you join if selected?")
        
        with tab5:
            st.markdown("### 📎 Additional Information & References")
            
            st.markdown("#### 👥 Professional Referees")
            st.info("Please provide two professional referees who can vouch for your work")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Referee 1**")
                referee1_name = st.text_input("Referee 1 - Full Name", key="ref1_name", placeholder="Full name")
                referee1_title = st.text_input("Referee 1 - Title/Position", key="ref1_title", placeholder="e.g., Head Teacher")
                referee1_contact = st.text_input("Referee 1 - Phone/Email", key="ref1_contact", placeholder="Phone number or email")
            
            with col2:
                st.markdown("**Referee 2**")
                referee2_name = st.text_input("Referee 2 - Full Name", key="ref2_name", placeholder="Full name")
                referee2_title = st.text_input("Referee 2 - Title/Position", key="ref2_title", placeholder="e.g., Education Officer")
                referee2_contact = st.text_input("Referee 2 - Phone/Email", key="ref2_contact", placeholder="Phone number or email")
            
            st.markdown("#### 📋 Document Checklist")
            st.info("Please confirm you have the following documents ready for submission")
            
            col1, col2 = st.columns(2)
            with col1:
                id_doc = st.checkbox("National ID Card/Passport")
                kcse_cert = st.checkbox("KCSE Certificate")
                degree_cert = st.checkbox("Degree/Diploma Certificate")
                tsc_cert = st.checkbox("TSC Certificate (if registered)")
            
            with col2:
                cv_doc = st.checkbox("Curriculum Vitae (CV)")
                recommendation = st.checkbox("Recommendation Letters")
                police_cert = st.checkbox("Police Clearance Certificate")
                other_docs = st.checkbox("Other Supporting Documents")
            
            st.markdown("#### ✍️ Declaration")
            declaration = st.checkbox("I declare that all information provided is true and accurate to the best of my knowledge. I understand that any false information may lead to disqualification.")
            
            remarks = st.text_area("Additional Remarks", 
                                  placeholder="Any other information you would like to add...",
                                  height=80)
        
        # Required fields note
        st.markdown("---")
        st.markdown("""
        <div style="background: #f8f9fa; padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;">
            <small>⚠️ <strong>Note:</strong> Fields marked with <span style="color: red;">*</span> are required</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Submit button inside the form
        submitted = st.form_submit_button("📤 Submit Application", use_container_width=True, type="primary")
        
        # Process submission ONLY when form is submitted
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
                    # Build comprehensive remarks with all application details
                    full_remarks = f"""
                    === APPLICATION DETAILS ===
                    Position: {position_applied}
                    Advert Ref: {advertisement_ref}
                    Source: {source_of_info}
                    Application Date: {application_date}
                    
                    === EDUCATION ===
                    KCSE: {kcse_year} - Grade {kcse_grade}
                    Qualification: {qualifications}
                    Institution: {institution}
                    Graduation: {graduation_year}
                    Professional Body: {professional_body}
                    
                    === EXPERIENCE ===
                    Experience: {experience_years} years
                    Current Employer: {current_employer}
                    Earliest Start: {earliest_start}
                    
                    === REFERENCES ===
                    Referee 1: {referee1_name} ({referee1_title}) - {referee1_contact}
                    Referee 2: {referee2_name} ({referee2_title}) - {referee2_contact}
                    
                    === DOCUMENTS ===
                    Documents Ready: ID:{id_doc}, KCSE:{kcse_cert}, Certificate:{degree_cert}, TSC:{tsc_cert}, CV:{cv_doc}
                    
                    === ADDITIONAL ===
                    {remarks}
                    """
                    
                    c.execute("""
                    INSERT INTO staff (
                        sno, name, gender, id_number, yob, ethnicity, disability, contact,
                        kcse, qualifications, subcounty, ward, experience, remarks,
                        created_at, created_by, position_applied, advertisement_ref,
                        email, experience_years, current_employer, referee1_name, 
                        referee1_contact, referee2_name, referee2_contact
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        0, name, gender, id_number, yob if yob else 0,
                        ethnicity if ethnicity and ethnicity != "Select Ethnicity" else "",
                        disability if disability and disability != "None" else "",
                        contact, kcse_year if kcse_year else 0,
                        f"{qualifications} from {institution} ({graduation_year}) | KCSE: {kcse_grade}",
                        subcounty if subcounty else "", ward if ward else "",
                        f"{experience_years} years - {experience_details}",
                        full_remarks, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        st.session_state.user["username"], position_applied, advertisement_ref,
                        email, experience_years, current_employer,
                        referee1_name, referee1_contact, referee2_name, referee2_contact
                    ))
                    
                    conn.commit()
                    log_audit(st.session_state.user['username'], "APPLICATION_SUBMIT", c.lastrowid, f"Job application: {name} for {position_applied}")
                    
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
                    
                    Thank you for applying to the County ECDE Recruitment!
                    """)
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error submitting application: {str(e)}")
                finally:
                    conn.close()
# =========================================================
# STAFF RECORDS
# =========================================================
def records():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">Staff Records</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">View, search and manage teacher data</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM staff ORDER BY id DESC", conn)
    conn.close()
    
    if df.empty:
        st.warning("No records found. Please add records using Staff Entry or Import Excel.")
        return
    
    # Advanced search section
    with st.expander("🔍 Advanced Search", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            search_name = st.text_input("Search by name", placeholder="Enter name...")
            search_id = st.text_input("Search by ID number", placeholder="Enter ID number...")
        with col2:
            search_subcounty = st.selectbox("Sub-County", ["All"] + sorted(df['subcounty'].dropna().unique().tolist()))
            search_qualification = st.text_input("Search by qualification", placeholder="Enter qualification...")
        with col3:
            search_ward = st.selectbox("Ward", ["All"] + sorted(df['ward'].dropna().unique().tolist()))
            gender_filter = st.selectbox("Gender", ["All", "Male", "Female"])
    
    # Simple search with button - OPTIMIZED
    st.subheader("🔍 Quick Search")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search by Name or ID", placeholder="Type name or ID number...", key="search_input", label_visibility="collapsed")
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    # Apply filters
    filtered_df = df.copy()
    
    # Apply quick search ONLY when search button is clicked
    if search_button and search:
        filtered_df = filtered_df[
            filtered_df["name"].str.contains(search, case=False, na=False) |
            filtered_df["id_number"].str.contains(search, na=False)
        ]
    
    # Apply advanced filters (these still apply on every change, but they're in an expander)
    if 'search_name' in locals() and search_name:
        filtered_df = filtered_df[filtered_df["name"].str.contains(search_name, case=False, na=False)]
    
    if 'search_id' in locals() and search_id:
        filtered_df = filtered_df[filtered_df["id_number"].str.contains(search_id, na=False)]
    
    if 'search_subcounty' in locals() and search_subcounty != "All":
        filtered_df = filtered_df[filtered_df["subcounty"] == search_subcounty]
    
    if 'search_ward' in locals() and search_ward != "All":
        filtered_df = filtered_df[filtered_df["ward"] == search_ward]
    
    if 'gender_filter' in locals() and gender_filter != "All":
        filtered_df = filtered_df[filtered_df["gender"] == gender_filter]
    
    if 'search_qualification' in locals() and search_qualification:
        filtered_df = filtered_df[filtered_df["qualifications"].str.contains(search_qualification, case=False, na=False)]
    
    st.markdown(f"### 📊 Results: {len(filtered_df):,} records found")
    
    # Pagination
    col1, col2 = st.columns([3, 1])
    with col1:
        page_size = st.selectbox("Records per page", [10, 25, 50, 100, 200])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    if len(filtered_df) > 0:
        total_pages = (len(filtered_df) + page_size - 1) // page_size
        page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
        
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size
        page_df = filtered_df.iloc[start_idx:end_idx]
        
        st.dataframe(page_df, use_container_width=True, height=400)
        st.caption(f"Page {page_number} of {total_pages}")
    else:
        st.info("No records match your search criteria.")
    
    # Export filtered data
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download Filtered Data (CSV)",
                csv,
                f"staff_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
    
    # Admin-only delete functionality
    if st.session_state.user["role"] == "Admin":
        st.markdown("---")
        st.warning("⚠️ Admin Actions - Use with caution!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Delete All Records", use_container_width=True):
                confirm = st.checkbox("Confirm: I understand this will delete ALL records permanently")
                if confirm:
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("DELETE FROM staff")
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.user['username'], "DELETE_ALL", 0, "Deleted all staff records")
                    st.success("All records deleted successfully!")
                    st.rerun()
                else:
                    st.warning("Please confirm to delete all records")
        
        with col2:
            record_id = st.number_input("Delete specific record by ID", min_value=1, step=1)
            if st.button("Delete Record", use_container_width=True):
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT name FROM staff WHERE id = ?", (record_id,))
                staff_name = c.fetchone()
                if staff_name:
                    c.execute("DELETE FROM staff WHERE id = ?", (record_id,))
                    conn.commit()
                    log_audit(st.session_state.user['username'], "DELETE", record_id, f"Deleted staff: {staff_name[0]}")
                    st.success(f"Record {record_id} deleted!")
                    st.rerun()
                else:
                    st.error(f"Record {record_id} not found")
                conn.close()
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
    
    # Get all applicants for selection
    conn = get_conn()
    applicants_df = pd.read_sql("SELECT id, name, id_number, position_applied, application_status FROM staff ORDER BY id DESC", conn)
    conn.close()
    
    if applicants_df.empty:
        st.warning("No applicants found to edit.")
        return
    
    # Applicant selector
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_applicant = st.selectbox(
            "Select Applicant to Edit",
            applicants_df['id'].tolist(),
            format_func=lambda x: f"{x} - {applicants_df[applicants_df['id']==x]['name'].iloc[0]} ({applicants_df[applicants_df['id']==x]['position_applied'].iloc[0]})"
        )
    
    if selected_applicant:
        # Load full applicant data
        conn = get_conn()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Get applicant data
        if is_cloud:
            applicant = pd.read_sql(f"SELECT * FROM staff WHERE id = {selected_applicant}", conn)
        else:
            applicant = pd.read_sql(f"SELECT * FROM staff WHERE id = {selected_applicant}", conn)
        
        # Try to get position code from multiple possible columns
        position_code = None
        if 'advertisement_ref' in applicant.columns:
            position_code = applicant.iloc[0]['advertisement_ref']
        elif 'position_code' in applicant.columns:
            position_code = applicant.iloc[0]['position_code']
        
        # Also try to get from position_applied by matching title
        position_title = applicant.iloc[0]['position_applied'] if 'position_applied' in applicant.columns else None
        
        # Fetch advertised position details
        position_details = None
        if position_code and position_code != 'None' and position_code != 'nan':
            try:
                if is_cloud:
                    position_details = pd.read_sql(f"SELECT * FROM advertised_positions WHERE position_code = '{position_code}'", conn)
                else:
                    position_details = pd.read_sql(f"SELECT * FROM advertised_positions WHERE position_code = '{position_code}'", conn)
                if not position_details.empty:
                    position_details = position_details.iloc[0]
            except Exception as e:
                pass
        
        # If not found by code, try by title
        if position_details is None and position_title:
            try:
                if is_cloud:
                    position_details = pd.read_sql(f"SELECT * FROM advertised_positions WHERE position_title = '{position_title}'", conn)
                else:
                    position_details = pd.read_sql(f"SELECT * FROM advertised_positions WHERE position_title = '{position_title}'", conn)
                if not position_details.empty:
                    position_details = position_details.iloc[0]
            except Exception as e:
                pass
        
        conn.close()
        
        if not applicant.empty:
            app = applicant.iloc[0]
            
            # Show current status banner
            status_colors = {
                "Pending": "🟡",
                "Shortlisted": "🟢",
                "Interview Scheduled": "🔵",
                "Interviewed": "🟣",
                "Recommended": "🟠",
                "Hired": "✅",
                "Rejected": "❌",
                "On Hold": "⏸️"
            }
            status_icon = status_colors.get(app['application_status'], "📋")
            st.info(f"{status_icon} **Current Status:** {app['application_status']} | **Position:** {app['position_applied']} | **Application Date:** {app['application_date']}")
            
            # Edit form tabs - Added 6th tab for Applicant Profile
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "📋 Position & Status", 
                "👤 Personal Information", 
                "📚 Education", 
                "📍 Location & Experience", 
                "📎 Additional Info",
                "📄 Applicant Profile"
            ])
            
            # ==================== TAB 1: POSITION & STATUS ====================
            with tab1:
                st.markdown("### 📋 Application Details")
                col1, col2 = st.columns(2)
                
                with col1:
                    position_applied = st.selectbox("Position Applied For", [
                        "ECDE Teacher - Permanent",
                        "ECDE Teacher - Contract",
                        "ECDE Trainer",
                        "ECDE Supervisor",
                        "ECDE Coordinator",
                        "ECDE Curriculum Developer",
                        "ECDE Administrator",
                        "Intern ECDE Teacher",
                        "Volunteer ECDE Teacher"
                    ], index=0 if app['position_applied'] is None else [
                        "ECDE Teacher - Permanent", "ECDE Teacher - Contract", "ECDE Trainer",
                        "ECDE Supervisor", "ECDE Coordinator", "ECDE Curriculum Developer",
                        "ECDE Administrator", "Intern ECDE Teacher", "Volunteer ECDE Teacher"
                    ].index(app['position_applied']) if app['position_applied'] in [
                        "ECDE Teacher - Permanent", "ECDE Teacher - Contract", "ECDE Trainer",
                        "ECDE Supervisor", "ECDE Coordinator", "ECDE Curriculum Developer",
                        "ECDE Administrator", "Intern ECDE Teacher", "Volunteer ECDE Teacher"
                    ] else 0)
                    
                    application_status = st.selectbox("Application Status", [
                        "Pending", "Shortlisted", "Interview Scheduled", "Interviewed", 
                        "Recommended", "Hired", "Rejected", "On Hold"
                    ], index=["Pending", "Shortlisted", "Interview Scheduled", "Interviewed", "Recommended", "Hired", "Rejected", "On Hold"].index(app['application_status']) if app['application_status'] in ["Pending", "Shortlisted", "Interview Scheduled", "Interviewed", "Recommended", "Hired", "Rejected", "On Hold"] else 0)
                
                with col2:
                    interview_date = st.date_input(
                        "Interview Date",
                        value=datetime.strptime(app['interview_date'], "%Y-%m-%d") if app['interview_date'] and app['interview_date'] != "None" else datetime.now()
                    )
                    interview_score = st.number_input("Interview Score (0-100)", min_value=0.0, max_value=100.0, value=float(app['interview_score']) if app['interview_score'] else 0.0, step=5.0)
                
                remarks = st.text_area("Recruitment Remarks/Notes", value=app['remarks'] if app['remarks'] else "", height=100)
            
            # ==================== TAB 2: PERSONAL INFORMATION ====================
            with tab2:
                st.markdown("### 👤 Personal Information")
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Full Name", value=app['name'] if app['name'] else "")
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(app['gender']) if app['gender'] in ["Male", "Female", "Other"] else 0)
                    id_number = st.text_input("ID Number", value=app['id_number'] if app['id_number'] else "")
                    yob = st.number_input("Year of Birth", min_value=1950, max_value=2026, value=int(app['yob']) if app['yob'] else 1990)
                
                with col2:
                    age = datetime.now().year - yob if yob else 0
                    st.info(f"📊 Age: {age} years")
                    ethnicity = st.selectbox("Ethnicity", [
                        "Kikuyu", "Luo", "Luhya", "Kalenjin", "Kamba", "Kisii",
                        "Meru", "Mijikenda", "Turkana", "Maasai", "Taita", "Embu",
                        "Swahili", "Samburu", "Pokot", "Other"
                    ], index=0 if app['ethnicity'] is None else [
                        "Kikuyu", "Luo", "Luhya", "Kalenjin", "Kamba", "Kisii",
                        "Meru", "Mijikenda", "Turkana", "Maasai", "Taita", "Embu",
                        "Swahili", "Samburu", "Pokot", "Other"
                    ].index(app['ethnicity']) if app['ethnicity'] in [
                        "Kikuyu", "Luo", "Luhya", "Kalenjin", "Kamba", "Kisii",
                        "Meru", "Mijikenda", "Turkana", "Maasai", "Taita", "Embu",
                        "Swahili", "Samburu", "Pokot", "Other"
                    ] else 0)
                    
                    disability = st.selectbox("Disability Status", [
                        "None", "Physical Disability", "Visual Impairment", 
                        "Hearing Impairment", "Learning Disability", "Albinism", "Other"
                    ], index=0 if app['disability'] is None else [
                        "None", "Physical Disability", "Visual Impairment", 
                        "Hearing Impairment", "Learning Disability", "Albinism", "Other"
                    ].index(app['disability']) if app['disability'] in [
                        "None", "Physical Disability", "Visual Impairment", 
                        "Hearing Impairment", "Learning Disability", "Albinism", "Other"
                    ] else 0)
            
            # ==================== TAB 3: EDUCATION ====================
            with tab3:
                st.markdown("### 📚 Education & Qualifications")
                
                col1, col2 = st.columns(2)
                with col1:
                    kcse_year = st.number_input("KCSE Year", min_value=2000, max_value=2026, value=int(app['kcse']) if app['kcse'] and str(app['kcse']).isdigit() else 2010)
                    kcse_grade = st.selectbox("KCSE Mean Grade", [
                        "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-"
                    ], index=0 if app['kcse_grade'] is None else [
                        "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-"
                    ].index(app['kcse_grade']) if app['kcse_grade'] in [
                        "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-"
                    ] else 0)
                
                with col2:
                    qualifications = st.selectbox("Highest Qualification", [
                        "ECDE Certificate", "ECDE Diploma", "Bachelor's Degree in ECDE",
                        "Bachelor's Degree in Education", "Postgraduate Diploma in ECDE",
                        "Master's Degree in ECDE", "Master's Degree in Education",
                        "PhD in ECDE", "Other"
                    ], index=0 if app['qualifications'] is None else [
                        "ECDE Certificate", "ECDE Diploma", "Bachelor's Degree in ECDE",
                        "Bachelor's Degree in Education", "Postgraduate Diploma in ECDE",
                        "Master's Degree in ECDE", "Master's Degree in Education",
                        "PhD in ECDE", "Other"
                    ].index(app['qualifications']) if app['qualifications'] in [
                        "ECDE Certificate", "ECDE Diploma", "Bachelor's Degree in ECDE",
                        "Bachelor's Degree in Education", "Postgraduate Diploma in ECDE",
                        "Master's Degree in ECDE", "Master's Degree in Education",
                        "PhD in ECDE", "Other"
                    ] else 0)
                
                institution = st.text_input("Institution Name", value=app['institution'] if app['institution'] else "")
                graduation_year = st.number_input("Graduation Year", min_value=1980, max_value=2026, value=int(app['graduation_year']) if app['graduation_year'] else 2020)
                professional_body = st.text_input("Professional Body Registration (TSC Number)", value=app['professional_body'] if app['professional_body'] else "")
            
            # ==================== TAB 4: LOCATION & EXPERIENCE ====================
            with tab4:
                st.markdown("### 📍 Location & Work Experience")
                
                col1, col2 = st.columns(2)
                with col1:
                    contact = st.text_input("Phone Number", value=app['contact'] if app['contact'] else "")
                    email = st.text_input("Email Address", value=app['email'] if app['email'] else "")
                    subcounty = st.text_input("Current Sub-County", value=app['subcounty'] if app['subcounty'] else "")
                    ward = st.text_input("Current Ward", value=app['ward'] if app['ward'] else "")
                
                with col2:
                    experience_years = st.number_input("Years of Experience", min_value=0, max_value=40, value=int(app['experience_years']) if app['experience_years'] else 0)
                    current_employer = st.text_input("Current Employer", value=app['current_employer'] if app['current_employer'] else "")
                    experience_details = st.text_area("Experience Details", value=app['experience'] if app['experience'] else "", height=100)
            
            # ==================== TAB 5: ADDITIONAL INFO ====================
            with tab5:
                st.markdown("### 📎 Additional Information")
                
                st.markdown("#### 👥 Referees")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Referee 1**")
                    referee1_name = st.text_input("Referee 1 Name", value=app['referee1_name'] if app['referee1_name'] else "", key="ref1_name")
                    referee1_contact = st.text_input("Referee 1 Contact", value=app['referee1_contact'] if app['referee1_contact'] else "", key="ref1_contact")
                
                with col2:
                    st.markdown("**Referee 2**")
                    referee2_name = st.text_input("Referee 2 Name", value=app['referee2_name'] if app['referee2_name'] else "", key="ref2_name")
                    referee2_contact = st.text_input("Referee 2 Contact", value=app['referee2_contact'] if app['referee2_contact'] else "", key="ref2_contact")
            
            # ==================== TAB 6: APPLICANT PROFILE ====================
            with tab6:
                st.markdown("### 📄 Applicant Profile")
                st.markdown("---")
                
                # Export buttons
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("📄 Generate PDF Report", use_container_width=True, type="primary"):
                        st.info("PDF generation feature - Ready to implement")
                with col2:
                    if st.button("🖨️ Print Profile", use_container_width=True):
                        st.info("Click Print from your browser (Ctrl+P or Cmd+P)")
                
                st.markdown("---")
                
def display_applicant_profile(app, position_details):
    """Display the applicant profile in a professional format"""
    
    # Professional CSS for profile display
    st.markdown("""
    <style>
        .profile-container {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .profile-header {
            text-align: center;
            border-bottom: 2px solid #1e3a5f;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }
        .logo-section {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 2rem;
            margin-bottom: 1rem;
        }
        .logo-placeholder {
            font-size: 3rem;
        }
        .county-name {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1e3a5f;
        }
        .board-name {
            font-size: 1.2rem;
            color: #2c5282;
        }
        .profile-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #2d3748;
            margin-top: 1rem;
        }
        .info-section {
            margin-bottom: 1.5rem;
        }
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1e3a5f;
            border-left: 4px solid #3b82f6;
            padding-left: 0.75rem;
            margin-bottom: 1rem;
        }
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
        }
        .info-item {
            display: flex;
            padding: 0.5rem;
            border-bottom: 1px solid #e2e8f0;
        }
        .info-label {
            font-weight: 600;
            width: 40%;
            color: #4a5568;
        }
        .info-value {
            width: 60%;
            color: #2d3748;
        }
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .status-Pending { background: #fef3c7; color: #d97706; }
        .status-Shortlisted { background: #d1fae5; color: #059669; }
        .status-Interviewed { background: #dbeafe; color: #2563eb; }
        .status-Hired { background: #d1fae5; color: #059669; }
        .status-Rejected { background: #fee2e2; color: #dc2626; }
        .footer-note {
            text-align: center;
            font-size: 0.7rem;
            color: #94a3b8;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #e2e8f0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Calculate age
    age = datetime.now().year - app['yob'] if app['yob'] else "N/A"
    
    # Get position code from available fields
    position_code = app.get('advertisement_ref', 'N/A')
    if position_code == 'None' or position_code == 'nan' or not position_code:
        position_code = 'N/A'
    
    # Safely extract position details values
    pos_title = 'N/A'
    pos_code = 'N/A'
    pos_dept = 'N/A'
    pos_emp_type = 'N/A'
    pos_vacancies = 'N/A'
    pos_salary = 'N/A'
    pos_deadline = 'N/A'
    pos_requirements = 'Not specified'
    pos_responsibilities = 'Not specified'
    
    if position_details is not None:
        try:
            # Check if it's a Pandas Series or dict
            if hasattr(position_details, 'get'):
                pos_title = str(position_details.get('position_title', 'N/A')) if position_details.get('position_title') is not None else 'N/A'
                pos_code = str(position_details.get('position_code', 'N/A')) if position_details.get('position_code') is not None else 'N/A'
                pos_dept = str(position_details.get('department', 'N/A')) if position_details.get('department') is not None else 'N/A'
                pos_emp_type = str(position_details.get('employment_type', 'N/A')) if position_details.get('employment_type') is not None else 'N/A'
                pos_vacancies = str(position_details.get('vacancies', 'N/A')) if position_details.get('vacancies') is not None else 'N/A'
                pos_salary = str(position_details.get('salary_range', 'N/A')) if position_details.get('salary_range') is not None else 'N/A'
                pos_deadline = str(position_details.get('application_deadline', 'N/A')) if position_details.get('application_deadline') is not None else 'N/A'
                
                req_val = position_details.get('requirements')
                pos_requirements = str(req_val) if req_val is not None and str(req_val) != 'nan' else 'Not specified'
                
                resp_val = position_details.get('responsibilities')
                pos_responsibilities = str(resp_val) if resp_val is not None and str(resp_val) != 'nan' else 'Not specified'
        except Exception as e:
            pass
    
    # Create profile HTML
    profile_html = f"""
    <div class="profile-container">
        <div class="profile-header">
            <div class="logo-section">
                <div class="logo-placeholder">🏛️</div>
                <div>
                    <div class="county-name">EMBU COUNTY</div>
                    <div class="board-name">PUBLIC SERVICE BOARD</div>
                </div>
                <div class="logo-placeholder">📜</div>
            </div>
            <div class="profile-title">APPLICANT PROFILE FORM</div>
            <div style="font-size: 0.85rem; color: #64748b;">Human Resource Management System</div>
        </div>
        
        <!-- Application Details -->
        <div class="info-section">
            <div class="section-title">📋 Application Information</div>
            <div class="info-grid">
                <div class="info-item"><span class="info-label">Application ID:</span><span class="info-value">ECPSB/{app['id']}/{datetime.now().year}</span></div>
                <div class="info-item"><span class="info-label">Application Date:</span><span class="info-value">{app['application_date'] if app['application_date'] else 'Not recorded'}</span></div>
                <div class="info-item"><span class="info-label">Position Applied:</span><span class="info-value">{app['position_applied'] if app['position_applied'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Position Code:</span><span class="info-value">{position_code}</span></div>
                <div class="info-item"><span class="info-label">Status:</span><span class="info-value"><span class="status-badge status-{app['application_status']}">{app['application_status']}</span></span></div>
                <div class="info-item"><span class="info-label">Interview Score:</span><span class="info-value">{app['interview_score'] if app['interview_score'] else 'Not interviewed'}</span></div>
            </div>
        </div>
        
        <!-- Personal Information -->
        <div class="info-section">
            <div class="section-title">👤 Personal Information</div>
            <div class="info-grid">
                <div class="info-item"><span class="info-label">Full Name:</span><span class="info-value">{app['name']}</span></div>
                <div class="info-item"><span class="info-label">Gender:</span><span class="info-value">{app['gender'] if app['gender'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">ID Number:</span><span class="info-value">{app['id_number']}</span></div>
                <div class="info-item"><span class="info-label">Year of Birth:</span><span class="info-value">{app['yob'] if app['yob'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Age:</span><span class="info-value">{age} years</span></div>
                <div class="info-item"><span class="info-label">Ethnicity:</span><span class="info-value">{app['ethnicity'] if app['ethnicity'] else 'Not specified'}</span></div>
                <div class="info-item"><span class="info-label">Disability:</span><span class="info-value">{app['disability'] if app['disability'] else 'None'}</span></div>
                <div class="info-item"><span class="info-label">Phone:</span><span class="info-value">{app['contact'] if app['contact'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Email:</span><span class="info-value">{app['email'] if app['email'] else 'Not provided'}</span></div>
            </div>
        </div>
        
        <!-- Education -->
        <div class="info-section">
            <div class="section-title">🎓 Education & Qualifications</div>
            <div class="info-grid">
                <div class="info-item"><span class="info-label">KCSE Year:</span><span class="info-value">{app['kcse'] if app['kcse'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">KCSE Grade:</span><span class="info-value">{app['kcse_grade'] if app['kcse_grade'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Highest Qualification:</span><span class="info-value">{app['qualifications'] if app['qualifications'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Institution:</span><span class="info-value">{app['institution'] if app['institution'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Graduation Year:</span><span class="info-value">{app['graduation_year'] if app['graduation_year'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Professional Body:</span><span class="info-value">{app['professional_body'] if app['professional_body'] else 'N/A'}</span></div>
            </div>
        </div>
        
        <!-- Location & Experience -->
        <div class="info-section">
            <div class="section-title">📍 Location & Work Experience</div>
            <div class="info-grid">
                <div class="info-item"><span class="info-label">Sub-County:</span><span class="info-value">{app['subcounty'] if app['subcounty'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Ward:</span><span class="info-value">{app['ward'] if app['ward'] else 'N/A'}</span></div>
                <div class="info-item"><span class="info-label">Experience:</span><span class="info-value">{app['experience_years'] if app['experience_years'] else 0} years</span></div>
                <div class="info-item"><span class="info-label">Current Employer:</span><span class="info-value">{app['current_employer'] if app['current_employer'] else 'N/A'}</span></div>
            </div>
        </div>
    """
    
    # Add Advertised Position Details if available
    if position_details is not None:
        profile_html += f"""
        <div class="info-section">
            <div class="section-title">📢 Advertised Position Details</div>
            <div class="info-grid">
                <div class="info-item"><span class="info-label">Position Title:</span><span class="info-value">{pos_title}</span></div>
                <div class="info-item"><span class="info-label">Position Code:</span><span class="info-value">{pos_code}</span></div>
                <div class="info-item"><span class="info-label">Department:</span><span class="info-value">{pos_dept}</span></div>
                <div class="info-item"><span class="info-label">Employment Type:</span><span class="info-value">{pos_emp_type}</span></div>
                <div class="info-item"><span class="info-label">Vacancies:</span><span class="info-value">{pos_vacancies}</span></div>
                <div class="info-item"><span class="info-label">Salary Range:</span><span class="info-value">{pos_salary}</span></div>
                <div class="info-item"><span class="info-label">Application Deadline:</span><span class="info-value">{pos_deadline}</span></div>
            </div>
            <div style="margin-top: 0.75rem;">
                <div class="info-item"><span class="info-label">Requirements:</span><span class="info-value">{pos_requirements}</span></div>
            </div>
            <div style="margin-top: 0.5rem;">
                <div class="info-item"><span class="info-label">Responsibilities:</span><span class="info-value">{pos_responsibilities}</span></div>
            </div>
        </div>
        """
    else:
        profile_html += """
        <div class="info-section">
            <div class="section-title">📢 Advertised Position Details</div>
            <div class="info-item"><span class="info-label">Note:</span><span class="info-value">No advertised position details available for this application.</span></div>
        </div>
        """
    
    # Add Referees section
    profile_html += f"""
        <!-- Referees -->
        <div class="info-section">
            <div class="section-title">👥 Referees</div>
            <div class="info-grid">
                <div class="info-item"><span class="info-label">Referee 1:</span><span class="info-value">{app['referee1_name'] if app['referee1_name'] else 'N/A'} ({app['referee1_contact'] if app['referee1_contact'] else 'N/A'})</span></div>
                <div class="info-item"><span class="info-label">Referee 2:</span><span class="info-value">{app['referee2_name'] if app['referee2_name'] else 'N/A'} ({app['referee2_contact'] if app['referee2_contact'] else 'N/A'})</span></div>
            </div>
        </div>
        
        <div class="footer-note">
            This is a computer-generated document. No signature is required.<br>
            Embu County Public Service Board | Integrity ● Transparency ● Excellence
        </div>
    </div>
    """
    
    st.markdown(profile_html, unsafe_allow_html=True)


def generate_position_details_html(position_details):
    """Generate HTML for advertised position details"""
    if position_details is None:
        return ""
    
    return f"""
    <div class="info-section">
        <div class="section-title">📢 Advertised Position Details</div>
        <div class="info-grid">
            <div class="info-item"><span class="info-label">Position Title:</span><span class="info-value">{position_details['position_title']}</span></div>
            <div class="info-item"><span class="info-label">Position Code:</span><span class="info-value">{position_details['position_code']}</span></div>
            <div class="info-item"><span class="info-label">Department:</span><span class="info-value">{position_details['department']}</span></div>
            <div class="info-item"><span class="info-label">Employment Type:</span><span class="info-value">{position_details['employment_type']}</span></div>
            <div class="info-item"><span class="info-label">Vacancies:</span><span class="info-value">{position_details['vacancies']}</span></div>
            <div class="info-item"><span class="info-label">Salary Range:</span><span class="info-value">{position_details['salary_range']}</span></div>
            <div class="info-item"><span class="info-label">Application Deadline:</span><span class="info-value">{position_details['application_deadline']}</span></div>
        </div>
        <div style="margin-top: 0.75rem;">
            <div class="info-item"><span class="info-label">Requirements:</span><span class="info-value">{position_details['requirements'] if position_details['requirements'] else 'Not specified'}</span></div>
        </div>
        <div style="margin-top: 0.5rem;">
            <div class="info-item"><span class="info-label">Responsibilities:</span><span class="info-value">{position_details['responsibilities'] if position_details['responsibilities'] else 'Not specified'}</span></div>
        </div>
    </div>
    """


def generate_applicant_pdf(app, position_details):
    """Generate and download PDF of applicant profile"""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    import io
    import base64
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=30)
    story.append(Paragraph("EMBU COUNTY PUBLIC SERVICE BOARD", title_style))
    story.append(Paragraph("Applicant Profile", styles['Heading2']))
    story.append(Spacer(1, 0.25 * inch))
    
    # Applicant details table
    data = [
        ["Application ID:", f"ECPSB/{app['id']}/{datetime.now().year}"],
        ["Application Date:", app['application_date'] if app['application_date'] else "Not recorded"],
        ["Position Applied:", app['position_applied']],
        ["Status:", app['application_status']],
        ["Full Name:", app['name']],
        ["ID Number:", app['id_number']],
        ["Gender:", app['gender']],
        ["Year of Birth:", str(app['yob'])],
        ["Phone:", app['contact']],
        ["Email:", app['email'] if app['email'] else "Not provided"],
        ["Qualifications:", app['qualifications'] if app['qualifications'] else "N/A"],
        ["Experience:", f"{app['experience_years'] if app['experience_years'] else 0} years"],
        ["Sub-County:", app['subcounty'] if app['subcounty'] else "N/A"],
    ]
    
    table = Table(data, colWidths=[2 * inch, 3.5 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("This is a computer-generated document.", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Download button
    st.download_button(
        label="📥 Download PDF",
        data=buffer,
        file_name=f"applicant_{app['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )


def generate_print_html(app, position_details):
    """Generate HTML for printing"""
    age = datetime.now().year - app['yob'] if app['yob'] else "N/A"
    
    position_html = ""
    if position_details is not None:
        position_html = f"""
        <div style="margin-bottom: 20px;">
            <h3 style="color: #1e3a5f; border-bottom: 2px solid #3b82f6; padding-bottom: 5px;">📢 Advertised Position Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Position Title:</strong></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{position_details['position_title']}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Position Code:</strong></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{position_details['position_code']}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Department:</strong></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{position_details['department']}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Employment Type:</strong></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{position_details['employment_type']}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Salary Range:</strong></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{position_details['salary_range']}</td></tr>
            </table>
        </div>
        """
    
    return f"""
    <html>
    <head>
        <title>Applicant Profile - {app['name']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ text-align: center; border-bottom: 2px solid #1e3a5f; margin-bottom: 30px; }}
            .county-name {{ font-size: 24px; font-weight: bold; color: #1e3a5f; }}
            .board-name {{ font-size: 18px; color: #2c5282; }}
            .profile-title {{ font-size: 20px; margin: 20px 0; }}
            h3 {{ color: #1e3a5f; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            td:first-child {{ font-weight: bold; width: 35%; background: #f5f5f5; }}
            .footer {{ text-align: center; font-size: 10px; color: #666; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; }}
            .status-badge {{ display: inline-block; padding: 3px 10px; border-radius: 15px; font-size: 12px; }}
            .status-Pending {{ background: #fef3c7; color: #d97706; }}
            .status-Shortlisted {{ background: #d1fae5; color: #059669; }}
            .status-Hired {{ background: #d1fae5; color: #059669; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="county-name">EMBU COUNTY</div>
            <div class="board-name">PUBLIC SERVICE BOARD</div>
            <div class="profile-title">APPLICANT PROFILE</div>
        </div>
        
        <h3>📋 Application Details</h3>
        <table>
            <tr><td>Application ID:</td><td>ECPSB/{app['id']}/{datetime.now().year}</td></tr>
            <tr><td>Application Date:</td><td>{app['application_date'] if app['application_date'] else 'Not recorded'}</td></tr>
            <tr><td>Position Applied:</td><td>{app['position_applied']}</td></tr>
            <tr><td>Status:</td><td><span class="status-badge status-{app['application_status']}">{app['application_status']}</span></td></tr>
        </table>
        
        <h3>👤 Personal Information</h3>
        <table>
            <tr><td>Full Name:</td><td>{app['name']}</td></tr>
            <tr><td>Gender:</td><td>{app['gender']}</td></tr>
            <tr><td>ID Number:</td><td>{app['id_number']}</td></tr>
            <tr><td>Year of Birth:</td><td>{app['yob']}</td></tr>
            <tr><td>Age:</td><td>{age} years</td></tr>
            <tr><td>Phone:</td><td>{app['contact']}</td></tr>
            <tr><td>Email:</td><td>{app['email'] if app['email'] else 'Not provided'}</td></tr>
        </table>
        
        <h3>🎓 Education</h3>
        <table>
            <tr><td>KCSE Year:</td><td>{app['kcse'] if app['kcse'] else 'N/A'}</td></tr>
            <tr><td>KCSE Grade:</td><td>{app['kcse_grade'] if app['kcse_grade'] else 'N/A'}</td></tr>
            <tr><td>Highest Qualification:</td><td>{app['qualifications'] if app['qualifications'] else 'N/A'}</td></tr>
            <tr><td>Institution:</td><td>{app['institution'] if app['institution'] else 'N/A'}</td></tr>
        </table>
        
        {position_html}
        
        <div class="footer">
            This is a computer-generated document. No signature is required.<br>
            Embu County Public Service Board | Integrity ● Transparency ● Excellence
        </div>
    </body>
    </html>
    """
# =========================================================
# EXPORT CENTER
# =========================================================
def export_center():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">Export Center</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Export data in multiple formats with custom options</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM staff", conn)
    conn.close()
    
    if df.empty:
        st.warning("No data available to export.")
        return
    
    st.subheader("📤 Export Options")
    
    export_format = st.radio("Select Export Format", ["Excel (.xlsx)", "CSV", "JSON"])
    
    # Column selection
    st.subheader("Select Columns to Export")
    all_columns = df.columns.tolist()
    selected_columns = st.multiselect("Choose columns", all_columns, default=all_columns)
    
    # Filter options
    st.subheader("Filter Data (Optional)")
    col1, col2 = st.columns(2)
    with col1:
        subcounty_export = st.multiselect("Sub-County", df['subcounty'].dropna().unique())
    with col2:
        gender_export = st.selectbox("Gender", ["All", "Male", "Female"])
    
    # Apply filters
    export_df = df[selected_columns].copy()
    if subcounty_export:
        export_df = export_df[export_df['subcounty'].isin(subcounty_export)]
    if gender_export != "All":
        export_df = export_df[export_df['gender'] == gender_export]
    
    st.info(f"📄 {len(export_df)} records will be exported")
    st.dataframe(export_df.head(), use_container_width=True)
    
    if export_format == "Excel (.xlsx)":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name='Staff Data', index=False)
            
            # Add summary sheet
            summary = pd.DataFrame({
                'Metric': ['Total Records', 'Date Exported', 'Exported By', 'Sub-Counties', 'Gender Distribution'],
                'Value': [
                    len(export_df),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.user['username'],
                    export_df['subcounty'].nunique() if 'subcounty' in export_df.columns else 'N/A',
                    f"Male: {len(export_df[export_df['gender']=='Male'])} | Female: {len(export_df[export_df['gender']=='Female'])}" if 'gender' in export_df.columns else 'N/A'
                ]
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)
        
        st.download_button(
            "📥 Download Excel File",
            output.getvalue(),
            f"ecde_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    elif export_format == "CSV":
        csv = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV File",
            csv,
            f"ecde_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    elif export_format == "JSON":
        json_str = export_df.to_json(orient='records', indent=2)
        st.download_button(
            "📥 Download JSON File",
            json_str,
            f"ecde_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "application/json",
            use_container_width=True
        )
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
# AUDIT TRAIL
# =========================================================
def audit_trail():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">🔒 Audit Trail</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Comprehensive system activity tracking and user monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.user["role"] != "Admin":
        st.error("⛔ Access Denied. Admin privileges required.")
        return
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    try:
        # First, ensure the audit_log table has all required columns
        if is_cloud:
            # PostgreSQL - add missing columns if they don't exist
            try:
                conn.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS ip_address TEXT")
                conn.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_agent TEXT")
                conn.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS session_id TEXT")
                conn.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS status TEXT")
                conn.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS before_value TEXT")
                conn.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS after_value TEXT")
                conn.commit()
            except:
                pass
        else:
            # SQLite - add missing columns
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(audit_log)")
            existing_cols = [col[1] for col in cursor.fetchall()]
            
            new_columns = ['ip_address', 'user_agent', 'session_id', 'status', 'before_value', 'after_value']
            for col in new_columns:
                if col not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE audit_log ADD COLUMN {col} TEXT")
                    except:
                        pass
            conn.commit()
        
        # Create views for better analysis
        st.subheader("📊 Audit Trail Dashboard")
        
        # Get statistics
        stats_df = pd.read_sql("""
            SELECT 
                COUNT(*) as total_audits,
                COUNT(DISTINCT username) as unique_users,
                DATE(MIN(timestamp)) as first_activity,
                DATE(MAX(timestamp)) as last_activity
            FROM audit_log
        """, conn)
        
        if not stats_df.empty and stats_df.iloc[0]['total_audits'] > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Activities", stats_df.iloc[0]['total_audits'])
            with col2:
                st.metric("Active Users", stats_df.iloc[0]['unique_users'])
            with col3:
                st.metric("First Activity", stats_df.iloc[0]['first_activity'][:10] if stats_df.iloc[0]['first_activity'] else 'N/A')
            with col4:
                st.metric("Last Activity", stats_df.iloc[0]['last_activity'][:10] if stats_df.iloc[0]['last_activity'] else 'N/A')
            
            st.markdown("---")
        
        # Activity by action type
        action_counts = pd.read_sql("""
            SELECT 
                action,
                COUNT(*) as count,
                DATE(timestamp) as date
            FROM audit_log
            GROUP BY action, DATE(timestamp)
            ORDER BY count DESC
            LIMIT 20
        """, conn)
        
        if not action_counts.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📈 Activity by Action Type")
                fig = px.bar(action_counts.head(10), x='action', y='count', 
                            title="Most Common Actions",
                            color='count',
                            color_continuous_scale='Blues')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("📊 Activity Timeline")
                daily_counts = pd.read_sql("""
                    SELECT 
                        DATE(timestamp) as date,
                        COUNT(*) as count
                    FROM audit_log
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                    LIMIT 30
                """, conn)
                if not daily_counts.empty:
                    fig2 = px.line(daily_counts, x='date', y='count', 
                                  title="Daily Activity Trend",
                                  markers=True)
                    fig2.update_layout(height=400)
                    st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("---")
        
        # Filters
        st.subheader("🔍 Filter Audit Log")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Date range filter
            date_range = st.selectbox("Date Range", 
                ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time", "Custom Range"],
                key="audit_date_range")
        
        with col2:
            # Action type filter
            actions = pd.read_sql("SELECT DISTINCT action FROM audit_log ORDER BY action", conn)
            action_list = ['All'] + actions['action'].tolist() if not actions.empty else ['All']
            selected_action = st.selectbox("Action Type", action_list, key="audit_action")
        
        with col3:
            # User filter
            users = pd.read_sql("SELECT DISTINCT username FROM audit_log ORDER BY username", conn)
            user_list = ['All'] + users['username'].tolist() if not users.empty else ['All']
            selected_user = st.selectbox("User", user_list, key="audit_user")
        
        with col4:
            # Status filter
            status_list = ['All', 'Success', 'Failed', 'Pending']
            selected_status = st.selectbox("Status", status_list, key="audit_status")
        
        # Build query with filters
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        # Date filter
        if date_range == "Last 24 Hours":
            query += " AND timestamp >= datetime('now', '-1 day')" if not is_cloud else " AND timestamp >= NOW() - INTERVAL '1 day'"
        elif date_range == "Last 7 Days":
            query += " AND timestamp >= datetime('now', '-7 days')" if not is_cloud else " AND timestamp >= NOW() - INTERVAL '7 days'"
        elif date_range == "Last 30 Days":
            query += " AND timestamp >= datetime('now', '-30 days')" if not is_cloud else " AND timestamp >= NOW() - INTERVAL '30 days'"
        elif date_range == "Last 90 Days":
            query += " AND timestamp >= datetime('now', '-90 days')" if not is_cloud else " AND timestamp >= NOW() - INTERVAL '90 days'"
        
        if selected_action != "All":
            query += " AND action = %s" if is_cloud else " AND action = ?"
            params.append(selected_action)
        
        if selected_user != "All":
            query += " AND username = %s" if is_cloud else " AND username = ?"
            params.append(selected_user)
        
        if selected_status != "All":
            query += " AND status = %s" if is_cloud else " AND status = ?"
            params.append(selected_status)
        
        query += " ORDER BY timestamp DESC LIMIT 1000"
        
        # Execute query
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
            # Format the dataframe for display
            display_df = audit_df.copy()
            
            # Format timestamp
            if 'timestamp' in display_df.columns:
                display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Select columns to display
            display_columns = ['timestamp', 'username', 'action', 'record_id', 'details', 'status', 'ip_address']
            available_cols = [col for col in display_columns if col in display_df.columns]
            display_df = display_df[available_cols]
            
            # Rename columns for better readability
            display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
            
            st.dataframe(display_df, use_container_width=True, height=500)
            
            # Export options
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Export full log
                csv = audit_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Full Audit Log (CSV)",
                    csv,
                    f"audit_log_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            with col2:
                # Export filtered results
                if len(audit_df) < len(display_df) or selected_action != "All" or selected_user != "All":
                    csv_filtered = audit_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Filtered Results (CSV)",
                        csv_filtered,
                        f"audit_log_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
            
            with col3:
                # Summary report
                if st.button("📊 Generate Summary Report", use_container_width=True):
                    summary = audit_df.groupby(['username', 'action']).size().reset_index(name='count')
                    summary = summary.sort_values('count', ascending=False)
                    st.subheader("📊 Activity Summary by User and Action")
                    st.dataframe(summary, use_container_width=True)
                    
                    csv_summary = summary.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Summary Report",
                        csv_summary,
                        f"audit_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )
        else:
            st.info("No audit records found matching your criteria.")
            
    except Exception as e:
        st.info(f"Audit trail is ready. Activities will appear here as users interact with the system.")
    
    conn.close()


# =========================================================
# IMPROVED LOG AUDIT FUNCTION
# =========================================================
def log_audit(username, action, record_id, details, status="Success", before_value=None, after_value=None):
    """Enhanced audit logging with more details"""
    try:
        conn = get_conn()
        c = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get additional info (optional - can be expanded)
        ip_address = "Not captured"
        user_agent = "Not captured"
        session_id = str(st.session_state.get('session_id', 'unknown'))
        
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
# BACKUP & RESTORE
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Backup Database")
        st.info("Create a backup of your entire database")
        if st.button("Create Backup", use_container_width=True):
            backup_file = f"backup_ecde_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy("ecde.db", backup_file)
            with open(backup_file, "rb") as f:
                st.download_button("⬇️ Download Backup", f, backup_file, use_container_width=True)
            st.success("Backup created successfully!")
            log_audit(st.session_state.user['username'], "BACKUP", 0, f"Created backup: {backup_file}")
    
    with col2:
        st.subheader("🔄 Restore Database")
        st.warning("⚠️ Restoring will overwrite current data!")
        uploaded_file = st.file_uploader("Choose backup file", type=["db"])
        if uploaded_file and st.button("Restore Database", use_container_width=True):
            confirm = st.checkbox("Confirm: I understand this will overwrite ALL current data")
            if confirm:
                with open("ecde.db", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                log_audit(st.session_state.user['username'], "RESTORE", 0, f"Restored database from backup")
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
                log_audit(st.session_state.user['username'], "SETTINGS_UPDATE", 0, "System settings updated")
        
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
    
    # Check if staff table exists and has data
    try:
        df = pd.read_sql("SELECT * FROM staff", conn)
    except:
        st.warning("Database not properly initialized. Please restart the application.")
        conn.close()
        return
    
    conn.close()
    
    if df.empty:
        st.warning("No data available to generate reports. Please import applicant data first.")
        return
    
    # Report type selector
    report_type = st.selectbox(
        "Select Report Type",
        ["📊 Applicant Summary Report", "📋 Shortlisted Candidates Report", "🎓 Qualifications Analysis", 
         "📍 Geographic Distribution", "📅 Application Timeline", "📑 Complete Export"]
    )
    
    # ==================== APPLICANT SUMMARY REPORT ====================
    if report_type == "📊 Applicant Summary Report":
        st.subheader("Applicant Summary Report")
        
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
        
        # Export button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Full Report (CSV)", csv, f"applicant_report_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
    
    # ==================== SHORTLISTED CANDIDATES REPORT ====================
    elif report_type == "📋 Shortlisted Candidates Report":
        st.subheader("Shortlisted Candidates Report")
        
        if 'application_status' in df.columns:
            shortlisted_df = df[df['application_status'] == 'Shortlisted']
            
            if shortlisted_df.empty:
                st.info("No shortlisted candidates found.")
            else:
                st.success(f"Total Shortlisted: {len(shortlisted_df)}")
                
                # Display shortlisted candidates
                display_cols = ['name', 'id_number', 'contact', 'qualifications', 'experience_years', 'subcounty']
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
        
        if 'qualifications' in df.columns:
            qual_counts = df['qualifications'].value_counts().head(15)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(x=qual_counts.values, y=qual_counts.index, orientation='h', 
                            title="Top Qualifications", labels={'x': 'Count', 'y': 'Qualification'})
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(qual_counts.reset_index().rename(columns={'index': 'Qualification', 'qualifications': 'Count'}), use_container_width=True)
        else:
            st.warning("Qualifications data not available")
    
    # ==================== GEOGRAPHIC DISTRIBUTION ====================
    elif report_type == "📍 Geographic Distribution":
        st.subheader("Geographic Distribution of Applicants")
        
        if 'subcounty' in df.columns:
            subcounty_counts = df['subcounty'].value_counts().head(15)
            
            fig = px.bar(x=subcounty_counts.values, y=subcounty_counts.index, orientation='h',
                        title="Applications by Sub-County", labels={'x': 'Number of Applicants', 'y': 'Sub-County'})
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(subcounty_counts.reset_index().rename(columns={'index': 'Sub-County', 'subcounty': 'Count'}), use_container_width=True)
        else:
            st.warning("Location data not available")
    
    # ==================== APPLICATION TIMELINE ====================
    elif report_type == "📅 Application Timeline":
        st.subheader("Application Timeline")
        
        if 'created_at' in df.columns:
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
        else:
            st.warning("Date data not available")
    
    # ==================== COMPLETE EXPORT ====================
    elif report_type == "📑 Complete Export":
        st.subheader("Complete Data Export")
        
        st.info("Export all applicant data in various formats")
        
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
    
    if st.session_state.user["role"] != "Admin":
        st.error("⛔ Access Denied. Admin privileges required.")
        return
    
    # Initialize session state for editing
    if 'editing_user' not in st.session_state:
        st.session_state.editing_user = None
    if 'changing_password_for' not in st.session_state:
        st.session_state.changing_password_for = None
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    cursor = conn.cursor()
    
    # =====================================================
    # EDIT USER FORM
    # =====================================================
    if st.session_state.editing_user:
        # Fetch user details
        if is_cloud:
            cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (st.session_state.editing_user,))
        else:
            cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (st.session_state.editing_user,))
        user_data = cursor.fetchone()
        
        if user_data:
            st.subheader(f"✏️ Edit User: {user_data[1]}")
            
            with st.form("edit_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username", value=user_data[1], disabled=True, help="Username cannot be changed")
                with col2:
                    new_role = st.selectbox("Role", ["User", "Admin"], index=0 if user_data[2] == "User" else 1)
                
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                        if is_cloud:
                            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_data[0]))
                        else:
                            cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_data[0]))
                        conn.commit()
                        st.success(f"✅ User '{user_data[1]}' updated successfully!")
                        st.session_state.editing_user = None
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.session_state.editing_user = None
                        st.rerun()
        
        st.markdown("---")
    
    # =====================================================
    # CHANGE PASSWORD FORM
    # =====================================================
    elif st.session_state.changing_password_for:
        # Fetch username
        if is_cloud:
            cursor.execute("SELECT id, username FROM users WHERE id = %s", (st.session_state.changing_password_for,))
        else:
            cursor.execute("SELECT id, username FROM users WHERE id = ?", (st.session_state.changing_password_for,))
        user_data = cursor.fetchone()
        
        if user_data:
            st.subheader(f"🔐 Change Password for: {user_data[1]}")
            
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
                            log_audit(st.session_state.user['username'], "PASSWORD_CHANGE", user_data[0], f"Password changed for user: {user_data[1]}")
                            st.session_state.changing_password_for = None
                            st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.session_state.changing_password_for = None
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
            users_df = pd.read_sql("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC", conn)
            
            if not users_df.empty:
                # Create a more interactive display
                for idx, user in users_df.iterrows():
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1, 1.5])
                        
                        with col1:
                            st.write(f"**{user['username']}**")
                        with col2:
                            st.write(user['role'])
                        with col3:
                            st.write(user['created_at'][:10] if user['created_at'] else "N/A")
                        with col4:
                            if user['username'] != st.session_state.user['username']:  # Can't edit self?
                                if st.button(f"✏️ Edit", key=f"edit_{user['id']}", use_container_width=True):
                                    st.session_state.editing_user = user['id']
                                    st.rerun()
                            else:
                                st.write("—")
                        with col5:
                            if user['username'] != st.session_state.user['username']:  # Can't delete self
                                if st.button(f"🔑 Password", key=f"pwd_{user['id']}", use_container_width=True):
                                    st.session_state.changing_password_for = user['id']
                                    st.rerun()
                            else:
                                st.write("—")
                        
                        # Delete button in a separate row with warning
                        if user['username'] != st.session_state.user['username']:
                            col1, col2, col3 = st.columns([4, 1, 4])
                            with col2:
                                if st.button(f"🗑️ Delete", key=f"delete_{user['id']}", use_container_width=True):
                                    confirm = st.checkbox(f"Confirm delete user '{user['username']}'?", key=f"confirm_{user['id']}")
                                    if confirm:
                                        if is_cloud:
                                            cursor.execute("DELETE FROM users WHERE id = %s", (user['id'],))
                                        else:
                                            cursor.execute("DELETE FROM users WHERE id = ?", (user['id'],))
                                        conn.commit()
                                        log_audit(st.session_state.user['username'], "DELETE_USER", user['id'], f"Deleted user: {user['username']}")
                                        st.success(f"✅ User '{user['username']}' deleted!")
                                        st.rerun()
                        st.markdown("---")
                
            else:
                st.info("No users found")
                
        except Exception as e:
            st.info("Users table ready. Create your first user below.")
    
    # =====================================================
    # CREATE NEW USER FORM
    # =====================================================
    if 'show_create_form' in st.session_state and st.session_state.show_create_form:
        st.markdown("---")
        st.subheader("➕ Create New User")
        
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*", placeholder="Choose a username", key="create_username")
                new_password = st.text_input("Password*", type="password", placeholder="Choose a password", key="create_password")
            with col2:
                new_role = st.selectbox("Role*", ["User", "Admin"], key="create_role")
                confirm_password = st.text_input("Confirm Password*", type="password", placeholder="Confirm password", key="create_confirm")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.form_submit_button("👤 Create User", use_container_width=True, type="primary"):
                    if not new_username or not new_password:
                        st.error("❌ Username and password are required")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match")
                    elif len(new_password) < 4:
                        st.error("❌ Password must be at least 4 characters")
                    else:
                        if create_user(new_username, new_password, new_role):
                            st.success(f"✅ User '{new_username}' created successfully!")
                            log_audit(st.session_state.user['username'], "CREATE_USER", 0, f"Created user: {new_username}")
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
# CREATE USER FUNCTION (Updated)
# =========================================================
def create_user(username, password, role):
    """Create a new user in the database"""
    try:
        conn = get_conn()
        if conn is None:
            st.error("Database connection failed")
            return False
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Convert username to lowercase for consistency
        username_lower = username.lower()
        
        # Hash the password
        hashed_password = hash_password(password)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if is_cloud:
            # PostgreSQL syntax
            cursor.execute("""
                INSERT INTO users (username, password, role, created_at)
                VALUES (%s, %s, %s, %s)
            """, (username_lower, hashed_password, role, created_at))
        else:
            # SQLite syntax
            cursor.execute("""
                INSERT INTO users (username, password, role, created_at)
                VALUES (?, ?, ?, ?)
            """, (username_lower, hashed_password, role, created_at))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False

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
        - `NAME` - Full name
        - `ID NUMBER` - National ID
        - `CONTACT` - Phone number
        
        **Optional Columns:**
        - SNO, GENDER, YOB, ETHINICITY
        - QUALIFICATIONS, SUB-COUNTY, WARD
        - EXPERIENCE, KCSE/KCE, REMARKS
        """)
    
    st.markdown("---")
    
    # Step 3: Upload file
    st.subheader("Step 3: Upload Your Data")
    
    file = st.file_uploader("Choose Excel/CSV File", type=["xlsx", "xls", "csv"])
    
    if file is not None:
        try:
            # Read the file
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            st.success(f"✅ File loaded! Found {len(df)} rows")
            
            # Check if file matches template format
            template_columns = ['SNO', 'NAME', 'GENDER', 'ID NUMBER', 'YOB', 'ETHINICITY', 
                               'DISABILITY', 'CONTACT', 'KCSE/KCE', 'QUALIFICATIONS', 
                               'SUB-COUNTY', 'WARD', 'EXPERIENCE', 'REMARKS']
            
            file_columns = list(df.columns)
            
            # Check if columns match template (case-insensitive)
            is_template_format = all(col.upper() in [c.upper() for c in file_columns] for col in template_columns[:3])  # At least required columns
            
            if is_template_format:
                st.info("✅ File matches template format. Direct import available!")
                
                # Preview data
                with st.expander("📊 Preview data to import", expanded=True):
                    st.dataframe(df.head(10), use_container_width=True)
                
                # Direct import button
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🚀 DIRECT IMPORT", use_container_width=True, type="primary"):
                        with st.spinner("Importing data..."):
                            c = conn.cursor()
                            inserted = 0
                            skipped = 0
                            errors = []
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for idx, row in df.iterrows():
                                try:
                                    # Get values from template columns
                                    sno = int(row['SNO']) if pd.notna(row.get('SNO')) else idx + 1
                                    name = str(row['NAME']).strip() if pd.notna(row.get('NAME')) else ''
                                    gender = str(row['GENDER']).strip() if pd.notna(row.get('GENDER')) else ''
                                    id_number = str(row['ID NUMBER']).strip() if pd.notna(row.get('ID NUMBER')) else ''
                                    yob = int(row['YOB']) if pd.notna(row.get('YOB')) else 0
                                    ethnicity = str(row['ETHINICITY']).strip() if pd.notna(row.get('ETHINICITY')) else ''
                                    disability = str(row['DISABILITY']).strip() if pd.notna(row.get('DISABILITY')) else ''
                                    contact = str(row['CONTACT']).strip() if pd.notna(row.get('CONTACT')) else ''
                                    kcse = str(row['KCSE/KCE']).strip() if pd.notna(row.get('KCSE/KCE')) else ''
                                    qualifications = str(row['QUALIFICATIONS']).strip() if pd.notna(row.get('QUALIFICATIONS')) else ''
                                    subcounty = str(row['SUB-COUNTY']).strip() if pd.notna(row.get('SUB-COUNTY')) else ''
                                    ward = str(row['WARD']).strip() if pd.notna(row.get('WARD')) else ''
                                    experience = str(row['EXPERIENCE']).strip() if pd.notna(row.get('EXPERIENCE')) else ''
                                    remarks = str(row['REMARKS']).strip() if pd.notna(row.get('REMARKS')) else ''
                                    
                                    # Validate required fields
                                    if not name or name == 'nan':
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: Missing name")
                                        continue
                                    if not id_number or id_number == 'nan':
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: Missing ID number")
                                        continue
                                    if not contact or contact == 'nan':
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: Missing contact")
                                        continue
                                    
                                    # Check for duplicate ID
                                    if is_cloud:
                                        c.execute("SELECT id FROM staff WHERE id_number = %s", (id_number,))
                                    else:
                                        c.execute("SELECT id FROM staff WHERE id_number = ?", (id_number,))
                                    
                                    if c.fetchone():
                                        skipped += 1
                                        errors.append(f"Row {idx+2}: ID {id_number} already exists")
                                        continue
                                    
                                    # Insert data
                                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    username = st.session_state.user['username']
                                    application_date = datetime.now().strftime("%Y-%m-%d")
                                    
                                    if is_cloud:
                                        c.execute("""
                                            INSERT INTO staff (
                                                sno, name, gender, id_number, yob, ethnicity, disability, contact,
                                                kcse, qualifications, subcounty, ward, experience, remarks,
                                                position_applied, advertisement_ref, application_status,
                                                application_date, created_at, created_by
                                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """, (
                                            sno, name, gender, id_number, yob, ethnicity, disability, contact,
                                            kcse, qualifications, subcounty, ward, experience, remarks,
                                            selected_position_title, selected_position_code, 'Pending',
                                            application_date, now, username
                                        ))
                                    else:
                                        c.execute("""
                                            INSERT INTO staff (
                                                sno, name, gender, id_number, yob, ethnicity, disability, contact,
                                                kcse, qualifications, subcounty, ward, experience, remarks,
                                                position_applied, advertisement_ref, application_status,
                                                application_date, created_at, created_by
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            sno, name, gender, id_number, yob, ethnicity, disability, contact,
                                            kcse, qualifications, subcounty, ward, experience, remarks,
                                            selected_position_title, selected_position_code, 'Pending',
                                            application_date, now, username
                                        ))
                                    
                                    inserted += 1
                                    progress_bar.progress((idx + 1) / len(df))
                                    status_text.text(f"Processing: {idx+1}/{len(df)} | ✅ Inserted: {inserted} | ⚠️ Skipped: {skipped}")
                                    
                                except Exception as e:
                                    skipped += 1
                                    errors.append(f"Row {idx+2}: {str(e)[:100]}")
                            
                            conn.commit()
                            
                            st.success(f"✅ Import Completed!")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Records", len(df))
                            with col2:
                                st.metric("Inserted", inserted)
                            with col3:
                                st.metric("Skipped", skipped)
                            
                            if errors:
                                with st.expander(f"⚠️ Errors ({len(errors)} issues)"):
                                    for err in errors[:20]:
                                        st.write(f"- {err}")
                            
                            if inserted > 0:
                                st.balloons()
                                st.rerun()
            else:
                # Manual column mapping for custom files
                st.warning("File format doesn't match template. Please map columns manually.")
                
                st.subheader("Step 4: Map Columns")
                st.write("**Columns in your file:**", list(df.columns))
                
                # Column mapping
                col1, col2 = st.columns(2)
                
                with col1:
                    sno_col = st.selectbox("Select column for SERIAL NUMBER (SNO)", ['None'] + list(df.columns), key="sno_col")
                    name_col = st.selectbox("Select column for FULL NAME", ['None'] + list(df.columns), key="name_col")
                    id_col = st.selectbox("Select column for ID NUMBER", ['None'] + list(df.columns), key="id_col")
                    phone_col = st.selectbox("Select column for PHONE NUMBER", ['None'] + list(df.columns), key="phone_col")
                    email_col = st.selectbox("Select column for EMAIL (optional)", ['None'] + list(df.columns), key="email_col")
                
                with col2:
                    gender_col = st.selectbox("Select column for GENDER", ['None'] + list(df.columns), key="gender_col")
                    yob_col = st.selectbox("Select column for YEAR OF BIRTH", ['None'] + list(df.columns), key="yob_col")
                    qual_col = st.selectbox("Select column for QUALIFICATION", ['None'] + list(df.columns), key="qual_col")
                    exp_col = st.selectbox("Select column for EXPERIENCE", ['None'] + list(df.columns), key="exp_col")
                    subcounty_col = st.selectbox("Select column for SUB-COUNTY", ['None'] + list(df.columns), key="subcounty_col")
                    ward_col = st.selectbox("Select column for WARD", ['None'] + list(df.columns), key="ward_col")
                
                if name_col == 'None' or id_col == 'None' or phone_col == 'None':
                    st.error("❌ Please map the required columns: Full Name, ID Number, and Phone Number")
                    return
                
                # Preview mapped data
                st.subheader("Step 5: Preview")
                
                preview_df = pd.DataFrame()
                preview_df['Name'] = df[name_col]
                preview_df['ID Number'] = df[id_col]
                preview_df['Phone'] = df[phone_col]
                
                st.dataframe(preview_df.head(10), use_container_width=True)
                
                # Manual import button
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🚀 IMPORT DATA", use_container_width=True, type="primary"):
                        c = conn.cursor()
                        inserted = 0
                        skipped = 0
                        errors = []
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for idx, row in df.iterrows():
                            try:
                                name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ''
                                id_number = str(row[id_col]).strip() if pd.notna(row[id_col]) else ''
                                contact = str(row[phone_col]).strip() if pd.notna(row[phone_col]) else ''
                                
                                if not name or name == 'nan' or not id_number or id_number == 'nan':
                                    skipped += 1
                                    errors.append(f"Row {idx+2}: Missing name or ID")
                                    continue
                                
                                # Check for duplicate
                                if is_cloud:
                                    c.execute("SELECT id FROM staff WHERE id_number = %s", (id_number,))
                                else:
                                    c.execute("SELECT id FROM staff WHERE id_number = ?", (id_number,))
                                
                                if c.fetchone():
                                    skipped += 1
                                    errors.append(f"Row {idx+2}: ID {id_number} already exists")
                                    continue
                                
                                # Get optional values
                                sno = int(row[sno_col]) if sno_col != 'None' and pd.notna(row[sno_col]) else idx + 1
                                email = str(row[email_col]) if email_col != 'None' and pd.notna(row[email_col]) else ''
                                gender = str(row[gender_col]) if gender_col != 'None' and pd.notna(row[gender_col]) else ''
                                yob = int(row[yob_col]) if yob_col != 'None' and pd.notna(row[yob_col]) else 0
                                qualification = str(row[qual_col]) if qual_col != 'None' and pd.notna(row[qual_col]) else ''
                                experience = str(row[exp_col]) if exp_col != 'None' and pd.notna(row[exp_col]) else ''
                                subcounty = str(row[subcounty_col]) if subcounty_col != 'None' and pd.notna(row[subcounty_col]) else ''
                                ward = str(row[ward_col]) if ward_col != 'None' and pd.notna(row[ward_col]) else ''
                                
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                username = st.session_state.user['username']
                                application_date = datetime.now().strftime("%Y-%m-%d")
                                
                                if is_cloud:
                                    c.execute("""
                                        INSERT INTO staff (
                                            sno, name, contact, email, gender, yob, qualifications, 
                                            experience_years, subcounty, ward, position_applied, 
                                            advertisement_ref, application_status, application_date,
                                            created_at, created_by
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (
                                        sno, name, contact, email, gender, yob, qualification,
                                        experience, subcounty, ward, selected_position_title,
                                        selected_position_code, 'Pending', application_date, now, username
                                    ))
                                else:
                                    c.execute("""
                                        INSERT INTO staff (
                                            sno, name, contact, email, gender, yob, qualifications, 
                                            experience_years, subcounty, ward, position_applied, 
                                            advertisement_ref, application_status, application_date,
                                            created_at, created_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        sno, name, contact, email, gender, yob, qualification,
                                        experience, subcounty, ward, selected_position_title,
                                        selected_position_code, 'Pending', application_date, now, username
                                    ))
                                
                                inserted += 1
                                progress_bar.progress((idx + 1) / len(df))
                                status_text.text(f"Processing: {idx+1}/{len(df)} | ✅ Inserted: {inserted} | ⚠️ Skipped: {skipped}")
                                
                            except Exception as e:
                                skipped += 1
                                errors.append(f"Row {idx+2}: {str(e)[:100]}")
                        
                        conn.commit()
                        
                        st.success(f"✅ Import Completed!")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Records", len(df))
                        with col2:
                            st.metric("Inserted", inserted)
                        with col3:
                            st.metric("Skipped", skipped)
                        
                        if errors:
                            with st.expander(f"⚠️ Errors ({len(errors)} issues)"):
                                for err in errors[:20]:
                                    st.write(f"- {err}")
                        
                        if inserted > 0:
                            st.balloons()
                            st.rerun()
                                
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
    # ONLY INIT DB ONCE PER SESSION (FIXES 9.7s DELAY)
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
    def keep_alive():
        """Keep the database connection alive to prevent suspension"""
        try:
            conn = get_conn()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
        except Exception as e:
            pass  # Silently fail
    
    # Call keep_alive at startup
    keep_alive()
    
    # Check login status
    if "user" not in st.session_state or st.session_state.user is None:
        login()
        return
    
    # Get menu from sidebar (may return None if hidden)
    menu = sidebar()
    
    # Store selected menu in session state to persist when sidebar is hidden
    if menu is None and 'selected_menu' in st.session_state:
        menu = st.session_state.selected_menu
    elif menu is not None:
        st.session_state.selected_menu = menu
    
    # Router - All navigation options
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
    
    # Optional: Display total load time (remove in production)
    total_time = time.time() - app_start
    if total_time > 1.0:
        st.sidebar.markdown(f"---\n⏱️ **Load Time:** {total_time:.1f}s")

# =========================================================
# RUN APPLICATION
# =========================================================
if __name__ == "__main__":
    main()
