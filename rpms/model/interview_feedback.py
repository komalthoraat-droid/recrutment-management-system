from dataclasses import dataclass


@dataclass
class InterviewFeedback:
    interview_id: int
    recommendation: str
    technical_rating: float | None = None
    communication_rating: float | None = None
    problem_solving_rating: float | None = None
    overall_rating: float | None = None
    remarks: str = ""
