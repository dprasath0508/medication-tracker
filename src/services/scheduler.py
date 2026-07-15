from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import logging
from typing import Dict, List
import json

from services.notifications import NotificationService
from utils.authz import SYSTEM_CALLER
from utils.database import MedicationDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicationScheduler:
    """Background scheduler for automated medication reminders."""
    
    def __init__(self, db: MedicationDB):
        self.db = db
        self.notification_service = NotificationService()
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("Medication Scheduler initialized")
    
    def schedule_all_medications(self):
        """Schedule reminders for all active medications."""
        users = self.db.get_users()
        
        for user in users:
            if user['role'] == 'patient':
                # Background service: reads as the explicit (read-only) system
                # identity — see utils/authz.py.
                medications = self.db.get_patient_medications(SYSTEM_CALLER, user['id'])

                for medication in medications:
                    self.schedule_medication_reminders(user, medication)
        
        logger.info("All medication reminders scheduled")
    
    def schedule_medication_reminders(self, user: Dict, medication: Dict):
        """Schedule reminders for a specific medication."""
        med_times = medication['times']
        
        # Get user preferences (default to both email and SMS)
        reminder_method = user.get('reminder_preference', 'both')
        
        for med_time in med_times:
            # Parse time (format: "HH:MM")
            hour, minute = med_time.split(':')
            
            # Create job ID
            job_id = f"med_{user['id']}_{medication['id']}_{med_time.replace(':', '')}"
            
            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Schedule daily reminder at specified time
            self.scheduler.add_job(
                func=self._send_reminder,
                trigger=CronTrigger(hour=int(hour), minute=int(minute)),
                args=[user, medication, reminder_method],
                id=job_id,
                name=f"Reminder: {medication['name']} for {user['name']}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled reminder for {user['name']}: {medication['name']} at {med_time}")
    
    def _send_reminder(self, user: Dict, medication: Dict, reminder_method: str):
        """Send reminder notification (called by scheduler)."""
        try:
            success = self.notification_service.send_medication_reminder(
                user, medication, reminder_method
            )
            
            if success:
                logger.info(f"Reminder sent to {user['name']} for {medication['name']}")
            else:
                logger.warning(f"Failed to send reminder to {user['name']}")
        
        except Exception as e:
            logger.error(f"Error sending reminder: {str(e)}")
    
    def schedule_weekly_reports(self):
        """Schedule weekly compliance reports (every Sunday at 6 PM)."""
        self.scheduler.add_job(
            func=self._generate_and_send_weekly_reports,
            trigger=CronTrigger(day_of_week='sun', hour=18, minute=0),
            id='weekly_reports',
            name='Weekly Compliance Reports',
            replace_existing=True
        )
        logger.info("Weekly reports scheduled for Sundays at 6 PM")
    
    def _generate_and_send_weekly_reports(self):
        """Generate and send weekly reports to all users."""
        users = self.db.get_users()
        
        for user in users:
            if user['role'] == 'patient':
                try:
                    # Get adherence data for past week
                    adherence_data = self._calculate_weekly_adherence(user['id'])
                    
                    # Get family member emails
                    family_emails = self._get_family_emails(user['id'])
                    
                    # Send report
                    self.notification_service.send_weekly_report(
                        user, adherence_data, family_emails
                    )
                    
                    logger.info(f"Weekly report sent for {user['name']}")
                
                except Exception as e:
                    logger.error(f"Error generating report for {user['name']}: {str(e)}")
    
    def _calculate_weekly_adherence(self, patient_id: int) -> Dict:
        """Calculate adherence data for the past week."""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        # Per-day dose counts via the data layer (previously raw SQL here)
        rows = self.db.get_daily_dose_counts(SYSTEM_CALLER, patient_id, days=7)
        by_date = {row['date']: row for row in rows}

        # Calculate statistics
        total_doses = sum(row['total'] for row in rows)
        taken_doses = sum(row['taken'] for row in rows)
        missed_doses = total_doses - taken_doses
        adherence_rate = (taken_doses / total_doses * 100) if total_doses > 0 else 0

        # Daily breakdown
        daily_data = []
        for i in range(7):
            day = end_date - timedelta(days=i)
            row = by_date.get(day.isoformat())
            day_taken = row['taken'] if row else 0
            day_total = row['total'] if row else 0
            day_rate = (day_taken / day_total * 100) if day_total > 0 else 0

            daily_data.append({
                'date': day.strftime('%A, %b %d'),
                'taken': day_taken,
                'missed': day_total - day_taken,
                'adherence_rate': day_rate
            })
        
        return {
            'adherence_rate': adherence_rate,
            'total_doses': total_doses,
            'taken_doses': taken_doses,
            'missed_doses': missed_doses,
            'week_start': start_date.strftime('%B %d, %Y'),
            'week_end': end_date.strftime('%B %d, %Y'),
            'daily_data': daily_data
        }
    
    def _get_family_emails(self, patient_id: int) -> List[str]:
        """Get email addresses of family members monitoring this patient."""
        # Get family circles the patient belongs to
        circles = self.db.get_user_family_circles(patient_id)
        
        family_emails = []
        for circle in circles:
            members = self.db.get_family_circle_members(circle['id'])
            for member in members:
                if member['role'] == 'family_member' and member['email']:
                    family_emails.append(member['email'])
        
        return list(set(family_emails))  # Remove duplicates
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Medication Scheduler stopped")