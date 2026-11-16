import unittest
from datetime import date, timedelta

from rpms.model.candidate import Candidate
from rpms.model.job import Job
from rpms.service.eligibility_service import EligibilityService


class EligibilityServiceTests(unittest.TestCase):

    def setUp(self):
        self.service = EligibilityService()
        self.candidate = Candidate(
            qualification="BE",
            passing_year=date.today().year,
            percentage=80,
            backlog_count=0,
            primary_technology="Python",
            skills=["Python", "SQL"],
        )
        self.job = Job(
            min_percentage=70,
            min_passing_year=date.today().year - 1,
            max_passing_year=date.today().year + 1,
            max_backlogs=0,
            application_deadline=date.today() + timedelta(days=1),
            qualification_rule="BE, BTech",
            required_skills=["Python", "SQL"],
        )

    def test_candidate_meeting_all_criteria_is_eligible(self):
        self.assertTrue(self.service.is_eligible(self.candidate, self.job))

    def test_reasons_include_all_failed_criteria(self):
        self.candidate.profile_status = "INACTIVE"
        self.candidate.placement_status = "PLACED"
        self.candidate.qualification = "BCA"
        self.candidate.passing_year -= 5
        self.candidate.percentage = 50
        self.candidate.backlog_count = 2
        self.candidate.skills = []
        self.job.status = "CLOSED"
        self.job.company_status = "INACTIVE"
        self.job.max_backlogs = 0
        reasons = self.service.get_failure_reasons(self.candidate, self.job)
        self.assertEqual(len(reasons), 9)
        self.assertTrue(any("Qualification" in reason for reason in reasons))
        self.assertTrue(any("required skills" in reason for reason in reasons))

    def test_deadline_today_is_still_valid(self):
        self.job.application_deadline = date.today()
        self.assertTrue(self.service.is_eligible(self.candidate, self.job))


if __name__ == "__main__":
    unittest.main()
