from dataclasses import dataclass
from datetime import date, time

@dataclass
class Interview:
    interview_id: int | None = None
    application_id: int = 0
    round_number: int = 1
    round_type: str = ""
    mode: str = ""
    status: str = "SCHEDULED"
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    interviewer_name: str = ""
    meeting_or_location: str = ""
