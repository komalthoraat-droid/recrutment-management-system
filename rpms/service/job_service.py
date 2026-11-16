from datetime import date

from rpms.exception.exceptions import (
    InvalidStatusTransitionError,
    JobNotFoundError,
)
from rpms.model.job import Job


class JobService:

    STATUS_TRANSITIONS = {
        "DRAFT": {"OPEN", "CANCELLED"},
        "OPEN": {"CLOSED", "CANCELLED"},
        "CLOSED": {"OPEN", "CANCELLED"},
        "CANCELLED": set(),
    }

    def __init__(self, job_dao, company_service):
        self.job_dao = job_dao
        self.company_service = company_service

    def add_job(self, job: Job) -> int:
        job.job_code = job.job_code.strip().upper()
        job.job_title = job.job_title.strip()
        job.location = job.location.strip()
        job.qualification_rule = job.qualification_rule.strip()
        job.status = job.status.strip().upper()
        job.required_skills = list(dict.fromkeys(
            skill.strip() for skill in job.required_skills if skill.strip()
        ))

        if not job.job_code or not job.job_title or not job.location:
            raise ValueError("Job code, title, and location are required")
        if job.openings < 1:
            raise ValueError("A job must have at least one opening")
        if not 0 <= job.min_percentage <= 100:
            raise ValueError("Minimum percentage must be between 0 and 100")
        if job.max_backlogs < 0:
            raise ValueError("Maximum backlogs cannot be negative")
        if (
            job.min_passing_year
            and job.max_passing_year
            and job.min_passing_year > job.max_passing_year
        ):
            raise ValueError("Minimum passing year cannot exceed maximum passing year")
        if job.min_package_lpa < 0 or job.max_package_lpa < 0:
            raise ValueError("Package amounts cannot be negative")
        if job.max_package_lpa and job.min_package_lpa > job.max_package_lpa:
            raise ValueError("Minimum package cannot exceed maximum package")
        if job.application_deadline is None or job.application_deadline < date.today():
            raise ValueError("Application deadline must be today or a future date")
        if job.status not in {"DRAFT", "OPEN"}:
            raise ValueError("A new job must be DRAFT or OPEN")
        company = self.company_service.get_company(job.company_id)
        if company.status != "ACTIVE":
            raise InvalidStatusTransitionError("Jobs can only be created for active companies")
        return self.job_dao.save(job)

    def get_job(self, job_id: int):
        job = self.job_dao.find_by_id(job_id)
        if not job:
            raise JobNotFoundError(f"Job ID {job_id} not found")
        return job

    def get_open_jobs(self, search: str = ""):
        return self.job_dao.find_open_jobs(search)

    def get_jobs(self, search: str = "", status: str | None = None):
        return self.job_dao.find_all(search, status)

    def update_status(self, job_id: int, status: str) -> None:
        job = self.get_job(job_id)
        target = status.strip().upper()
        if target not in self.STATUS_TRANSITIONS.get(job.status, set()):
            raise ValueError(f"Cannot move job from {job.status} to {target}")
        if target == "OPEN" and job.application_deadline < date.today():
            raise ValueError("An expired job cannot be reopened")
        if target == "OPEN":
            company = self.company_service.get_company(job.company_id)
            if company.status != "ACTIVE":
                raise ValueError("A job cannot be opened for an inactive company")
        self.job_dao.set_status(job_id, target)
