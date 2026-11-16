from dataclasses import dataclass
from dataclasses import field

@dataclass
class Candidate:
    candidate_id: int | None = None
    candidate_code: str = ""
    full_name: str = ""
    email: str = ""
    mobile: str = ""
    qualification: str = ""
    passing_year: int = 0
    percentage: float = 0.0
    backlog_count: int = 0
    primary_technology: str = ""
    profile_status: str = "ACTIVE"
    placement_status: str = "NOT_PLACED"
    skills: list[str] = field(default_factory=list)
