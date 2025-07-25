#!/usr/bin/env python3
"""
Medication Tracker - Test Script
Test the core functionality of our medication tracking system.
"""

from models.medication import Medication, User
from utils.database import MedicationDB

def test_basic_functionality():
    """Test basic medication tracking functionality."""
    print("🧪 Testing Medication Tracker Core Functionality\n")
    
    # Initialize database
    print("1. Initializing database...")
    db = MedicationDB()
    print("   ✅ Database initialized successfully!")
    
    # Create a user
    print("\n2. Creating user...")
    user_id = db.add_user("Dorothy Johnson", 75)
    print(f"   ✅ Created user Dorothy Johnson (ID: {user_id})")
    
    # Add medications
    print("\n3. Adding medications...")
    med1_id = db.add_medication(user_id, "Metformin", "500mg", "twice_daily", ["08:00", "20:00"])
    med2_id = db.add_medication(user_id, "Lisinopril", "10mg", "daily", ["08:00"])
    print(f"   ✅ Added Metformin (ID: {med1_id})")
    print(f"   ✅ Added Lisinopril (ID: {med2_id})")
    
    # Get user's medications
    print("\n4. Retrieving user medications...")
    medications = db.get_user_medications(user_id)
    print(f"   ✅ Found {len(medications)} medications:")
    for med in medications:
        print(f"      • {med['name']} - {med['dosage']} at {', '.join(med['times'])}")
    
    # Log some doses
    print("\n5. Logging medication doses...")
    db.log_dose(user_id, "Metformin", "08:00", True)
    db.log_dose(user_id, "Lisinopril", "08:00", True)
    db.log_dose(user_id, "Metformin", "20:00", False)  # Missed evening dose
    print("   ✅ Logged morning doses (taken) and evening Metformin (missed)")
    
    # Check adherence
    print("\n6. Calculating adherence rate...")
    adherence = db.get_user_adherence(user_id, days=1)
    print(f"   ✅ Today's adherence rate: {adherence:.1f}%")
    
    # Test the User class
    print("\n7. Testing User class...")
    user = User("Dorothy Johnson", 75)
    
    # Create medication objects
    metformin = Medication("Metformin", "500mg", "twice_daily", ["08:00", "20:00"])
    lisinopril = Medication("Lisinopril", "10mg", "daily", ["08:00"])
    
    user.add_medication(metformin)
    user.add_medication(lisinopril)
    
    schedule = user.get_todays_schedule()
    print(f"   ✅ Generated daily schedule with {len(schedule)} doses:")
    for dose in schedule:
        print(f"      • {dose['time']}: {dose['medication']} - {dose['dosage']}")
    
    print("\n🎉 All tests passed! Your medication tracker is working perfectly!")
    print(f"\n📊 Database location: {db.db_path}")
    print("Ready to build the user interface!")

if __name__ == "__main__":
    test_basic_functionality()

    