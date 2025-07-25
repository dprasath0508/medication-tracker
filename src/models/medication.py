from datetime import datetime, time
from typing import List

class Medication:
    """Represents a medication with dosage schedule."""
    
    def __init__(self, name: str, dosage: str, frequency: str, times: List[str]):
        self.name = name
        self.dosage = dosage  # "10mg", "500mg", etc.
        self.frequency = frequency  # "daily", "twice_daily", "three_times_daily"
        self.times = times  # ["08:00", "20:00"]
        self.created_date = datetime.now()
        self.active = True
    
    def __str__(self):
        return f"{self.name} - {self.dosage} at {', '.join(self.times)}"
    
    def get_daily_schedule(self):
        """Returns today's schedule for this medication."""
        schedule = []
        for time_str in self.times:
            schedule.append({
                'medication': self.name,
                'dosage': self.dosage,
                'time': time_str,
                'taken': False
            })
        return schedule

class DoseLog:
    """Records when medications are taken."""
    
    def __init__(self, medication_name: str, scheduled_time: str, taken: bool, actual_time: str = None):
        self.medication_name = medication_name
        self.scheduled_time = scheduled_time
        self.taken = taken
        self.actual_time = actual_time or datetime.now().strftime("%H:%M")
        self.date = datetime.now().date()
        self.timestamp = datetime.now()
    
    def __str__(self):
        status = "✅ Taken" if self.taken else "❌ Missed"
        return f"{self.medication_name} at {self.scheduled_time}: {status}"

class User:
    """Represents a user (elderly person) with their medications."""
    
    def __init__(self, name: str, age: int = None):
        self.name = name
        self.age = age
        self.medications = []
        self.dose_logs = []
        self.created_date = datetime.now()
    
    def add_medication(self, medication: Medication):
        """Add a new medication to user's list."""
        self.medications.append(medication)
    
    def get_todays_schedule(self):
        """Get all medications scheduled for today."""
        schedule = []
        for med in self.medications:
            if med.active:
                schedule.extend(med.get_daily_schedule())
        
        # Sort by time
        schedule.sort(key=lambda x: x['time'])
        return schedule
    
    def log_dose(self, medication_name: str, scheduled_time: str, taken: bool):
        """Log whether a dose was taken."""
        dose_log = DoseLog(medication_name, scheduled_time, taken)
        self.dose_logs.append(dose_log)
        return dose_log
    
    def get_adherence_rate(self, days: int = 7):
        """Calculate medication adherence rate for last X days."""
        if not self.dose_logs:
            return 0.0
        
        recent_logs = [log for log in self.dose_logs 
                      if (datetime.now().date() - log.date).days <= days]
        
        if not recent_logs:
            return 0.0
        
        taken_count = sum(1 for log in recent_logs if log.taken)
        return (taken_count / len(recent_logs)) * 100
    
    