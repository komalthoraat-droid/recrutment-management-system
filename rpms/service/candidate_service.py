from rpms.exception.exceptions import CandidateNotFoundError
from rpms.util.validation import (
    is_valid_email,
    is_valid_mobile,
    is_valid_percentage,
    is_valid_backlog_count
)

class CandidateService:

    def __init__(self, candidate_dao):
        self.candidate_dao = candidate_dao

    def add_candidate(self, candidate):
        candidate.candidate_code = candidate.candidate_code.strip().upper()
        candidate.full_name = candidate.full_name.strip()
        candidate.email = candidate.email.strip().lower()
        candidate.mobile = candidate.mobile.strip()
        candidate.qualification = candidate.qualification.strip()
        candidate.primary_technology = candidate.primary_technology.strip()
        candidate.skills = list(dict.fromkeys(
            skill.strip() for skill in candidate.skills if skill.strip()
        ))
        if candidate.primary_technology and candidate.primary_technology.casefold() not in {
            skill.casefold() for skill in candidate.skills
        }:
            candidate.skills.append(candidate.primary_technology)

        if not candidate.candidate_code or not candidate.full_name:
            raise ValueError("Candidate code and full name are required")
        if not candidate.qualification:
            raise ValueError("Candidate qualification is required")

        if not is_valid_email(candidate.email):
            raise ValueError("Invalid email")

        if not is_valid_mobile(candidate.mobile):
            raise ValueError("Mobile must contain 10 digits")

        if not is_valid_percentage(candidate.percentage):
            raise ValueError("Percentage must be 0-100")

        if not is_valid_backlog_count(candidate.backlog_count):
            raise ValueError("Backlog count cannot be negative")

        if not 1950 <= candidate.passing_year <= 2200:
            raise ValueError("Passing year must be between 1950 and 2200")

        if candidate.profile_status != "ACTIVE":
            raise ValueError("New candidates must have ACTIVE profile status")

        if self.candidate_dao.find_by_email(candidate.email):
            raise ValueError("Duplicate email")

        if self.candidate_dao.find_by_mobile(candidate.mobile):
            raise ValueError("Duplicate mobile")

        return self.candidate_dao.save(candidate)

    def get_candidate(self, candidate_id):
        candidate = self.candidate_dao.find_by_id(candidate_id)
        if not candidate:
            raise CandidateNotFoundError(f"Candidate ID {candidate_id} not found")
        return candidate

    def get_all_candidates(self, search: str = "", status: str | None = None):
        return self.candidate_dao.find_all(search, status)

    def update_profile_status(self, candidate_id: int, status: str) -> None:
        target = status.strip().upper()
        if target not in {"ACTIVE", "INACTIVE", "ON_HOLD", "BLACKLISTED"}:
            raise ValueError("Invalid candidate profile status")
        if not self.candidate_dao.set_profile_status(candidate_id, target):
            raise CandidateNotFoundError(f"Candidate ID {candidate_id} not found")
