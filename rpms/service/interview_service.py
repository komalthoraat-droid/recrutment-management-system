from datetime import date

from rpms.exception.exceptions import (
    ApplicationNotFoundError,
    InterviewNotFoundError,
    InvalidStatusTransitionError,
)
from rpms.model.interview_feedback import InterviewFeedback


class InterviewService:

    def __init__(self, interview_dao, application_dao):
        self.interview_dao = interview_dao
        self.application_dao = application_dao

    def schedule(self, interview):
        application = self.application_dao.find_by_id(interview.application_id)
        if not application:
            raise ApplicationNotFoundError(
                f"Application ID {interview.application_id} not found"
            )
        if application["application_status"] not in {"SHORTLISTED", "INTERVIEWED"}:
            raise InvalidStatusTransitionError(
                "Only shortlisted or previously interviewed applications can be scheduled"
            )
        if interview.scheduled_date is None or interview.scheduled_date < date.today():
            raise ValueError("Interview date must be today or a future date")
        interview.round_type = interview.round_type.strip().upper()
        interview.mode = interview.mode.strip().upper()
        if not interview.round_type:
            raise ValueError("Interview round type is required")
        if interview.mode not in {"ONLINE", "OFFLINE", "TELEPHONIC"}:
            raise ValueError("Interview mode must be ONLINE, OFFLINE, or TELEPHONIC")
        interview.round_number = self.interview_dao.next_round_number(
            interview.application_id
        )
        return self.interview_dao.save(interview)

    def submit_feedback(self, feedback: InterviewFeedback) -> None:
        interview = self.interview_dao.find_by_id(feedback.interview_id)
        if not interview:
            raise InterviewNotFoundError(f"Interview ID {feedback.interview_id} not found")
        if interview["status"] not in {"SCHEDULED", "RESCHEDULED"}:
            raise InvalidStatusTransitionError("Feedback can only be recorded for a scheduled interview")
        feedback.recommendation = feedback.recommendation.strip().upper()
        if feedback.recommendation not in {"NEXT_ROUND", "SELECTED", "REJECTED", "ON_HOLD"}:
            raise ValueError("Invalid interview recommendation")
        for label, rating in (
            ("technical", feedback.technical_rating),
            ("communication", feedback.communication_rating),
            ("problem-solving", feedback.problem_solving_rating),
            ("overall", feedback.overall_rating),
        ):
            if rating is not None and not 0 <= rating <= 5:
                raise ValueError(f"{label.title()} rating must be between 0 and 5")
        self.interview_dao.save_feedback(feedback)

    def update_status(self, interview_id: int, status: str, scheduled_date=None) -> None:
        interview = self.interview_dao.find_by_id(interview_id)
        if not interview:
            raise InterviewNotFoundError(f"Interview ID {interview_id} not found")
        current = interview["status"]
        target = status.strip().upper()
        allowed = {
            "SCHEDULED": {"RESCHEDULED", "CANCELLED", "NO_SHOW"},
            "RESCHEDULED": {"RESCHEDULED", "CANCELLED", "NO_SHOW"},
        }
        if target not in allowed.get(current, set()):
            raise InvalidStatusTransitionError(
                f"Cannot move interview from {current} to {target}"
            )
        if target == "RESCHEDULED":
            if scheduled_date is None or scheduled_date < date.today():
                raise ValueError("A rescheduled interview needs a date today or later")
        self.interview_dao.set_status(
            interview_id,
            target,
            scheduled_date=scheduled_date
        )
