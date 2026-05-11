#!/usr/bin/env python3
"""
Standalone Test Data Generator for Embu County Public Service Board
Run this script separately to populate test data
Usage: python generate_test_data.py
"""

import sqlite3
import random
from datetime import datetime
import os

# Configuration
DB_NAME = "ecde.db"  # Change to your database file

# Sample data pools
FIRST_NAMES = ["John", "Mary", "Peter", "Jane", "James", "Ann", "David", "Sarah", "Michael", "Grace",
               "Joseph", "Esther", "Benjamin", "Ruth", "Samuel", "Deborah", "Daniel", "Hannah", "Paul", "Judith",
               "Kennedy", "Lucy", "Robert", "Faith", "William", "Irene", "Charles", "Beatrice", "Stephen", "Catherine"]

LAST_NAMES = ["Kamau", "Wanjiku", "Otieno", "Muthoni", "Ochieng", "Njeri", "Kipchoge", "Akinyi", "Mwangi", "Chebet",
              "Kariuki", "Atieno", "Maina", "Achieng", "Omondi", "Wambui", "Kibet", "Nyambura", "Ndegwa", "Wanjiru",
              "Kimani", "Nyambura", "Wachira", "Wairimu", "Muriithi", "Wanjala", "Kiprono", "Mideva", "Odhiambo", "Okoth"]

SUBCOUNTIES = ["Central", "East", "North", "South", "West", "Manyatta", "Runyenjes", "Mbeere North", "Mbeere South", "Siakago"]
WARDS = ["Kithimu", "Kagaari", "Nginda", "Mufu", "Kiambere", "Gachoka", "Mavuria", "Kiritiri", "Evurore", "Mbita"]

POSITIONS = [
    "ECDE Teacher - Permanent",
    "ECDE Teacher - Contract", 
    "ECDE Trainer",
    "ECDE Supervisor",
    "ECDE Coordinator",
    "ECDE Curriculum Developer",
    "ECDE Administrator",
    "Intern ECDE Teacher"
]

QUALIFICATIONS = ["ECDE Certificate", "ECDE Diploma", "Bachelor's Degree in ECDE", "Bachelor's Degree in Education"]
STATUSES = ["Pending", "Shortlisted", "Interviewed", "Recommended", "Hired", "Rejected"]
DEPARTMENTS = ["Administration", "Finance", "Human Resource", "ICT", "Health", "Education", "Public Works", "Agriculture"]
DESIGNATIONS = ["ECDE Teacher", "Senior ECDE Teacher", "ECDE Trainer", "ECDE Supervisor", "ECDE Coordinator", "ECDE Administrator"]
JOB_GROUPS = ["JG 'H'", "JG 'J'", "JG 'K'", "JG 'L'", "JG 'M'", "JG 'N'"]

def get_conn():
    """Get database connection"""
    return sqlite3.connect(DB_NAME)

