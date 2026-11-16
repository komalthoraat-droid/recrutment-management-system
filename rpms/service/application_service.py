import uuid

from mysql.connector import IntegrityError

from rpms.exception.exceptions import (
    CandidateNotFoundError,
    JobNotFoundError,
    DuplicateApplicationError,
    CandidateNotEligibleError,
    ApplicationNotFoundError,
    InvalidStatusTransitionError
)
from rpms.model.application import Application


class ApplicationService:

    STATUS_TRANSITIONS = {
        "APPLIED": {"SHORTLISTED", "REJECTED", "WITHDRAWN"},
        "SHORTLISTED": {"REJECTED", "WITHDRAWN"},
        "INTERVIEW_SCHEDULED": {"REJECTED", "WITHDRAWN"},
        "INTERVIEWED": {"REJECTED", "WITHDRAWN"},
        "SELECTED": {"REJECTED", "WITHDRAWN"},
        "REJECTED": set(),
        "JOINED": set(),
        "WITHDRAWN": set(),
    }

    def __init__(self, candidate_dao, job_dao, application_dao, eligibility_service):
        self.candidate_dao = candidate_dao
        self.job_dao = job_dao
        self.application_dao = application_dao
        self.eligibility_service = eligibility_service

    def apply_for_job(self, candidate_id: int, job_id: int) -> int:
        candidate = self.candidate_dao.find_by_id(candidate_id)
        if not candidate:
            raise CandidateNotFoundError("Candidate not found")

        job = self.job_dao.find_by_id(job_id)
        if not job:
            raise JobNotFoundError("Job not found")

        if self.application_dao.exists(candidate_id, job_id):
            raise DuplicateApplicationError("Candidate has already applied for this job")

        reasons = self.eligibility_service.get_failure_reasons(candidate, job)
        if reasons:
            raise CandidateNotEligibleError("; ".join(reasons))

        app = Application(
            application_code="APP-" + uuid.uuid4().hex[:8].upper(),
            candidate_id=candidate_id,
            job_id=job_id,
            eligibility_status="ELIGIBLE",
            eligibility_reason="Meets eligibility criteria",
            application_status="APPLIED"
        )

        try:
            return self.application_dao.save(app)
        except IntegrityError as exc:
            if exc.errno == 1062:
                raise DuplicateApplicationError(
                    "Candidate has already applied for this job"
                ) from exc
            raise

    def shortlist(self, application_id: int, remarks: str = "") -> None:
        self.transition(application_id, "SHORTLISTED", remarks or "Application shortlisted")

    def transition(self, application_id: int, status: str, remarks: str = "") -> None:
        application = self.application_dao.find_by_id(application_id)
        if not application:
            raise ApplicationNotFoundError(f"Application ID {application_id} not found")
        current_status = application["application_status"]
        next_status = status.strip().upper()
        allowed = self.STATUS_TRANSITIONS.get(current_status, set())
        if next_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot move application from {current_status} to {next_status}"
            )
        try:
            self.application_dao.set_status(
                application_id,
                next_status,
                remarks or f"Status changed to {next_status}",
                expected_status=current_status
            )
        except LookupError as exc:
            raise ApplicationNotFoundError(str(exc)) from exc
