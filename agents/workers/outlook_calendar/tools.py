from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import sys
import os

# Add the parent directory to path to import the outlook integration
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from outlook_integration import OutlookIntegration

# Hardcoded email mapping for demo purposes
EMAIL_MAP = {
    "yash": "ysgupta@wisc.edu",
    "nikhil": "nst@wisc.edu",
}

def _resolve_email_addresses(name_or_emails: Optional[List[str]]) -> Optional[List[str]]:
    """Resolves names to email addresses using the hardcoded map."""
    if not name_or_emails:
        return None
    
    resolved_emails = []
    for item in name_or_emails:
        # Check if the item is a name in our map (case-insensitive)
        resolved_email = EMAIL_MAP.get(item.lower())
        if resolved_email:
            resolved_emails.append(resolved_email)
        else:
            # Assume it's already a valid email address
            resolved_emails.append(item)
    return resolved_emails

# Schema for sending emails
class SendEmailSchema(BaseModel):
    to: List[str] = Field(description="List of email addresses to send the email to.")
    subject: str = Field(description="The subject line of the email.")
    body: str = Field(description="The content/body of the email.")
    cc: Optional[List[str]] = Field(default=None, description="List of email addresses to CC.")
    bcc: Optional[List[str]] = Field(default=None, description="List of email addresses to BCC.")

# Schema for scheduling meetings
class ScheduleMeetingSchema(BaseModel):
    subject: str = Field(description="The subject/title of the meeting.")
    start_time: str = Field(description="Start time in ISO format (YYYY-MM-DDTHH:MM:SS) or relative time like 'in 2 hours'.")
    duration_minutes: int = Field(default=60, description="Duration of the meeting in minutes.")
    attendees: Optional[List[str]] = Field(default=None, description="List of email addresses to invite to the meeting.")
    description: str = Field(default="", description="Description or agenda for the meeting.")

@tool(args_schema=SendEmailSchema)
def send_email(to: List[str], subject: str, body: str, cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None) -> str:
    """Sends an email using Microsoft Outlook."""
    
    # Resolve names to emails for all recipient fields
    resolved_to = _resolve_email_addresses(to)
    resolved_cc = _resolve_email_addresses(cc)
    resolved_bcc = _resolve_email_addresses(bcc)

    async def _send_email():
        oi = OutlookIntegration()
        try:
            await oi.initialize()
            result = await oi.send_email(
                to=resolved_to,
                subject=subject,
                body=body,
                cc=resolved_cc,
                bcc=resolved_bcc
            )
            await oi.shutdown()
            return result
        except Exception as e:
            await oi.shutdown()
            raise e
    
    try:
        result = asyncio.run(_send_email())
        if result.get("success"):
            return f"✅ Email sent successfully to {', '.join(resolved_to)}"
        else:
            return f"❌ Failed to send email: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

@tool(args_schema=ScheduleMeetingSchema)
def schedule_meeting(subject: str, start_time: str, duration_minutes: int = 60, attendees: Optional[List[str]] = None, description: str = "") -> str:
    """Schedules a meeting using Microsoft Outlook calendar. Note: Attendees will be included in the meeting title since the server doesn't support actual attendee invitations."""
    
    # Resolve attendee names to emails
    resolved_attendees = _resolve_email_addresses(attendees)

    # Parse start_time - handle relative times like "in 2 hours"
    if start_time.startswith("in "):
        # Handle relative time like "in 2 hours"
        try:
            parts = start_time.split()
            if len(parts) >= 3 and parts[0] == "in":
                amount = int(parts[1])
                unit = parts[2].lower()
                
                if unit in ["hour", "hours"]:
                    parsed_start_time = datetime.utcnow() + timedelta(hours=amount)
                elif unit in ["minute", "minutes"]:
                    parsed_start_time = datetime.utcnow() + timedelta(minutes=amount)
                elif unit in ["day", "days"]:
                    parsed_start_time = datetime.utcnow() + timedelta(days=amount)
                else:
                    return f"❌ Unsupported time unit: {unit}. Use 'hours', 'minutes', or 'days'."
            else:
                return f"❌ Invalid relative time format. Use 'in X hours/minutes/days'."
        except ValueError:
            return f"❌ Invalid time format: {start_time}"
    else:
        # Handle ISO format
        try:
            parsed_start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            return f"❌ Invalid ISO time format: {start_time}. Use YYYY-MM-DDTHH:MM:SS or 'in X hours'."
    
    async def _schedule_meeting():
        oi = OutlookIntegration()
        try:
            await oi.initialize()
            result = await oi.schedule_meeting(
                subject=subject,
                start_time=parsed_start_time,
                duration_minutes=duration_minutes,
                attendees=resolved_attendees,
                description=description
            )
            await oi.shutdown()
            return result
        except Exception as e:
            await oi.shutdown()
            raise e
    
    try:
        result = asyncio.run(_schedule_meeting())
        if result.get("success"):
            attendee_info = f" (attendees in title: {', '.join(resolved_attendees)})" if resolved_attendees else ""
            return f"✅ Meeting '{subject}' scheduled for {parsed_start_time.strftime('%Y-%m-%d %H:%M UTC')}{attendee_info}"
        else:
            return f"❌ Failed to schedule meeting: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"❌ Error scheduling meeting: {str(e)}"