def init_tables():
    """Ensure tables exist before inserting data"""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Create staff table
    cursor.execute("""
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
    
    # Create employees table for HR
    cursor.execute("""
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
    
    # Create users table if needed
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        created_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Tables verified/created")

def generate_applicants(num_records=50):
    """Generate applicant records"""
    conn = get_conn()
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    
    print(f"\n📝 Generating {num_records} applicant records...")
    
    for i in range(num_records):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        gender = "Male" if random.random() > 0.5 else "Female"
        id_number = f"{random.randint(10000000, 99999999)}"
        
        # Check if ID already exists
        cursor.execute("SELECT id_number FROM staff WHERE id_number = ?", (id_number,))
        if cursor.fetchone():
            skipped += 1
            continue
        
        yob = random.randint(1970, 2000)
        ethnicity = random.choice(["Kikuyu", "Luo", "Luhya", "Kalenjin", "Kamba", "Kisii", "Meru", "Embu"])
        disability = "None" if random.random() > 0.1 else "Physical Disability"
        contact = f"07{random.randint(10000000, 99999999)}"
        kcse = str(random.randint(2000, 2015))
        qualifications = random.choice(QUALIFICATIONS)
        subcounty = random.choice(SUBCOUNTIES)
        ward = random.choice(WARDS)
        experience = f"{random.randint(1, 20)} years of experience"
        position = random.choice(POSITIONS)
        status = random.choice(STATUSES) if random.random() > 0.3 else "Pending"
        email = f"{name.lower().replace(' ', '.')}@example.com"
        kcse_grade = random.choice(["A", "A-", "B+", "B", "B-", "C+", "C"])
        institution = random.choice(["Kenyatta University", "Moi University", "Mount Kenya University", "University of Nairobi"])
        graduation_year = random.randint(2010, 2023)
        experience_years = random.randint(1, 25)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        application_date = f"{random.randint(2023, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        
        try:
            cursor.execute("""
                INSERT INTO staff (
                    sno, name, gender, id_number, yob, ethnicity, disability, contact, kcse,
                    qualifications, subcounty, ward, experience, position_applied, application_status,
                    email, kcse_grade, institution, graduation_year, experience_years,
                    created_at, created_by, application_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i + 1, name, gender, id_number, yob, ethnicity, disability, contact, kcse,
                qualifications, subcounty, ward, experience, position, status,
                email, kcse_grade, institution, graduation_year, experience_years,
                created_at, "system", application_date
            ))
            inserted += 1
            
            if inserted % 10 == 0:
                print(f"   ... {inserted} records inserted")
                
        except Exception as e:
            print(f"   Error: {e}")
            skipped += 1
    
    conn.commit()
    conn.close()
    print(f"✅ Applicants: {inserted} inserted, {skipped} skipped")

def generate_employees(num_records=20):
    """Generate employee records for HR"""
    conn = get_conn()
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    
    print(f"\n👔 Generating {num_records} employee records...")
    
    for i in range(num_records):
        staff_no = f"ECPSB/2024/{1000 + i:04d}"
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        personal_no = f"{random.randint(10000000, 99999999)}"
        age = random.randint(25, 60)
        department = random.choice(DEPARTMENTS)
        designation = random.choice(DESIGNATIONS)
        job_group = random.choice(JOB_GROUPS)
        appointment_date = f"{random.randint(2010, 2023)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute("""
                INSERT INTO employees (
                    staff_no, name, personal_no, age, department, first_appointment_date,
                    current_designation, current_job_group, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (staff_no, name, personal_no, age, department, appointment_date,
                  designation, job_group, created_at, "system"))
            inserted += 1
        except Exception as e:
            print(f"   Error: {e}")
            skipped += 1
    
    conn.commit()
    conn.close()
    print(f"✅ Employees: {inserted} inserted, {skipped} skipped")

def generate_admin_user():
    """Generate admin user if not exists"""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (username, password, role, created_at)
            VALUES (?, ?, ?, ?)
        """, ("admin", "admin123", "Admin", created_at))
        conn.commit()
        print("✅ Admin user created (username: admin, password: admin123)")
    else:
        print("ℹ️ Admin user already exists")
    
    conn.close()

def show_summary():
    """Show database summary"""
    conn = get_conn()
    cursor = conn.cursor()
    
    print("\n" + "="*50)
    print("📊 DATABASE SUMMARY")
    print("="*50)
    
    cursor.execute("SELECT COUNT(*) FROM staff")
    staff_count = cursor.fetchone()[0]
    print(f"   Staff/Applicants: {staff_count}")
    
    cursor.execute("SELECT COUNT(*) FROM employees")
    employees_count = cursor.fetchone()[0] if cursor.execute("SELECT COUNT(*) FROM employees") else 0
    print(f"   HR Employees: {employees_count}")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    print(f"   Users: {users_count}")
    
    conn.close()

def main():
    print("="*50)
    print("🏛️ EMBU COUNTY PUBLIC SERVICE BOARD")
    print("   Test Data Generator")
    print("="*50)
    
    # Check if database exists
    if not os.path.exists(DB_NAME):
        print(f"⚠️ Database '{DB_NAME}' not found. It will be created.")
    
    # Initialize tables
    init_tables()
    
    # Ask for number of records
    print("\nHow many test records do you want to generate?")
    print("1. 10 records (quick test)")
    print("2. 25 records")
    print("3. 50 records")
    print("4. 100 records")
    print("5. Custom number")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        num = 10
    elif choice == "2":
        num = 25
    elif choice == "3":
        num = 50
    elif choice == "4":
        num = 100
    elif choice == "5":
        num = int(input("Enter number of records: "))
    else:
        num = 20
    
    # Generate data
    generate_applicants(num)
    generate_employees(max(10, num // 2))
    generate_admin_user()
    show_summary()
    
    print("\n✅ Test data generation complete!")
    print(f"📁 Database location: {os.path.abspath(DB_NAME)}")

if __name__ == "__main__":
    main()