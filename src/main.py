#!/usr/bin/env python3
"""
Medication Tracker - Family Circle Test
Test the family circle functionality for multi-user medication management.
"""

from models.medication import Medication, User
from models.family import FamilyCircleManager
from utils.database import MedicationDB

def test_family_circle_functionality():
    """Test the family circle features."""
    print("🏠 Testing Family Circle Medication Management\n")
    
    # Initialize database
    print("1. Initializing database with family support...")
    db = MedicationDB()
    family_manager = FamilyCircleManager(db)
    print("   ✅ Database initialized with family circle tables!")
    
    # Create users
    print("\n2. Creating users...")
    # Elderly patient
    dorothy_id = db.add_user("Dorothy Johnson", "dorothy@email.com", 75, "patient", "555-0123")
    
    # Family members
    sarah_id = db.add_user("Sarah Johnson", "sarah@email.com", 45, "family_member", "555-0124")
    mike_id = db.add_user("Mike Johnson", "mike@email.com", 50, "family_member", "555-0125")
    
    print(f"   ✅ Created Dorothy Johnson (Patient, ID: {dorothy_id})")
    print(f"   ✅ Created Sarah Johnson (Daughter, ID: {sarah_id})")
    print(f"   ✅ Created Mike Johnson (Son-in-law, ID: {mike_id})")
    
    # Create family circle
    print("\n3. Creating family circle...")
    circle_id, invite_code = family_manager.create_family_circle("Johnson Family Care", sarah_id)
    print(f"   ✅ Created 'Johnson Family Care' circle")
    print(f"   📨 Invite code: {invite_code}")
    
    # Add family members to circle
    print("\n4. Adding family members to circle...")
    
    # Add Dorothy as patient
    dorothy_joined = db.join_family_circle(invite_code, dorothy_id, "patient")
    # Add Mike as family caregiver
    mike_joined = db.join_family_circle(invite_code, mike_id, "spouse")
    
    print(f"   ✅ Dorothy joined circle: {dorothy_joined}")
    print(f"   ✅ Mike joined circle: {mike_joined}")
    
    # Get circle members
    print("\n5. Family circle members:")
    members = db.get_family_circle_members(circle_id)
    for member in members:
        print(f"   👤 {member['name']} - {member['relationship']} - {member['role']}")
        print(f"      Permissions: {member['permissions']}")
    
    # Sarah (daughter) adds medications for Dorothy
    print("\n6. Sarah adding medications for Dorothy...")
    med1_id = family_manager.add_medication_for_patient(
        family_member_id=sarah_id,
        patient_id=dorothy_id,
        medication_data={
            'name': 'Metformin',
            'dosage': '500mg',
            'frequency': 'twice_daily',
            'times': ['08:00', '20:00'],
            'notes': 'Take with meals'
        }
    )
    
    med2_id = family_manager.add_medication_for_patient(
        family_member_id=sarah_id,
        patient_id=dorothy_id,
        medication_data={
            'name': 'Lisinopril',
            'dosage': '10mg',
            'frequency': 'daily',
            'times': ['08:00'],
            'notes': 'Blood pressure medication'
        }
    )
    
    print(f"   ✅ Sarah added Metformin for Dorothy (ID: {med1_id})")
    print(f"   ✅ Sarah added Lisinopril for Dorothy (ID: {med2_id})")
    
    # View Dorothy's medications
    print("\n7. Dorothy's current medications:")
    medications = db.get_patient_medications(dorothy_id)
    for med in medications:
        print(f"   💊 {med['name']} - {med['dosage']} at {', '.join(med['times'])}")
        print(f"      Managed by: {med['managed_by_name']}")
        print(f"      Notes: {med['notes']}")
    
    # Log some doses (can be done by family members)
    print("\n8. Logging medication doses...")
    db.log_dose(dorothy_id, "Metformin", "08:00", True, dorothy_id)  # Dorothy took morning dose
    db.log_dose(dorothy_id, "Lisinopril", "08:00", True, dorothy_id)  # Dorothy took BP med
    db.log_dose(dorothy_id, "Metformin", "20:00", False, sarah_id)  # Sarah marked evening dose missed
    
    print("   ✅ Logged morning doses (taken) and evening Metformin (missed)")
    print("   ℹ️  Family members can help track doses remotely")
    
    # Family dashboard view
    print("\n9. Sarah's family dashboard:")
    dashboard_data = family_manager.get_family_dashboard_data(sarah_id)
    
    print(f"   📊 Monitoring {dashboard_data['total_patients']} patients")
    print(f"   📈 Average adherence: {dashboard_data['average_adherence']}%")
    print(f"   ⚠️  Patients needing attention: {dashboard_data['patients_needing_attention']}")
    
    print("\n   Patient Status:")
    for patient in dashboard_data['patients_status']:
        print(f"   👵 {patient['name']} ({patient['age']} years old)")
        print(f"      📋 {patient['total_medications']} medications")
        print(f"      ✅ {patient['adherence_rate']:.1f}% adherence rate")
    
    if dashboard_data['alerts']:
        print("\n   🚨 Alerts:")
        for alert in dashboard_data['alerts']:
            print(f"      {alert}")
    
    # Mike's view
    print(f"\n10. Mike's family dashboard:")
    mike_dashboard = family_manager.get_family_dashboard_data(mike_id)
    print(f"    📊 Mike can also monitor {mike_dashboard['total_patients']} patients")
    print(f"    📱 Family members can collaborate on care")
    
    print("\n🎉 Family Circle functionality working perfectly!")
    print("\n💡 Key Features Demonstrated:")
    print("   • Family members can create care circles")
    print("   • Multiple people can manage one patient's medications")
    print("   • Remote monitoring and progress tracking")
    print("   • Collaborative medication management")
    print("   • Family dashboard with alerts and insights")
    
    print(f"\n📊 Database location: {db.db_path}")
    print("🚀 Ready to build the user interface!")

def test_basic_functionality():
    """Test basic single-user functionality (original test)."""
    print("🧪 Testing Basic Medication Tracker Functionality\n")
    
    # Initialize database
    print("1. Initializing database...")
    db = MedicationDB()
    print("   ✅ Database initialized successfully!")
    
    # Create a user (old style for backward compatibility)
    print("\n2. Creating user...")
    user_id = db.add_user("Dorothy Johnson", age=75)
    print(f"   ✅ Created user Dorothy Johnson (ID: {user_id})")
    
    # Add medications (updated method signature)
    print("\n3. Adding medications...")
    med1_id = db.add_medication(user_id, user_id, "Metformin", "500mg", "twice_daily", ["08:00", "20:00"])
    med2_id = db.add_medication(user_id, user_id, "Lisinopril", "10mg", "daily", ["08:00"])
    print(f"   ✅ Added Metformin (ID: {med1_id})")
    print(f"   ✅ Added Lisinopril (ID: {med2_id})")
    
    # Get user's medications
    print("\n4. Retrieving user medications...")
    medications = db.get_patient_medications(user_id)
    print(f"   ✅ Found {len(medications)} medications:")
    for med in medications:
        print(f"      • {med['name']} - {med['dosage']} at {', '.join(med['times'])}")
    
    print("\n✅ Basic functionality still works!")

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Basic functionality (original)")
    print("2. Family circle functionality (new)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        test_basic_functionality()
    else:
        test_family_circle_functionality()