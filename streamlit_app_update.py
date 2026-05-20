import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
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
            conn = psycopg2.connect(database_url)
            return conn
        except Exception as e:
            st.error(f"❌ Database connection failed: {e}")
            return None
    else:
        # Running locally - use SQLite
        return sqlite3.connect("ecde.db", check_same_thread=False)

# =========================================================
# SECURITY FUNCTIONS
# =========================================================
def hash_password(password):
    salt = "ecde_secure_salt"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def login_user(username, password):
    conn = get_conn()
    if conn is None:
        return None
    
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    
    # Check if using PostgreSQL (cloud) or SQLite (local)
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    try:
        if is_cloud:
            # PostgreSQL syntax
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, hashed_password))
        else:
            # SQLite syntax
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
        
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        st.error(f"Login error: {e}")
        conn.close()
        return None

def create_default_admin():
    """Create default admin user if doesn't exist"""
    conn = get_conn()
    
    if conn is None:
        return
    
    c = conn.cursor()
    
    # Check if admin exists (using correct syntax for each database)
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    try:
        if is_cloud:
            c.execute("SELECT * FROM users WHERE username=%s", ("admin",))
        else:
            c.execute("SELECT * FROM users WHERE username=?", ("admin",))
        
        if not c.fetchone():
            # Insert admin user
            admin_password = hash_password("admin123")
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
            print("✅ Default admin user created (username: admin, password: admin123)")
    
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        conn.close()

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
            declaration_accepted TEXT DEFAULT 'No'
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
        
        # Audit log table
        c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            user TEXT,
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
        # HR TABLES (MISSING FROM YOUR VERSION)
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
            declaration_accepted TEXT DEFAULT 'No'
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
            user TEXT,
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
        # HR TABLES (MISSING FROM YOUR VERSION)
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
    # CREATE INDEXES (with HR indexes)
    # ===========================================
    
    if is_cloud:
        # PostgreSQL indexes
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_id_number ON staff(id_number)")
        except:
            pass
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_name ON staff(name)")
        except:
            pass
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_subcounty ON staff(subcounty)")
        except:
            pass
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_status ON staff(application_status)")
        except:
            pass
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_position ON position_applications(position_id)")
        except:
            pass
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_status ON position_applications(status)")
        except:
            pass
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_applicant ON position_applications(applicant_id)")
        except:
            pass
        # HR indexes
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_employees_staff_no ON employees(staff_no)")
        except:
            pass
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department)")
        except:
            pass
    else:
        # SQLite indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_id_number ON staff(id_number)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_name ON staff(name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_subcounty ON staff(subcounty)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_status ON staff(application_status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_position ON position_applications(position_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_status ON position_applications(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_position_applications_applicant ON position_applications(applicant_id)")
        # HR indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_employees_staff_no ON employees(staff_no)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department)")
    
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
    
    # Create tabs for HR modules
    hr_tab1, hr_tab2, hr_tab3, hr_tab4, hr_tab5 = st.tabs([
        "📊 HR Analytics",
        "👥 Staff Registry",
        "📈 Promotions",
        "🔄 Redesignation",
        "📄 Contracts"
    ])
    
    conn = get_conn()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    cursor = conn.cursor()
    
    # TAB 1: HR Analytics
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
                    total_employees = len(employees_df)
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Employees", total_employees)
                    col2.metric("Departments", employees_df['department'].nunique() if 'department' in employees_df.columns else 0)
                    col3.metric("Active Staff", total_employees)
                    
                    if 'department' in employees_df.columns:
                        st.subheader("Department Distribution")
                        dept_counts = employees_df['department'].value_counts().reset_index()
                        dept_counts.columns = ['Department', 'Employees']
                        st.dataframe(dept_counts, use_container_width=True)
        except Exception as e:
            st.info(f"HR Analytics ready. Add employees to see data. ({e})")
    
    # TAB 2: Staff Registry
    with hr_tab2:
        st.subheader("👥 Staff Registry")
        
        tab_add, tab_view = st.tabs(["➕ Add Staff", "📋 View Staff"])
        
        with tab_add:
            with st.form("add_employee_form_hr"):
                col1, col2 = st.columns(2)
                with col1:
                    staff_no = st.text_input("Staff No *", placeholder="e.g., ECPSB/001", key="hr_staff_no")
                    name = st.text_input("Full Name *", placeholder="Enter full name", key="hr_name")
                    personal_no = st.text_input("Personal No", placeholder="National ID", key="hr_personal_no")
                    age = st.number_input("Age", min_value=18, max_value=100, value=30, key="hr_age")
                    department = st.selectbox("Department", 
                        ["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Other"],
                        key="hr_department")
                with col2:
                    first_appointment_date = st.date_input("First Appointment Date", key="hr_appointment_date")
                    current_designation = st.text_input("Current Designation", key="hr_designation")
                    current_job_group = st.text_input("Current Job Group", key="hr_job_group")
                    academic_qualifications = st.text_area("Academic Qualifications", height=80, key="hr_academic")
                    professional_qualifications = st.text_area("Professional Qualifications", height=80, key="hr_professional")
                
                if st.form_submit_button("💾 Save Employee"):
                    if not staff_no or not name:
                        st.error("Staff No and Name are required!")
                    else:
                        try:
                            # Create table if not exists
                            if is_cloud:
                                cursor.execute("""
                                    CREATE TABLE IF NOT EXISTS employees (
                                        staff_no TEXT PRIMARY KEY,
                                        name TEXT,
                                        personal_no TEXT,
                                        age INTEGER,
                                        department TEXT,
                                        first_appointment_date TEXT,
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
                                        staff_no TEXT PRIMARY KEY,
                                        name TEXT,
                                        personal_no TEXT,
                                        age INTEGER,
                                        department TEXT,
                                        first_appointment_date TEXT,
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
                            if is_cloud:
                                cursor.execute("""
                                    INSERT INTO employees (staff_no, name, personal_no, age, department, first_appointment_date, current_designation, current_job_group, academic_qualifications, professional_qualifications, created_at, created_by)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (staff_no, name, personal_no, age, department, str(first_appointment_date), current_designation, current_job_group, academic_qualifications, professional_qualifications, now, st.session_state.user['username']))
                            else:
                                cursor.execute("""
                                    INSERT INTO employees (staff_no, name, personal_no, age, department, first_appointment_date, current_designation, current_job_group, academic_qualifications, professional_qualifications, created_at, created_by)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (staff_no, name, personal_no, age, department, str(first_appointment_date), current_designation, current_job_group, academic_qualifications, professional_qualifications, now, st.session_state.user['username']))
                            conn.commit()
                            st.success(f"✅ Employee {name} added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        
        with tab_view:
            search = st.text_input("🔍 Search by Name or Staff No", placeholder="Type to search...", key="hr_search")
            try:
                employees_df = pd.read_sql("SELECT * FROM employees ORDER BY name", conn)
                if employees_df.empty:
                    st.info("No employee records yet. Use 'Add Staff' tab to add employees.")
                else:
                    if search:
                        employees_df = employees_df[employees_df['name'].str.contains(search, case=False, na=False) | employees_df['staff_no'].str.contains(search, case=False, na=False)]
                    st.dataframe(employees_df, use_container_width=True)
            except Exception as e:
                st.info("Employee table not ready yet. Add your first employee.")
    
    # TAB 3: Promotions
    with hr_tab3:
        st.subheader("📈 Promotions Management")
        st.info("Promotion records will be displayed here")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']}" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_promo_employee")
                new_designation = st.text_input("New Designation", key="hr_promo_designation")
                effective_date = st.date_input("Effective Date", key="hr_promo_date")
                
                if st.button("Process Promotion", key="hr_promo_btn"):
                    if selected_employee != "Select employee...":
                        st.success(f"Promotion processed for {selected_employee}!")
                    else:
                        st.warning("Please select an employee")
            else:
                st.warning("No employees found. Please add employees in Staff Registry first.")
        except:
            st.info("Add employees to enable promotions")
    
    # TAB 4: Redesignation
    with hr_tab4:
        st.subheader("🔄 Redesignation Management")
        st.info("Redesignation records will be displayed here")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']}" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_redesign_employee")
                new_department = st.selectbox("New Department", 
                    ["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture", "Other"],
                    key="hr_redesign_dept")
                new_designation = st.text_input("New Designation", key="hr_redesign_designation")
                effective_date = st.date_input("Effective Date", key="hr_redesign_date")
                
                if st.button("Process Redesignation", key="hr_redesign_btn"):
                    if selected_employee != "Select employee...":
                        st.success(f"Redesignation processed for {selected_employee}!")
                    else:
                        st.warning("Please select an employee")
            else:
                st.warning("No employees found. Please add employees in Staff Registry first.")
        except:
            st.info("Add employees to enable redesignation")
    
    # TAB 5: Contracts
    with hr_tab5:
        st.subheader("📄 Contract Management")
        st.info("Contract records will be displayed here")
        
        try:
            employees_df = pd.read_sql("SELECT staff_no, name FROM employees ORDER BY name", conn)
            if not employees_df.empty:
                employee_options = ["Select employee..."] + [f"{row['staff_no']} - {row['name']}" for _, row in employees_df.iterrows()]
                selected_employee = st.selectbox("Select Staff", employee_options, key="hr_contract_employee")
                start_date = st.date_input("Start Date", key="hr_contract_start")
                end_date = st.date_input("End Date", key="hr_contract_end")
                contract_type = st.selectbox("Contract Type", ["Permanent", "Contract", "Temporary", "Internship"], key="hr_contract_type")
                
                if st.button("Save Contract", key="hr_contract_btn"):
                    if selected_employee != "Select employee...":
                        st.success(f"Contract saved for {selected_employee}!")
                    else:
                        st.warning("Please select an employee")
            else:
                st.warning("No employees found. Please add employees in Staff Registry first.")
        except:
            st.info("Add employees to enable contract management")
    
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
    
    /* ============================================
       HIDE THE NATIVE STREAMLIT TOGGLE BUTTON (<<<)
       ============================================ */
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    /* Also hide the sidebar resize handle */
    [data-testid="stSidebar"] [data-testid="stMarkdown"] + div {
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
def log_audit(user, action, record_id, details):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO audit_log (user, action, record_id, details, timestamp)
            VALUES (?,?,?,?,?)
        """, (user, action, record_id, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except:
        pass


# =========================================================
# SIDEBAR
# =========================================================
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
        # DATABASE QUICK STATS
        # =====================================================
        try:
            conn = get_conn()
            c = conn.cursor()

            c.execute("SELECT COUNT(*) FROM staff")
            total_staff = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM staff WHERE application_status='Pending'")
            pending = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM staff WHERE application_status='Shortlisted'")
            shortlisted = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM staff WHERE application_status='Approved'")
            approved = c.fetchone()[0]

            conn.close()

        except:
            total_staff = 0
            pending = 0
            shortlisted = 0
            approved = 0

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 18px;">
            <div style="background: rgba(255,255,255,0.08); padding: 12px; border-radius: 12px; text-align: center;">
                <div style="font-size: 11px; color: #cbd5e1;">Total</div>
                <div style="font-size: 20px; font-weight: 700; color: white; margin-top: 4px;">{total_staff}</div>
            </div>
            <div style="background: rgba(255,255,255,0.08); padding: 12px; border-radius: 12px; text-align: center;">
                <div style="font-size: 11px; color: #cbd5e1;">Pending</div>
                <div style="font-size: 20px; font-weight: 700; color: #f59e0b; margin-top: 4px;">{pending}</div>
            </div>
            <div style="background: rgba(255,255,255,0.08); padding: 12px; border-radius: 12px; text-align: center;">
                <div style="font-size: 11px; color: #cbd5e1;">Shortlisted</div>
                <div style="font-size: 20px; font-weight: 700; color: #3b82f6; margin-top: 4px;">{shortlisted}</div>
            </div>
            <div style="background: rgba(255,255,255,0.08); padding: 12px; border-radius: 12px; text-align: center;">
                <div style="font-size: 11px; color: #cbd5e1;">Approved</div>
                <div style="font-size: 20px; font-weight: 700; color: #10b981; margin-top: 4px;">{approved}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # =====================================================
        # NAVIGATION MENU
        # =====================================================
        menu_options = {
            "📊 Dashboard": "Overview & KPIs",
            "👥 Staff Profile": "View staff profiles",
            "📝 Applicant Registration": "Register applicants",
            "✏️ Edit Application": "Modify applications",
            "⭐ Shortlist Management": "Manage shortlisted candidates",
            "📊 Scoresheet": "Panelist scoring",
            "📈 Position Dashboard": "Position analytics",
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
            background: rgba(255,255,255,0.06);
            padding: 10px;
            border-radius: 10px;
            margin-top: 10px;
            margin-bottom: 16px;
            font-size: 12px;
            color: #cbd5e1;
        ">
            {menu_options[menu]}
        </div>
        """, unsafe_allow_html=True)

        # =====================================================
        # SYSTEM STATUS
        # =====================================================
        st.markdown("""
        <div style="
            background: rgba(16,185,129,0.12);
            border: 1px solid rgba(16,185,129,0.2);
            padding: 12px;
            border-radius: 12px;
            margin-bottom: 18px;
        ">
            <div style="display: flex; align-items: center; gap: 8px; color: #10b981; font-size: 13px; font-weight: 600;">
                🟢 System Online
            </div>
            <div style="margin-top: 6px; color: #cbd5e1; font-size: 11px;">
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
            text-align: center;
            margin-top: 22px;
            padding-top: 12px;
            border-top: 1px solid rgba(255,255,255,0.08);
            font-size: 11px;
            color: #94a3b8;
        ">
            ECPSB HR System v2.0<br>
            Embu County Government
        </div>
        """, unsafe_allow_html=True)

    return menu
# =========================================================
# TEST DATA GENERATOR
# =========================================================
def generate_test_data():
    """Generate and populate test data for the system"""
    
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">🧪 Test Data Generator</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Populate the system with sample data for testing</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.user["role"] != "Admin":
        st.error("⛔ Access Denied. Admin privileges required.")
        return
    
    st.warning("⚠️ This will add sample data to your database. Existing data will remain.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        num_records = st.number_input("Number of test records to generate", min_value=1, max_value=100, value=20, step=5)
    
    with col2:
        department = st.selectbox("Department/Focus", [
            "All Departments",
            "ECDE Teachers",
            "ECDE Trainers",
            "ECDE Supervisors",
            "ECDE Coordinators",
            "ECDE Administrators"
        ])
    
    if st.button("🚀 Generate Test Data", type="primary", use_container_width=True):
        with st.spinner(f"Generating {num_records} test records..."):
            generate_employees(num_records, department)
            generate_applicants(num_records, department)
            generate_advertised_positions()
        st.success(f"✅ Successfully generated test data!")
        st.balloons()

def generate_employees(num_records, department):
    """Generate test employee records"""
    conn = get_conn()
    cursor = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Sample data pools
    first_names = ["John", "Mary", "Peter", "Jane", "James", "Ann", "David", "Sarah", "Michael", "Grace",
                   "Joseph", "Esther", "Benjamin", "Ruth", "Samuel", "Deborah", "Daniel", "Hannah", "Paul", "Judith"]
    
    last_names = ["Kamau", "Wanjiku", "Otieno", "Muthoni", "Ochieng", "Njeri", "Kipchoge", "Akinyi", "Mwangi", "Chebet",
                  "Kariuki", "Atieno", "Maina", "Achieng", "Omondi", "Wambui", "Kibet", "Nyambura", "Ndegwa", "Wanjiru"]
    
    departments = ["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture"]
    
    designations = ["ECDE Teacher", "Senior ECDE Teacher", "ECDE Trainer", "ECDE Supervisor", 
                    "ECDE Coordinator", "ECDE Administrator", "Curriculum Developer", "Quality Assurance Officer"]
    
    job_groups = ["JG 'H'", "JG 'J'", "JG 'K'", "JG 'L'", "JG 'M'", "JG 'N'"]
    
    for i in range(num_records):
        staff_no = f"ECPSB/{datetime.now().year}/{1000 + i:04d}"
        name = f"{first_names[i % len(first_names)]} {last_names[i % len(last_names)]}"
        personal_no = f"{10000000 + i:08d}"
        age = random.randint(25, 60)
        dept = department if department != "All Departments" else departments[i % len(departments)]
        designation = designations[i % len(designations)]
        job_group = job_groups[i % len(job_groups)]
        appointment_date = f"{(datetime.now().year - random.randint(1, 15))}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created_by = st.session_state.user['username']
        
        try:
            if is_cloud:
                cursor.execute("""
                    INSERT INTO employees (staff_no, name, personal_no, age, department, first_appointment_date, 
                    current_designation, current_job_group, academic_qualifications, professional_qualifications, 
                    created_at, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (staff_no, name, personal_no, age, dept, appointment_date, designation, job_group,
                      "Bachelor's Degree in Education", "Certified ECDE Teacher", created_at, created_by))
            else:
                cursor.execute("""
                    INSERT INTO employees (staff_no, name, personal_no, age, department, first_appointment_date, 
                    current_designation, current_job_group, academic_qualifications, professional_qualifications, 
                    created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (staff_no, name, personal_no, age, dept, appointment_date, designation, job_group,
                      "Bachelor's Degree in Education", "Certified ECDE Teacher", created_at, created_by))
        except Exception as e:
            print(f"Error inserting employee {name}: {e}")
    
    conn.commit()
    conn.close()
    st.info(f"✅ Generated {num_records} employee records")

def generate_applicants(num_records, department):
    """Generate test applicant/staff records"""
    conn = get_conn()
    cursor = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Sample data pools
    first_names = ["James", "Lucy", "Robert", "Faith", "William", "Irene", "Charles", "Beatrice", "Stephen", "Catherine",
                   "Kennedy", "Mildred", "Fredrick", "Lilian", "Patrick", "Teresa", "Christopher", "Nancy", "Edward", "Rose"]
    
    last_names = ["Kimani", "Nyambura", "Wachira", "Wairimu", "Muriithi", "Wanjala", "Kiprono", "Mideva", "Odhiambo", "Okoth",
                  "Mutua", "Nduku", "Kilonzo", "Mbithi", "Munyao", "Mutiso", "Kioko", "Mwikali", "Musyoka", "Mutindi"]
    
    subcounties = ["Central", "East", "North", "South", "West", "Manyatta", "Runyenjes", "Mbeere North", "Mbeere South", "Siakago"]
    wards = ["Kithimu", "Kagaari", "Nginda", "Mufu", "Kiambere", "Gachoka", "Mavuria", "Kiritiri", "Evurore", "Mbita"]
    
    positions = [
        "ECDE Teacher - Permanent",
        "ECDE Teacher - Contract",
        "ECDE Trainer",
        "ECDE Supervisor",
        "ECDE Coordinator",
        "ECDE Curriculum Developer",
        "ECDE Administrator",
        "Intern ECDE Teacher"
    ]
    
    qualifications = ["ECDE Certificate", "ECDE Diploma", "Bachelor's Degree in ECDE", "Bachelor's Degree in Education"]
    statuses = ["Pending", "Shortlisted", "Interviewed", "Recommended", "Hired", "Rejected"]
    
    for i in range(num_records):
        sno = i + 1
        name = f"{first_names[i % len(first_names)]} {last_names[i % len(last_names)]}"
        gender = "Male" if i % 2 == 0 else "Female"
        id_number = f"{10000000 + i:08d}"
        yob = random.randint(1970, 2000)
        ethnicity = ["Kikuyu", "Luo", "Luhya", "Kalenjin", "Kamba", "Kisii", "Meru", "Embu"][i % 8]
        disability = "None" if i % 10 != 0 else "Physical Disability"
        contact = f"07{random.randint(10000000, 99999999)}"
        kcse = str(random.randint(2000, 2015))
        qualification = qualifications[i % len(qualifications)]
        subcounty = subcounties[i % len(subcounties)]
        ward = wards[i % len(wards)]
        experience = f"{random.randint(1, 15)} years of teaching experience"
        position = positions[i % len(positions)]
        status = statuses[i % len(statuses)] if i % 5 != 0 else "Pending"
        email = f"{name.lower().replace(' ', '.')}@example.com"
        kcse_grade = ["A", "A-", "B+", "B", "B-", "C+", "C"][i % 7]
        institution = ["Kenyatta University", "Moi University", "Mount Kenya University", "University of Nairobi"][i % 4]
        graduation_year = random.randint(2010, 2023)
        experience_years = random.randint(1, 20)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created_by = st.session_state.user['username']
        application_date = f"{(datetime.now().year)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        
        try:
            if is_cloud:
                cursor.execute("""
                    INSERT INTO staff (sno, name, gender, id_number, yob, ethnicity, disability, contact, kcse,
                    qualifications, subcounty, ward, experience, position_applied, application_status, email,
                    kcse_grade, institution, graduation_year, experience_years, created_at, created_by, application_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (sno, name, gender, id_number, yob, ethnicity, disability, contact, kcse, qualification,
                      subcounty, ward, experience, position, status, email, kcse_grade, institution,
                      graduation_year, experience_years, created_at, created_by, application_date))
            else:
                cursor.execute("""
                    INSERT INTO staff (sno, name, gender, id_number, yob, ethnicity, disability, contact, kcse,
                    qualifications, subcounty, ward, experience, position_applied, application_status, email,
                    kcse_grade, institution, graduation_year, experience_years, created_at, created_by, application_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sno, name, gender, id_number, yob, ethnicity, disability, contact, kcse, qualification,
                      subcounty, ward, experience, position, status, email, kcse_grade, institution,
                      graduation_year, experience_years, created_at, created_by, application_date))
        except Exception as e:
            print(f"Error inserting applicant {name}: {e}")
    
    conn.commit()
    conn.close()
    st.info(f"✅ Generated {num_records} applicant records")

def generate_advertised_positions():
    """Generate test advertised positions"""
    conn = get_conn()
    cursor = conn.cursor()
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    positions = [
        ("ECDE Teacher - Permanent", "ECDE/2024/01", "Early Childhood Education", "Permanent", 15,
         "Bachelor's Degree in ECDE or Education\nTSC Registration\nCPR Certification\nFirst Aid Certificate",
         "Teach children aged 3-5 years\nDevelop lesson plans\nAssess student progress\nParent communication",
         "KES 35,000 - 45,000", "2025-01-31", "Open"),
        ("ECDE Trainer", "ECDE/2024/02", "Training & Development", "Contract", 3,
         "Master's Degree in ECDE\n5+ years teaching experience\nTraining certification",
         "Train ECDE teachers\nDevelop training materials\nConduct workshops\nEvaluate training outcomes",
         "KES 60,000 - 80,000", "2025-01-15", "Open"),
        ("ECDE Supervisor", "ECDE/2024/03", "Quality Assurance", "Permanent", 5,
         "Bachelor's Degree\n3+ years supervisory experience\nValid driving license",
         "Supervise ECDE centers\nQuality assurance visits\nTeacher evaluation\nReport preparation",
         "KES 50,000 - 65,000", "2025-01-20", "Open")
    ]
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = st.session_state.user['username']
    
    for pos in positions:
        try:
            if is_cloud:
                cursor.execute("""
                    INSERT INTO advertised_positions (position_title, position_code, department, employment_type, vacancies,
                    requirements, responsibilities, salary_range, application_deadline, status, created_at, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (*pos, now, username))
            else:
                cursor.execute("""
                    INSERT INTO advertised_positions (position_title, position_code, department, employment_type, vacancies,
                    requirements, responsibilities, salary_range, application_deadline, status, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (*pos, now, username))
        except Exception as e:
            print(f"Error inserting position: {e}")
    
    conn.commit()
    conn.close()
    st.info(f"✅ Generated {len(positions)} advertised positions")
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
    # 2. FETCH DATA
    # ======================================================
    def get_data():
        """Fetch staff data from database"""
        try:
            conn = get_conn()
            df = pd.read_sql("SELECT * FROM staff", conn)
            conn.close()
            return df
        except Exception as e:
            return pd.DataFrame(columns=['application_status', 'subcounty', 'gender', 'yob', 'created_at'])
    
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
    cards = st.columns(4)
    
    kpi_data = [
        ("TOTAL STAFF", str(total_staff), "All Applicants"),
        ("PENDING APPLICATIONS", str(pending), "Requires review"),
        ("SHORTLISTED", str(shortlisted), "Candidates"),
        ("HIRED", str(hired), "This period"),
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
# STAFF PROFILE
# =========================================================
def staff_profile():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">Staff Profile</h1>
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
def data_entry():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">📝 Job Application Form</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">ECDE Teacher Recruitment - Register your application</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for better organization
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Position", "👤 Personal Information", "📚 Education", "📍 Location", "📎 Documents"])
    
    # Initialize variables
    position_applied = ""
    advertisement_ref = ""
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
    referee_name = ""
    referee_contact = ""
    remarks = ""
    
    with tab1:
        st.markdown("### 📋 Position Information")
        st.info("Please select the position you are applying for")
        
        col1, col2 = st.columns(2)
        
        with col1:
            position_applied = st.selectbox("🎯 Position Applied For*", [
                "Select Position",
                "ECDE Teacher - Permanent",
                "ECDE Teacher - Contract",
                "ECDE Trainer",
                "ECDE Supervisor",
                "ECDE Coordinator",
                "ECDE Curriculum Developer",
                "ECDE Administrator",
                "Intern ECDE Teacher",
                "Volunteer ECDE Teacher"
            ], help="Select the position you wish to apply for")
            
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
        
        # Previous application status
        previously_applied = st.radio("Have you applied for any ECDE position with us before?", ["No", "Yes"], horizontal=True)
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
        
        # KCSE Results
        st.markdown("#### 📖 KCSE Results")
        col1, col2 = st.columns(2)
        with col1:
            kcse_year = st.number_input("KCSE Year", min_value=2000, max_value=2026, step=1, help="Year of KCSE completion")
        with col2:
            kcse_grade = st.selectbox("KCSE Mean Grade", [
                "Select Grade",
                "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-"
            ], help="Overall KCSE mean grade")
        
        # Highest Qualification
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
        
        # Professional Certifications
        st.markdown("#### 📜 Professional Certifications")
        professional_body = st.text_input("Professional Body Registration", 
                                         placeholder="e.g., TSC Registration Number",
                                         help="Teachers Service Commission registration number if registered")
        
        additional_certs = st.text_area("Other Certifications & Trainings", 
                                       placeholder="List any additional professional certifications, workshops, or short courses...",
                                       height=100)
    
    with tab4:
        st.markdown("### 📍 Location & Work Experience")
        
        # Current Location
        st.markdown("#### 🏠 Current Residence")
        col1, col2 = st.columns(2)
        with col1:
            subcounty = st.selectbox("🏢 Current Sub-County", [
                "Select Sub-County",
                "Central", "East", "North", "South", "West",
                "Kisumu Central", "Kisumu East", "Kisumu West", "Kisumu North", "Kisumu South",
                "Nairobi Central", "Nairobi North", "Nairobi South", "Nairobi West", "Nairobi East",
                "Mombasa Central", "Mombasa North", "Mombasa South", "Mombasa West",
                "Other"
            ], help="Your current sub-county of residence")
        with col2:
            ward = st.selectbox("🏘️ Current Ward", [
                "Select Ward",
                "Other"
            ], help="Your current ward of residence")
        
        # Contact Information
        st.markdown("#### 📞 Contact Information")
        col1, col2 = st.columns(2)
        with col1:
            contact = st.text_input("📱 Phone Number*", placeholder="07XXXXXXXX", help="Required - Format: 07XXXXXXXX")
        with col2:
            email = st.text_input("📧 Email Address", placeholder="youremail@example.com", help="For official communication")
        
        # Work Experience
        st.markdown("#### 💼 Work Experience")
        col1, col2 = st.columns(2)
        with col1:
            experience_years = st.slider("Years of Teaching Experience", 0, 40, 0, help="Total years of teaching experience")
        with col2:
            current_employer = st.text_input("Current Employer (if any)", placeholder="School/Institution name")
        
        experience_details = st.text_area("Work Experience Details", 
                                         placeholder="Describe your previous teaching positions:\n- School Name\n- Position held\n- Duration\n- Key responsibilities and achievements",
                                         height=150)
        
        # Availability
        earliest_start = st.date_input("📅 Earliest Start Date", help="When can you join if selected?")
    
    with tab5:
        st.markdown("### 📎 Additional Information & References")
        
        # Referees
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
        
        # Document Checklist
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
        
        # Declaration
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
    
    # Submit button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        submit = st.button("📤 Submit Application", use_container_width=True, type="primary")

    if submit:
        # Validation
        errors = []
        if position_applied == "Select Position":
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
                    sno,name,gender,id_number,yob,ethnicity,disability,contact,
                    kcse,qualifications,subcounty,ward,experience,remarks,
                    created_at,created_by
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    0,  # sno - auto-generated application number
                    name,
                    gender,
                    id_number,
                    yob if yob else 0,
                    ethnicity if ethnicity and ethnicity != "Select Ethnicity" else "",
                    disability if disability and disability != "None" else "",
                    contact,
                    kcse_year if kcse_year else 0,
                    f"{qualifications} from {institution} ({graduation_year}) | KCSE: {kcse_grade}",
                    subcounty if subcounty and subcounty != "Select Sub-County" else "",
                    ward if ward and ward != "Select Ward" else "",
                    f"{experience_years} years - {experience_details}",
                    full_remarks,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.user["username"]
                ))
                
                conn.commit()
                log_audit(st.session_state.user['username'], "APPLICATION_SUBMIT", c.lastrowid, f"Job application: {name} for {position_applied}")
                
                # Success message
                st.balloons()
                st.success(f"""
                ✅ **Application Successfully Submitted!**
                
                **Application Summary:**
                - Name: {name}
                - Position: {position_applied}
                - ID Number: {id_number}
                - Application Date: {application_date}
                
                **Next Steps:**
                1. You will receive a confirmation SMS/Email
                2. Shortlisted candidates will be contacted for interview
                3. Keep your phone accessible for communication
                
                Thank you for applying to the County ECDE Recruitment!
                """)
                
                # Clear form by rerunning
                st.rerun()
                
            except sqlite3.IntegrityError:
                st.error(f"❌ An application with ID Number {id_number} already exists! Please check your ID number.")
            except Exception as e:
                st.error(f"❌ Error submitting application: {str(e)}")
            finally:
                conn.close()
# =========================================================
# APPLICANT REGISTRATION (RECRUITMENT)
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
    
    # Simple search
    st.subheader("🔍 Quick Search")
    search = st.text_input("Search by Name or ID", placeholder="Type name or ID number...")
    
    # Apply filters
    filtered_df = df.copy()
    
    if search:
        filtered_df = filtered_df[
            filtered_df["name"].str.contains(search, case=False, na=False) |
            filtered_df["id_number"].str.contains(search, na=False)
        ]
    
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
    page_size = st.selectbox("Records per page", [10, 25, 50, 100, 200])
    total_pages = (len(filtered_df) + page_size - 1) // page_size
    page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    page_df = filtered_df.iloc[start_idx:end_idx]
    
    st.dataframe(page_df, use_container_width=True, height=400)
    st.caption(f"Page {page_number} of {total_pages}")
    
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
        applicant = pd.read_sql(f"SELECT * FROM staff WHERE id = {selected_applicant}", conn)
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
            
            # Edit form tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Position & Status", "👤 Personal Information", "📚 Education", "📍 Location & Experience", "📎 Additional Info"])
            
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
                
                # Remarks field
                remarks = st.text_area("Recruitment Remarks/Notes", value=app['remarks'] if app['remarks'] else "", height=100)
            
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
                
                # Save button
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    save_button = st.button("💾 Save Changes", use_container_width=True, type="primary")
            
            # Process save
            if save_button:
                conn = get_conn()
                c = conn.cursor()
                
                try:
                    # Build experience string
                    experience_str = f"{experience_years} years"
                    if experience_details:
                        experience_str += f" - {experience_details}"
                    
                    c.execute("""
                    UPDATE staff SET
                        position_applied = ?,
                        application_status = ?,
                        interview_date = ?,
                        interview_score = ?,
                        remarks = ?,
                        name = ?,
                        gender = ?,
                        id_number = ?,
                        yob = ?,
                        ethnicity = ?,
                        disability = ?,
                        contact = ?,
                        email = ?,
                        kcse = ?,
                        kcse_grade = ?,
                        qualifications = ?,
                        institution = ?,
                        graduation_year = ?,
                        professional_body = ?,
                        subcounty = ?,
                        ward = ?,
                        experience_years = ?,
                        current_employer = ?,
                        experience = ?,
                        referee1_name = ?,
                        referee1_contact = ?,
                        referee2_name = ?,
                        referee2_contact = ?
                    WHERE id = ?
                    """, (
                        position_applied,
                        application_status,
                        interview_date.strftime("%Y-%m-%d"),
                        interview_score,
                        remarks,
                        name,
                        gender,
                        id_number,
                        yob,
                        ethnicity,
                        disability,
                        contact,
                        email,
                        kcse_year,
                        kcse_grade,
                        qualifications,
                        institution,
                        graduation_year,
                        professional_body,
                        subcounty,
                        ward,
                        experience_years,
                        current_employer,
                        experience_str,
                        referee1_name,
                        referee1_contact,
                        referee2_name,
                        referee2_contact,
                        selected_applicant
                    ))
                    
                    conn.commit()
                    log_audit(st.session_state.user['username'], "EDIT_APPLICANT", selected_applicant, f"Updated applicant: {name}")
                    
                    st.success(f"✅ Application for {name} has been updated successfully!")
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error updating record: {str(e)}")
                finally:
                    conn.close()
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
        
        # Get connection for this tab only
        conn = get_conn()
        
        # Get all applicants
        applicants_df = pd.read_sql("SELECT id, name, id_number, contact, email, qualifications, experience_years, application_status, subcounty FROM staff ORDER BY id DESC", conn)
        conn.close()  # Close after reading
        
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
                        # Use a fresh connection for update
                        update_conn = get_conn()
                        if update_conn is None:
                            st.error("Database connection failed")
                        else:
                            update_cursor = update_conn.cursor()
                            success_count = 0
                            
                            for app_id in selected_ids:
                                try:
                                    update_cursor.execute("""
                                        UPDATE staff 
                                        SET application_status = 'Shortlisted',
                                            shortlist_date = CURRENT_TIMESTAMP,
                                            remarks = CASE 
                                                WHEN remarks IS NULL THEN 'Shortlisted on ' || CURRENT_TIMESTAMP
                                                ELSE remarks || ' | Shortlisted on ' || CURRENT_TIMESTAMP
                                            END
                                        WHERE id = ?
                                    """, (app_id,))
                                    success_count += 1
                                except Exception as e:
                                    st.error(f"Error shortlisting ID {app_id}: {e}")
                            
                            update_conn.commit()
                            
                            # Verify the update
                            update_cursor.execute("SELECT COUNT(*) FROM staff WHERE application_status = 'Shortlisted'")
                            new_count = update_cursor.fetchone()[0]
                            
                            update_conn.close()
                            
                            if success_count > 0:
                                st.success(f"✅ {success_count} candidate(s) have been shortlisted successfully!")
                                st.info(f"📊 Total shortlisted candidates in database: {new_count}")
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
                
                # Show file preview
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
                        id_list = list(dict.fromkeys(id_list))  # Remove duplicates
                        
                        conn_bulk = get_conn()
                        if conn_bulk:
                            cursor = conn_bulk.cursor()
                            
                            for id_num in id_list:
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
                            
                            conn_bulk.close()
                            st.rerun()
                
                # Show results after processing
                if st.session_state.bulk_processed:
                    st.markdown("---")
                    st.subheader("📊 Results")
                    
                    # Show matched candidates
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
                                    
                                    for candidate in st.session_state.bulk_matched:
                                        update_cursor.execute("""
                                            UPDATE staff 
                                            SET application_status = 'Shortlisted',
                                                shortlist_date = CURRENT_TIMESTAMP,
                                                remarks = CASE 
                                                    WHEN remarks IS NULL THEN 'Shortlisted via bulk upload'
                                                    ELSE remarks || ' | Shortlisted via bulk upload'
                                                END
                                            WHERE id = ?
                                        """, (candidate['id'],))
                                    
                                    update_conn.commit()
                                    
                                    # Verify
                                    update_cursor.execute("SELECT COUNT(*) FROM staff WHERE application_status = 'Shortlisted'")
                                    total_shortlisted = update_cursor.fetchone()[0]
                                    update_conn.close()
                                    
                                    st.success(f"✅ {len(st.session_state.bulk_matched)} candidates shortlisted successfully!")
                                    st.info(f"📊 Total shortlisted candidates: {total_shortlisted}")
                                    st.balloons()
                                    
                                    # Reset state and rerun
                                    st.session_state.bulk_processed = False
                                    st.session_state.bulk_matched = []
                                    st.session_state.bulk_not_found = []
                                    st.rerun()
                    else:
                        st.warning("No valid candidates found to shortlist")
                    
                    # Show not found
                    if st.session_state.bulk_not_found:
                        with st.expander(f"⚠️ {len(st.session_state.bulk_not_found)} IDs not found or already shortlisted"):
                            for item in st.session_state.bulk_not_found[:20]:
                                st.write(f"- {item}")
                            
                            if len(st.session_state.bulk_not_found) > 20:
                                st.write(f"... and {len(st.session_state.bulk_not_found) - 20} more")
                    
                    # Reset button
                    if st.button("🔄 Clear & Start Over", use_container_width=True):
                        st.session_state.bulk_processed = False
                        st.session_state.bulk_matched = []
                        st.session_state.bulk_not_found = []
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        
        st.markdown("---")
        st.markdown("### ✏️ Or Paste ID Numbers Manually")
        
        # Manual paste option
        manual_ids = st.text_area(
            "Paste ID Numbers (one per line)",
            placeholder="12345678\n87654321\n34567890",
            height=120,
            key="manual_shortlist_ids"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📋 Process Manual IDs", use_container_width=True):
                if manual_ids.strip():
                    id_list = [id_num.strip() for id_num in manual_ids.split('\n') if id_num.strip()]
                    
                    conn_manual = get_conn()
                    if conn_manual:
                        cursor = conn_manual.cursor()
                        matched = []
                        not_found = []
                        
                        for id_num in id_list:
                            cursor.execute("""
                                SELECT id, name, id_number, contact, application_status 
                                FROM staff 
                                WHERE id_number = ?
                            """, (id_num,))
                            result = cursor.fetchone()
                            
                            if result:
                                if result[4] != 'Shortlisted' and result[4] != 'Hired':
                                    matched.append({
                                        'id': result[0],
                                        'name': result[1],
                                        'id_number': result[2],
                                        'contact': result[3]
                                    })
                                else:
                                    not_found.append(f"{id_num} (Already {result[4]})")
                            else:
                                not_found.append(f"{id_num} (Not found)")
                        
                        if matched:
                            st.success(f"✅ Found {len(matched)} candidates")
                            for m in matched:
                                st.write(f"- {m['name']} (ID: {m['id_number']})")
                            
                            if st.button(f"⭐ Shortlist These {len(matched)} Candidates", use_container_width=True, type="primary"):
                                for m in matched:
                                    cursor.execute("""
                                        UPDATE staff 
                                        SET application_status = 'Shortlisted',
                                            shortlist_date = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    """, (m['id'],))
                                conn_manual.commit()
                                
                                cursor.execute("SELECT COUNT(*) FROM staff WHERE application_status = 'Shortlisted'")
                                total = cursor.fetchone()[0]
                                conn_manual.close()
                                
                                st.success(f"✅ {len(matched)} candidates shortlisted!")
                                st.info(f"📊 Total shortlisted: {total}")
                                st.rerun()
                        else:
                            st.warning("No valid ID numbers found")
                        conn_manual.close()
                else:
                    st.warning("Please paste ID numbers")
    
    # ==================== TAB 3: SHORTLISTED CANDIDATES ====================
    with tab3:
        st.subheader("📊 Shortlisted Candidates")
        
        # Refresh button
        col1, col2 = st.columns([3, 1])
        with col1:
            pass
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        # Get connection for viewing
        view_conn = get_conn()
        
        if view_conn is None:
            st.error("Cannot connect to database")
            return
        
        # Query with proper case-insensitive matching
        shortlisted_df = pd.read_sql("""
            SELECT id, name, id_number, contact, email, qualifications, experience_years, 
       subcounty, created_at, remarks
FROM staff  
            WHERE application_status = 'Shortlisted'
            ORDER BY shortlist_date DESC, name
        """, view_conn)
        
        if shortlisted_df.empty:
            st.info("No candidates have been shortlisted yet. Use the tabs above to shortlist candidates.")
            
            # Debug: Show what statuses exist
            debug_df = pd.read_sql("SELECT application_status, COUNT(*) as count FROM staff GROUP BY application_status", view_conn)
            if not debug_df.empty:
                st.write("**Current statuses in database:**")
                st.dataframe(debug_df)
        else:
            st.success(f"✅ Total Shortlisted Candidates: {len(shortlisted_df)}")
            
            # Search within shortlisted
            search_shortlist = st.text_input("🔍 Search within shortlisted", placeholder="Search by name or ID...")
            
            if search_shortlist:
                shortlisted_df = shortlisted_df[
                    shortlisted_df['name'].str.contains(search_shortlist, case=False, na=False) |
                    shortlisted_df['id_number'].str.contains(search_shortlist, na=False)
                ]
            
            # Display shortlisted candidates
            st.dataframe(
                shortlisted_df[['name', 'id_number', 'contact', 'qualifications', 'experience_years', 'subcounty']],
                use_container_width=True,
                height=400
            )
            
            # Export shortlisted candidates
            csv = shortlisted_df.to_csv(index=False).encode('utf-8')
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Shortlist (CSV)",
                    csv,
                    f"shortlisted_candidates_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            # Option to remove from shortlist
            st.markdown("---")
            st.subheader("❌ Remove from Shortlist")
            
            remove_candidate = st.selectbox(
                "Select candidate to remove",
                shortlisted_df['id'].tolist(),
                format_func=lambda x: f"{shortlisted_df[shortlisted_df['id']==x]['name'].iloc[0]} - {shortlisted_df[shortlisted_df['id']==x]['id_number'].iloc[0]}"
            )
            
            if remove_candidate and st.button("Remove from Shortlist", use_container_width=True):
                remove_conn = get_conn()
                remove_cursor = remove_conn.cursor()
                remove_cursor.execute("UPDATE staff SET application_status = 'Pending' WHERE id = ?", (remove_candidate,))
                remove_conn.commit()
                remove_conn.close()
                st.success("Candidate removed from shortlist")
                st.rerun()
        
        view_conn.close()


# Helper function to shortlist candidates
def shortlist_candidates(candidate_ids, conn):
    """Helper function to shortlist multiple candidates"""
    c = conn.cursor()
    for candidate_id in candidate_ids:
        c.execute("""
            UPDATE staff 
            SET application_status = 'Shortlisted',
                remarks = CASE 
                    WHEN remarks IS NULL THEN 'Shortlisted on ' || datetime('now')
                    ELSE remarks || ' | Shortlisted on ' || datetime('now')
                END
            WHERE id = ?
        """, (candidate_id,))
        
        # Also update position_applications if exists
        try:
            c.execute("""
                UPDATE position_applications 
                SET status = 'Shortlisted', 
                    status_updated_date = datetime('now')
                WHERE applicant_id = ?
            """, (candidate_id,))
        except:
            pass
        
        log_audit(st.session_state.user['username'], "SHORTLIST", candidate_id, "Candidate shortlisted")
    conn.commit()
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
        <h1 style="color: white; margin: 0;">Audit Trail</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Track all system activities</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.user["role"] != "Admin":
        st.error("⛔ Access Denied. Admin privileges required.")
        return
    
    conn = get_conn()
    try:
        audit_df = pd.read_sql("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 500", conn)
        if not audit_df.empty:
            st.dataframe(audit_df, use_container_width=True)
            
            # Filter by user
            users = ['All'] + list(audit_df['user'].unique())
            selected_user = st.selectbox("Filter by User", users)
            if selected_user != "All":
                audit_df = audit_df[audit_df['user'] == selected_user]
                st.dataframe(audit_df, use_container_width=True)
            
            # Export audit log
            csv = audit_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Audit Log", csv, f"audit_log_{datetime.now().strftime('%Y%m%d')}.csv")
        else:
            st.info("No audit records found")
    except Exception as e:
        st.info(f"Audit trail feature - table exists but no records yet")
    finally:
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
    
    # Create tabs FIRST - THIS MUST BE HERE
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 Dropdown Options",
        "👥 Board Members",
        "📊 Scoring Criteria",
        "🎯 Scoring Parameters",
        "📢 Advertised Positions",
        "🔄 Recruitment Rounds",
        "⚙️ General Settings"
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
            # Display current options
            try:
                if is_cloud:
                    query = "SELECT id, option_value, option_order, is_active FROM dropdown_options WHERE category = %s ORDER BY option_order"
                    options_df = pd.read_sql(query, conn, params=(selected_category,))
                else:
                    options_df = pd.read_sql(f"SELECT id, option_value, option_order, is_active FROM dropdown_options WHERE category = '{selected_category}' ORDER BY option_order", conn)
                
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
                        
                        # Clear existing options
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
        
        # Initialize default board members if table is empty
        cursor.execute("SELECT COUNT(*) FROM panelists")
        if cursor.fetchone()[0] == 0:
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
        
        # Check if criteria exist, if not, insert defaults
        cursor.execute("SELECT COUNT(*) FROM scoring_criteria")
        if cursor.fetchone()[0] == 0:
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
                if is_cloud:
                    cursor.execute("""
                        INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
                        VALUES (%s, %s, %s, %s, 1)
                    """, criteria)
                else:
                    cursor.execute("""
                        INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
                        VALUES (?, ?, ?, ?, 1)
                    """, criteria)
            conn.commit()
        
        # Get current criteria
        criteria_df = pd.read_sql("SELECT id, criteria_key, criteria_name, max_score, description, is_active FROM scoring_criteria ORDER BY id", conn)
        
        st.markdown("### Scoring Criteria Configuration")
        
        edited_criteria = st.data_editor(
            criteria_df[['criteria_name', 'max_score', 'description', 'is_active']],
            use_container_width=True,
            key="criteria_editor"
        )
        
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
        
        total_max = criteria_df['max_score'].sum()
        st.info(f"📊 **Total Possible Score: {total_max} points**")
    
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
        
        positions_df = pd.read_sql("SELECT * FROM advertised_positions ORDER BY id DESC", conn)
        
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
                    st.write(position['requirements'])
                    st.write("**Responsibilities:**")
                    st.write(position['responsibilities'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        new_status = st.selectbox(f"Status", ["Open", "Closed", "On Hold"], key=f"status_{position['id']}", index=["Open", "Closed", "On Hold"].index(position['status']))
                        if st.button(f"Update", key=f"update_{position['id']}"):
                            if is_cloud:
                                cursor.execute("UPDATE advertised_positions SET status = %s WHERE id = %s", (new_status, position['id']))
                            else:
                                cursor.execute("UPDATE advertised_positions SET status = ? WHERE id = ?", (new_status, position['id']))
                            conn.commit()
                            st.success(f"Status updated to {new_status}")
                            st.rerun()
                    with col3:
                        if st.button(f"🗑️ Delete", key=f"delete_{position['id']}"):
                            if is_cloud:
                                cursor.execute("DELETE FROM advertised_positions WHERE id = %s", (position['id'],))
                            else:
                                cursor.execute("DELETE FROM advertised_positions WHERE id = ?", (position['id'],))
                            conn.commit()
                            st.warning(f"Position deleted")
                            st.rerun()
        else:
            st.info("No advertised positions yet.")
    
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
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Manage system users and permissions</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.user["role"] != "Admin":
        st.error("⛔ Access Denied. Admin privileges required.")
        return
    
    # Display existing users
    conn = get_conn()
    try:
        users_df = pd.read_sql("SELECT username, role, created_at FROM users ORDER BY created_at", conn)
        if not users_df.empty:
            st.subheader("📋 Existing Users")
            st.dataframe(users_df, use_container_width=True)
    except Exception as e:
        st.info("No users found or table not ready")
    finally:
        conn.close()
    
    st.markdown("---")
    st.subheader("➕ Create New User")
    
    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("Username", placeholder="Choose a username", key="new_username")
        new_password = st.text_input("Password", type="password", placeholder="Choose a password", key="new_password")
    
    with col2:
        new_role = st.selectbox("Role", ["User", "Admin"], key="new_role")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password", key="confirm_password")
    
    if st.button("👤 Create User", use_container_width=True, key="create_btn"):
        if not new_username or not new_password:
            st.error("Username and password are required")
        elif new_password != confirm_password:
            st.error("Passwords do not match")
        else:
            if create_user(new_username, new_password, new_role):
                st.success(f"User {new_username} created successfully!")
                st.rerun()
            else:
                st.error(f"Username {new_username} may already exist")
def create_user(username, password, role):
    """Create a new user in the database"""
    try:
        conn = get_conn()
        if conn is None:
            st.error("Database connection failed")
            return False
        
        cursor = conn.cursor()
        is_cloud = st.secrets.get("DATABASE_URL") is not None
        
        # Hash the password using your existing hash_password function
        hashed_password = hash_password(password)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if is_cloud:
            # PostgreSQL syntax
            cursor.execute("""
                INSERT INTO users (username, password, role, created_at)
                VALUES (%s, %s, %s, %s)
            """, (username, hashed_password, role, created_at))
        else:
            # SQLite syntax
            cursor.execute("""
                INSERT INTO users (username, password, role, created_at)
                VALUES (?, ?, ?, ?)
            """, (username, hashed_password, role, created_at))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False
# =========================================================
# IMPORT EXCEL WITH FLEXIBLE COLUMN MAPPING
# =========================================================
def import_excel():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">📥 Import Applicant Data</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Import job applications based on advertised positions</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    
    # Step 1: Select advertised position
    st.subheader("Step 1: Select Advertised Position")
    
    positions_df = pd.read_sql("SELECT * FROM advertised_positions WHERE status = 'Open' ORDER BY id DESC", conn)
    
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
    
    st.info(f"**Position:** {selected_position_data['position_title']} | **Code:** {selected_position_data['position_code']} | **Vacancies:** {selected_position_data['vacancies']}")
    
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
        st.download_button("📥 Download Template", csv, "import_template.csv", "text/csv")
    
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
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
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
                gender_col = st.selectbox("Select column for GENDER (optional)", ['None'] + list(df.columns), key="gender_col")
                yob_col = st.selectbox("Select column for YEAR OF BIRTH (YOB)", ['None'] + list(df.columns), key="yob_col")
                qual_col = st.selectbox("Select column for QUALIFICATION (optional)", ['None'] + list(df.columns), key="qual_col")
                exp_col = st.selectbox("Select column for EXPERIENCE (optional)", ['None'] + list(df.columns), key="exp_col")
                subcounty_col = st.selectbox("Select column for SUB-COUNTY (optional)", ['None'] + list(df.columns), key="subcounty_col")
                ward_col = st.selectbox("Select column for WARD (optional)", ['None'] + list(df.columns), key="ward_col")
            
            if name_col == 'None' or id_col == 'None' or phone_col == 'None':
                st.error("❌ Please map the required columns: Full Name, ID Number, and Phone Number")
                return
            
            # Preview mapped data
            st.subheader("Step 5: Preview")
            
            preview_df = pd.DataFrame()
            preview_df['SNO'] = df[sno_col] if sno_col != 'None' else ''
            preview_df['Name'] = df[name_col]
            preview_df['ID Number'] = df[id_col]
            preview_df['Phone'] = df[phone_col]
            
            st.dataframe(preview_df.head(10), use_container_width=True)
            
            # Import button
            if st.button("🚀 Import Data", type="primary", use_container_width=True):
                c = conn.cursor()
                inserted = 0
                skipped = 0
                errors = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, row in df.iterrows():
                    try:
                        name = str(row[name_col]).strip()
                        id_number = str(row[id_col]).strip()
                        phone = str(row[phone_col]).strip()
                        
                        if not name or name == 'nan' or not id_number or id_number == 'nan':
                            skipped += 1
                            errors.append(f"Row {idx+2}: Missing name or ID")
                            continue
                        
                        # Check for duplicate
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
                        
                        c.execute("""
                            INSERT INTO staff (
                                sno, name, id_number, contact, email, gender, yob, qualifications, experience_years,
                                subcounty, ward, position_applied, application_status, created_at, created_by
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            sno, name, id_number, phone, email, gender, yob, qualification, experience,
                            subcounty, ward, selected_position_data['position_title'], 'Pending',
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.user['username']
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
                        for err in errors[:10]:
                            st.write(f"- {err}")
                
                if inserted > 0:
                    st.balloons()
                    st.rerun()
                
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
    
    conn.close()
# =========================================================
# POSITION DASHBOARD
# =========================================================
def position_dashboard():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">📊 Position Dashboard</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Track recruitment progress by position</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_conn()
    
    try:
        # Get all positions from staff table (simple version)
        positions_df = pd.read_sql("SELECT DISTINCT position_applied FROM staff WHERE position_applied IS NOT NULL AND position_applied != ''", conn)
        
        if positions_df.empty:
            st.info("📢 No position data available. Applicant data will appear here once positions are assigned.")
            st.markdown("""
            ### How to get started:
            1. Go to **Applicant Registration** to add applicants
            2. Assign a position when registering
            3. Or use **Import Excel** to bulk upload applicants with positions
            4. Use **Shortlist Management** to update applicant status
            """)
            return
        
        st.subheader("📊 Recruitment Summary")
        
        # Create summary data
        summary_data = []
        for idx, row in positions_df.iterrows():
            position = row['position_applied']
            
            total = pd.read_sql(f"SELECT COUNT(*) as count FROM staff WHERE position_applied = '{position}'", conn)
            shortlisted = pd.read_sql(f"SELECT COUNT(*) as count FROM staff WHERE position_applied = '{position}' AND application_status = 'Shortlisted'", conn)
            interviewed = pd.read_sql(f"SELECT COUNT(*) as count FROM staff WHERE position_applied = '{position}' AND application_status = 'Interviewed'", conn)
            hired = pd.read_sql(f"SELECT COUNT(*) as count FROM staff WHERE position_applied = '{position}' AND application_status = 'Hired'", conn)
            
            summary_data.append({
                "Position": position,
                "Total Applications": total['count'].iloc[0],
                "Shortlisted": shortlisted['count'].iloc[0],
                "Interviewed": interviewed['count'].iloc[0],
                "Hired": hired['count'].iloc[0]
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Positions", len(positions_df))
        with col2:
            st.metric("Total Applications", summary_df['Total Applications'].sum())
        with col3:
            st.metric("Total Shortlisted", summary_df['Shortlisted'].sum())
        with col4:
            st.metric("Total Hired", summary_df['Hired'].sum())
        
        st.markdown("---")
        
        # Display table
        st.dataframe(summary_df, use_container_width=True)
        
        # Progress bars
        st.subheader("📈 Hiring Progress by Position")
        for idx, row in summary_df.iterrows():
            if row['Total Applications'] > 0:
                hire_rate = (row['Hired'] / row['Total Applications']) * 100
                st.write(f"**{row['Position']}** - Hired: {row['Hired']} / {row['Total Applications']} applicants")
                st.progress(min(hire_rate / 100, 1.0))
        
        # View applicants by position
        st.markdown("---")
        st.subheader("🔍 View Applicants by Position")
        
        selected_position = st.selectbox(
            "Select Position",
            positions_df['position_applied'].tolist()
        )
        
        if selected_position:
            applicants_df = pd.read_sql(f"""
                SELECT name, id_number, contact, qualifications, experience_years, 
                       application_status, created_at
                FROM staff 
                WHERE position_applied = '{selected_position}'
                ORDER BY created_at DESC
            """, conn)
            
            if not applicants_df.empty:
                st.write(f"**Total Applicants: {len(applicants_df)}**")
                st.dataframe(applicants_df, use_container_width=True)
                
                # Export
                csv = applicants_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Data",
                    csv,
                    f"applicants_{selected_position}.csv",
                    "text/csv"
                )
            else:
                st.info(f"No applicants found for {selected_position}")
                
    except Exception as e:
        st.info(f"Position dashboard is ready. Data will appear once you add applicants with positions.")
    
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
    
    # Create or verify panelists table
    def init_panelists_table():
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS panelists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                role TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Check if panelists exist
        c.execute("SELECT COUNT(*) FROM panelists")
        if c.fetchone()[0] == 0:
            # Insert default panelists
            default_panelists = [
                ("Board Member 1", "Board Member"),
                ("Board Member 2", "Board Member"),
                ("Board Member 3", "Board Member"),
                ("Board Member 4", "Board Member"),
                ("Board Member 5", "Board Member"),
                ("Board Member 6", "Board Member"),
                ("Board Member 7", "Board Member"),
                ("Technical Officer", "Technical Officer")
            ]
            c.executemany("INSERT INTO panelists (name, role) VALUES (?, ?)", default_panelists)
        conn.commit()
    
    init_panelists_table()
    
    # Create scores table
    def init_scores_table():
        c = conn.cursor()
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
        conn.commit()
    
    init_scores_table()
    
    # Get all shortlisted candidates
    shortlisted_df = pd.read_sql("""
        SELECT id, name, id_number, qualifications, experience_years, 
               position_applied, application_status
        FROM staff 
        WHERE application_status = 'Shortlisted' 
        ORDER BY name
    """, conn)
    
    if shortlisted_df.empty:
        st.info("📋 No shortlisted candidates found. Please shortlist candidates first using the Shortlist Management module.")
        return
    
    # Get panelists
    panelists_df = pd.read_sql("SELECT id, name, role FROM panelists WHERE is_active = 1", conn)
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Select Candidate", "✏️ Panelist Scoring", "📊 Panelist Summary", "🏆 Final Rankings"])
    
    # ==================== TAB 1: SELECT CANDIDATE ====================
    with tab1:
        st.subheader("🎯 Select Candidate to Score")
        
        selected_candidate = st.selectbox(
            "Choose Candidate",
            shortlisted_df['id'].tolist(),
            format_func=lambda x: f"{shortlisted_df[shortlisted_df['id']==x]['name'].iloc[0]} - {shortlisted_df[shortlisted_df['id']==x]['position_applied'].iloc[0]}"
        )
        
        if selected_candidate:
            candidate = shortlisted_df[shortlisted_df['id'] == selected_candidate].iloc[0]
            
            # Display candidate info
            st.markdown("---")
            st.subheader("📋 Candidate Information")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.text_input("Name", value=candidate['name'], disabled=True)
                st.text_input("ID Number", value=candidate['id_number'], disabled=True)
            with col2:
                st.text_input("Position Applied", value=candidate['position_applied'], disabled=True)
                st.text_input("Experience", value=f"{candidate['experience_years']} years", disabled=True)
            with col3:
                st.text_input("Qualifications", value=candidate['qualifications'][:50] if candidate['qualifications'] else "N/A", disabled=True)
            
            # Check scoring progress
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(DISTINCT panelist_id) as scored_count, 
                       (SELECT COUNT(*) FROM panelists WHERE is_active = 1) as total_panelists
                FROM panelist_scores 
                WHERE candidate_id = ?
            """, (selected_candidate,))
            result = c.fetchone()
            scored_count = result[0] if result[0] else 0
            total_panelists = result[1] if result[1] else 8
            
            st.info(f"📊 Scoring Progress: {scored_count}/{total_panelists} panelists have scored this candidate")
            
            if scored_count == total_panelists:
                st.success("✅ All panelists have completed scoring for this candidate!")
    
    # ==================== TAB 2: PANELIST SCORING ====================
    with tab2:
        st.subheader("✏️ Panelist Scoring")
        
        if 'selected_candidate' not in dir():
            st.warning("Please select a candidate in the 'Select Candidate' tab first.")
        else:
            # Select panelist
            st.markdown("### 👥 Select Panelist")
            
            # Get panelists who haven't scored this candidate yet
            c = conn.cursor()
            c.execute("""
                SELECT p.id, p.name, p.role
                FROM panelists p
                WHERE p.id NOT IN (
                    SELECT panelist_id FROM panelist_scores WHERE candidate_id = ?
                ) AND p.is_active = 1
            """, (selected_candidate,))
            
            available_panelists = c.fetchall()
            
            # Also get panelists who have already scored (for viewing)
            c.execute("""
                SELECT p.id, p.name, p.role, ps.total_score
                FROM panelists p
                JOIN panelist_scores ps ON p.id = ps.panelist_id
                WHERE ps.candidate_id = ?
            """, (selected_candidate,))
            completed_panelists = c.fetchall()
            
            if available_panelists:
                panelist_options = {p[0]: f"{p[1]} ({p[2]})" for p in available_panelists}
                selected_panelist = st.selectbox(
                    "Select Panelist (Only those who haven't scored)",
                    list(panelist_options.keys()),
                    format_func=lambda x: panelist_options[x]
                )
                
                if selected_panelist:
                    panelist_name = panelist_options[selected_panelist]
                    
                    st.markdown("---")
                    st.markdown(f"### 📝 Scoring by: {panelist_name}")
                    
                    # Scoring Criteria Section
                    st.markdown("#### Detailed Criteria Assessment")
                    st.info("Rate each criterion based on the candidate's performance")
                    
                    # Define scoring criteria
                    criteria = {
                        "academic": {
                            "name": "Academic and Professional Qualifications",
                            "max_score": 5,
                            "levels": {"Degree/Certificate (2)": 2, "Computer (1)": 1, "Form Four (2)": 2}
                        },
                        "hr_knowledge": {
                            "name": "Knowledge on Human Resource Management",
                            "max_score": 15,
                            "levels": {"Limited (0-5)": 5, "Average (6-10)": 10, "Good (11-15)": 15}
                        },
                        "procurement": {
                            "name": "Knowledge of Public Finance/Procurement",
                            "max_score": 15,
                            "levels": {"Limited (0-5)": 5, "Average (6-10)": 10, "Good (11-15)": 15}
                        },
                        "gov_structure": {
                            "name": "Government Structure & Organization Functions",
                            "max_score": 10,
                            "levels": {"Limited (0-2)": 2, "Average (3-5)": 5, "Good (6-10)": 10}
                        },
                        "leadership": {
                            "name": "Strategic Leadership Capability & Potential",
                            "max_score": 10,
                            "levels": {"Limited (0-2)": 2, "Average (3-5)": 5, "Good (6-10)": 10}
                        },
                        "communication": {
                            "name": "Communication Skills",
                            "max_score": 5,
                            "levels": {"Limited (0-2)": 2, "Average (3-4)": 4, "Good (5)": 5}
                        },
                        "general_knowledge": {
                            "name": "General Knowledge (National, Regional & Global Issues)",
                            "max_score": 5,
                            "levels": {"Limited (0-2)": 2, "Average (3-4)": 4, "Good (5)": 5}
                        },
                        "technical": {
                            "name": "Knowledge/Experience in the Technical Area",
                            "max_score": 35,
                            "levels": {"Limited (0-10)": 10, "Average (11-20)": 20, "Good (21-35)": 35}
                        }
                    }
                    
                    scores = {}
                    total_panelist_score = 0
                    
                    col1, col2 = st.columns(2)
                    
                    for idx, (key, criterion) in enumerate(criteria.items()):
                        with col1 if idx % 2 == 0 else col2:
                            st.markdown(f"**{criterion['name']}** (Max: {criterion['max_score']})")
                            
                            # Use number input for precise scoring
                            score = st.number_input(
                                f"Score for {criterion['name'][:30]}",
                                min_value=0,
                                max_value=criterion['max_score'],
                                value=0,
                                step=1,
                                key=f"{key}_{selected_candidate}_{selected_panelist}"
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
                    st.metric("Panelist Score", f"{total_panelist_score}/100")
                    
                    # Submit button
                    if st.button(f"💾 Submit {panelist_name}'s Scores", use_container_width=True, type="primary"):
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO panelist_scores (
                                candidate_id, panelist_id, academic_score, hr_knowledge_score,
                                procurement_score, gov_structure_score, leadership_score,
                                communication_score, general_knowledge_score, technical_score,
                                total_score, timestamp
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            selected_candidate, selected_panelist,
                            scores['academic'], scores['hr_knowledge'],
                            scores['procurement'], scores['gov_structure'],
                            scores['leadership'], scores['communication'],
                            scores['general_knowledge'], scores['technical'],
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
                    st.write(f"- {p[1]} ({p[2]}): Score = {p[3]}/100")
            else:
                st.warning("No panelists available. Please add panelists in the database.")
    
    # ==================== TAB 3: PANELIST SUMMARY ====================
    with tab3:
        st.subheader("📊 Panelist Scores Summary")
        
        if 'selected_candidate' not in dir():
            st.warning("Please select a candidate in the 'Select Candidate' tab first.")
        else:
            # Get all scores for this candidate
            scores_df = pd.read_sql(f"""
                SELECT p.name as panelist_name, p.role,
                       ps.academic_score, ps.hr_knowledge_score, ps.procurement_score,
                       ps.gov_structure_score, ps.leadership_score, ps.communication_score,
                       ps.general_knowledge_score, ps.technical_score, ps.total_score,
                       ps.timestamp
                FROM panelist_scores ps
                JOIN panelists p ON ps.panelist_id = p.id
                WHERE ps.candidate_id = {selected_candidate}
                ORDER BY ps.total_score DESC
            """, conn)
            
            if scores_df.empty:
                st.info("No scores have been submitted yet. Please go to 'Panelist Scoring' tab to submit scores.")
            else:
                # Display individual panelist scores
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
                
                # Calculate overall candidate score (mean of all panelist totals)
                st.markdown("---")
                st.subheader("🎯 Overall Candidate Score")
                
                panelist_scores_list = scores_df['total_score'].tolist()
                overall_score = sum(panelist_scores_list) / len(panelist_scores_list)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Number of Panelists", len(panelist_scores_list))
                with col2:
                    st.metric("Highest Panelist Score", max(panelist_scores_list))
                with col3:
                    st.metric("Lowest Panelist Score", min(panelist_scores_list))
                
                # Display overall score prominently
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0f2b42 100%); 
                            padding: 2rem; border-radius: 12px; text-align: center; margin: 1rem 0;">
                    <h2 style="color: white; margin: 0;">Overall Candidate Score</h2>
                    <h1 style="color: white; font-size: 4rem; margin: 0;">{overall_score:.1f}</h1>
                    <p style="color: rgba(255,255,255,0.8);">out of 100</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Update the staff table with the overall score
                c = conn.cursor()
                c.execute("UPDATE staff SET interview_score = ? WHERE id = ?", (overall_score, selected_candidate))
                conn.commit()
                
                # Show distribution chart
                st.subheader("📊 Score Distribution by Panelist")
                fig = px.bar(
                    scores_df,
                    x='panelist_name',
                    y='total_score',
                    title="Panelist Scores Distribution",
                    labels={'total_score': 'Score', 'panelist_name': 'Panelist'},
                    color='total_score',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Export option
                csv = scores_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Panelist Scores",
                    csv,
                    f"panelist_scores_{selected_candidate}.csv",
                    "text/csv"
                )
    
    # ==================== TAB 4: FINAL RANKINGS ====================
    with tab4:
        st.subheader("🏆 Final Candidate Rankings")
        
        # Get all scored candidates with their overall scores
        ranked_df = pd.read_sql("""
            SELECT id, name, id_number, position_applied, interview_score, created_at
            FROM staff 
            WHERE application_status = 'Shortlisted' 
            AND interview_score IS NOT NULL 
            AND interview_score > 0
            ORDER BY interview_score DESC
        """, conn)
        
        if ranked_df.empty:
            st.info("No candidates have been fully scored yet. Please complete scoring in the tabs above.")
        else:
            # Add rank
            ranked_df['Rank'] = ranked_df['interview_score'].rank(method='min', ascending=False).astype(int)
            
            # Display ranking table
            st.dataframe(
                ranked_df[['Rank', 'name', 'id_number', 'position_applied', 'interview_score']],
                use_container_width=True
            )
            
            # Top 3 highlights
            st.markdown("### 🏅 Top 3 Candidates")
            
            top3 = ranked_df.head(3)
            col1, col2, col3 = st.columns(3)
            
            for idx, (_, row) in enumerate(top3.iterrows()):
                with [col1, col2, col3][idx]:
                    st.markdown(f"""
                    <div style="background: white; padding: 1rem; border-radius: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <h1 style="font-size: 3rem; margin: 0;">{'🥇' if idx==0 else '🥈' if idx==1 else '🥉'}</h1>
                        <h3>{row['name']}</h3>
                        <p>Score: <b>{row['interview_score']:.1f}/100</b></p>
                        <p style="font-size: 0.8rem;">{row['position_applied']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Export rankings
            csv = ranked_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Final Rankings (CSV)",
                csv,
                f"final_rankings_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
    
    conn.close()
# =========================================================
# CREATE MISSING TABLES FOR SCORESHEET
# =========================================================
def create_scoresheet_tables():
    """Create all tables needed for the scoresheet module"""
    conn = get_conn()
    c = conn.cursor()
    
    # Create panelists table
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
            ("Board Member 1", "Board Member", 1, 1),
            ("Board Member 2", "Board Member", 1, 2),
            ("Board Member 3", "Board Member", 1, 3),
            ("Board Member 4", "Board Member", 1, 4),
            ("Board Member 5", "Board Member", 1, 5),
            ("Board Member 6", "Board Member", 1, 6),
            ("Board Member 7", "Board Member", 1, 7),
            ("Technical Officer", "Technical Officer", 1, 8)
        ]
        c.executemany("""
            INSERT INTO panelists (name, role, is_active, display_order, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, [(name, role, active, order, datetime.now().strftime("%Y-%m-%d %H:%M:%S")) 
              for name, role, active, order in default_panelists])
    
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
        c.executemany("""
            INSERT INTO scoring_criteria (criteria_key, criteria_name, max_score, description, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, default_criteria)
    
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
        c.executemany("""
            INSERT INTO scoring_parameters (param_key, param_name, param_value, description)
            VALUES (?, ?, ?, ?)
        """, default_params)
    
    conn.commit()
    conn.close()
    print("✅ Scoresheet tables created successfully!")
# =========================================================
# MAIN APPLICATION
# =========================================================
def main():
    apply_theme()
    
    # System initialization
    init_db()
    create_settings_tables()
    create_scoresheet_tables()      
    migrate_database()
    ensure_database_columns()        
    create_default_admin()

    if "user" not in st.session_state or st.session_state.user is None:
        login()
        return
    
    # Get menu from sidebar (may return None if hidden)
    menu = sidebar()
    
    # If sidebar is hidden, still need to handle navigation
    # Store selected menu in session state to persist
    if menu is None:
        # Use previously selected menu or default to Dashboard
        if 'selected_menu' not in st.session_state:
            st.session_state.selected_menu = "📊 Dashboard"
        menu = st.session_state.selected_menu
    else:
        # Update session state with current selection
        st.session_state.selected_menu = menu
    
    # Router - All navigation options
    if menu == "📊 Dashboard":
        dashboard()
    elif menu == "👥 Staff Profile":
        staff_profile()
    elif menu == "📝 Applicant Registration":
        data_entry()
    elif menu == "✏️ Edit Application":
        edit_applicant()
    elif menu == "⭐ Shortlist Management":
        shortlist_management()
    elif menu == "📊 Position Dashboard":
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
    elif menu == "📊 Scoresheet":
        scoresheet_module()
    elif menu == "🧪 Test Data":
        generate_test_data()
    elif menu == "⚙️ Settings":
        system_settings()
    elif menu == "👤 Users":
        users()
    else:
        dashboard()


# =========================================================
# RUN APPLICATION
# =========================================================
if __name__ == "__main__":
    main()
