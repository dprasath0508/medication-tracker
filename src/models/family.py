from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class FamilyMember:
    """Represents a family member in a family circle."""
    id: int
    name: str
    email: str
    role: str  # 'patient' or 'family_member'
    relationship: str  # 'patient', 'child', 'spouse', 'caregiver'
    permissions: List[str]  # ['view', 'manage_meds', 'set_reminders']
    joined_date: datetime
    
    def can_manage_medications(self) -> bool:
        """Check if this family member can manage medications."""
        return 'manage_meds' in self.permissions
    
    def can_set_reminders(self) -> bool:
        """Check if this family member can set reminders."""
        return 'set_reminders' in self.permissions

@dataclass 
class FamilyCircle:
    """Represents a family circle for medication management."""
    id: int
    name: str
    invite_code: str
    created_by: int
    created_date: datetime
    members: List[FamilyMember]
    
    def get_patients(self) -> List[FamilyMember]:
        """Get all patients (elderly people) in this family circle."""
        return [member for member in self.members if member.role == 'patient']
    
    def get_caregivers(self) -> List[FamilyMember]:
        """Get all family members who can provide care."""
        return [member for member in self.members if member.role == 'family_member']
    
    def get_member_by_id(self, user_id: int) -> FamilyMember:
        """Get a specific member by their user ID."""
        for member in self.members:
            if member.id == user_id:
                return member
        return None

class FamilyCircleManager:
    """Manages family circle operations."""
    
    def __init__(self, db):
        self.db = db
    
    def create_family_circle(self, name: str, creator_id: int) -> tuple[int, str]:
        """Create a new family circle."""
        return self.db.create_family_circle(name, creator_id)
    
    def join_family_circle(self, invite_code: str, user_id: int, relationship: str = 'family_member') -> bool:
        """Join an existing family circle."""
        return self.db.join_family_circle(invite_code, user_id, relationship)
    
    def get_family_dashboard_data(self, family_member_id: int) -> Dict[str, Any]:
        """Get comprehensive dashboard data for a family member."""
        # Get all patients this family member can monitor
        patients_status = self.db.get_family_patients_status(family_member_id)
        
        # Get family member's circles
        circles = self.db.get_user_family_circles(family_member_id)
        
        # Calculate summary statistics
        total_patients = len(patients_status)
        avg_adherence = sum(p['adherence_rate'] for p in patients_status) / len(patients_status) if patients_status else 0
        
        # Find patients needing attention (low adherence)
        patients_needing_attention = [p for p in patients_status if p['adherence_rate'] < 80]
        
        return {
            'total_patients': total_patients,
            'average_adherence': round(avg_adherence, 1),
            'patients_needing_attention': len(patients_needing_attention),
            'family_circles': circles,
            'patients_status': patients_status,
            'alerts': self._generate_alerts(patients_status)
        }
    
    def _generate_alerts(self, patients_status: List[Dict]) -> List[str]:
        """Generate alerts for family dashboard."""
        alerts = []
        
        for patient in patients_status:
            if patient['adherence_rate'] < 70:
                alerts.append(f"⚠️ {patient['name']} has low medication adherence ({patient['adherence_rate']:.1f}%)")
            elif patient['adherence_rate'] < 90:
                alerts.append(f"⚡ {patient['name']} could use some encouragement ({patient['adherence_rate']:.1f}% adherence)")
        
        return alerts
    
    def add_medication_for_patient(self, family_member_id: int, patient_id: int, medication_data: Dict[str, Any]) -> int:
        """Family member adds medication for a patient."""
        return self.db.add_medication(
            patient_id=patient_id,
            managed_by=family_member_id,
            name=medication_data['name'],
            dosage=medication_data['dosage'],
            frequency=medication_data['frequency'],
            times=medication_data['times'],
            notes=medication_data.get('notes', '')
        )